import json
import csv
import calendar
from decimal import Decimal
from datetime import date, datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Q
from django.urls import reverse

from accounts.models import Workspace
from accounts.forms import WorkspaceForm
from .models import Transaction, Category, MonthlyGoal, RecurringExpense
from .forms import TransactionForm, CategoryForm, MonthlyGoalForm, RecurringExpenseForm

from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa


def add_months(orig_date, months_to_add):
    """
    Incrementa meses com segurança matemática e de calendário.
    Trata anos bissextos e meses com 28, 29, 30 ou 31 dias sem lançar exceções.
    Ex: 31/01 + 1 mês = 28/02 (ou 29/02 se bissexto).
    """
    new_year = orig_date.year + (orig_date.month - 1 + months_to_add) // 12
    new_month = (orig_date.month - 1 + months_to_add) % 12 + 1
    _, max_day = calendar.monthrange(new_year, new_month)
    new_day = min(orig_date.day, max_day)
    return date(new_year, new_month, new_day)


def landing_page_view(request):
    """
    Landing page pública do produto.
    Se o usuário já estiver logado, redireciona diretamente ao dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'finances/landing_page.html')


@login_required
def dashboard_view(request):
    workspaces = Workspace.objects.filter(user=request.user)

    workspace_id = request.GET.get('workspace')
    current_workspace = None
    if workspace_id:
        current_workspace = workspaces.filter(id=workspace_id).first()
    if not current_workspace and workspaces.exists():
        current_workspace = workspaces.first()

    today = date.today()
    try:
        selected_year = int(request.GET.get('year', today.year))
        selected_month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        selected_year = today.year
        selected_month = today.month

    search_query = request.GET.get('q', '').strip()
    filter_type = request.GET.get('type', '').strip()
    filter_category = request.GET.get('cat', '').strip()
    filter_payment = request.GET.get('payment', '').strip()

    # 1. POST: Workspace
    if request.method == 'POST' and 'create_workspace' in request.POST:
        ws_form = WorkspaceForm(request.POST)
        if ws_form.is_valid():
            new_ws = ws_form.save(commit=False)
            new_ws.user = request.user
            new_ws.save()
            return redirect(f"{request.path}?workspace={new_ws.id}&year={selected_year}&month={selected_month}")

    # 2. POST: Categoria
    if request.method == 'POST' and 'create_category' in request.POST and current_workspace:
        cat_form = CategoryForm(request.POST)
        if cat_form.is_valid():
            new_cat = cat_form.save(commit=False)
            new_cat.workspace = current_workspace
            new_cat.save()
            return redirect(f"{request.path}?workspace={current_workspace.id}&year={selected_year}&month={selected_month}")

    # 3. POST: Transação (Com suporte a parcelamento em lote e upload de comprovante)
    if request.method == 'POST' and 'create_transaction' in request.POST and current_workspace:
        trans_form = TransactionForm(request.POST, request.FILES, workspace=current_workspace)
        if trans_form.is_valid():
            raw_installments = request.POST.get('installments', '1').strip()
            try:
                num_installments = max(1, int(raw_installments))
            except ValueError:
                num_installments = 1

            installment_type = request.POST.get('installment_type', 'total')

            base_trans = trans_form.save(commit=False)
            base_trans.workspace = current_workspace
            initial_amount = base_trans.amount
            initial_desc = base_trans.description
            initial_date = base_trans.transaction_date

            if num_installments == 1:
                base_trans.save()
            else:
                # Cálculo de parcelamento com compensação de centavos na 1ª parcela
                if installment_type == 'per_installment':
                    part_amount = initial_amount
                    first_amount = initial_amount
                else:
                    part_amount = (initial_amount / num_installments).quantize(Decimal('0.01'))
                    first_amount = initial_amount - (part_amount * (num_installments - 1))

                # Primeira parcela (01/N): herda o comprovante e status escolhido
                base_trans.description = f"{initial_desc} (01/{num_installments:02d})"
                base_trans.amount = first_amount
                base_trans.save()

                # Parcelas futuras (02/N até N/N): entram nos meses seguintes como PENDING
                for i in range(1, num_installments):
                    due_date = add_months(initial_date, i)
                    installment_number = i + 1
                    Transaction.objects.create(
                        workspace=current_workspace,
                        description=f"{initial_desc} ({installment_number:02d}/{num_installments:02d})",
                        amount=part_amount,
                        transaction_date=due_date,
                        category=base_trans.category,
                        payment_method=base_trans.payment_method,
                        status='PENDING',
                        notes=base_trans.notes or f"Parcela {installment_number} de {num_installments} referente à compra '{initial_desc}'."
                    )

            return redirect(f"{request.path}?workspace={current_workspace.id}&year={selected_year}&month={selected_month}")

    # 4. POST: Metas do Mês
    if request.method == 'POST' and 'save_goals' in request.POST and current_workspace:
        raw_rev = request.POST.get('revenue_goal', '').replace(',', '.').strip()
        raw_exp = request.POST.get('expense_limit', '').replace(',', '.').strip()

        try:
            rev_val = Decimal(raw_rev) if raw_rev else Decimal('0.00')
        except Exception:
            rev_val = Decimal('0.00')

        try:
            exp_val = Decimal(raw_exp) if raw_exp else Decimal('0.00')
        except Exception:
            exp_val = Decimal('0.00')

        MonthlyGoal.objects.update_or_create(
            workspace=current_workspace,
            year=selected_year,
            month=selected_month,
            defaults={
                'revenue_goal': rev_val,
                'expense_limit': exp_val,
            }
        )
        return redirect(f"{request.path}?workspace={current_workspace.id}&year={selected_year}&month={selected_month}")

    # Auto-provisionamento de assinaturas recorrentes com verificação temporal e baixa automática
    if current_workspace:
        active_recurrings = RecurringExpense.objects.filter(workspace=current_workspace, is_active=True)
        for rec in active_recurrings:
            _, max_days = calendar.monthrange(selected_year, selected_month)
            valid_day = min(rec.due_day, max_days)
            t_date = date(selected_year, selected_month, valid_day)

            # Regra: Só vira PAID automaticamente se auto_pay estiver ativo e a data já tiver chegado
            should_auto_pay = rec.auto_pay and (t_date <= today)
            initial_status = 'PAID' if should_auto_pay else 'PENDING'

            existing_trans = Transaction.objects.filter(
                workspace=current_workspace,
                recurring_expense=rec,
                transaction_date__year=selected_year,
                transaction_date__month=selected_month
            ).first()

            if not existing_trans:
                Transaction.objects.create(
                    workspace=current_workspace,
                    description=f"{rec.description} 🔁",
                    amount=rec.amount,
                    category=rec.category,
                    payment_method=rec.payment_method,
                    transaction_date=t_date,
                    status=initial_status,
                    notes=rec.notes or 'Despesa recorrente mensal provisionada automaticamente.',
                    recurring_expense=rec
                )
            else:
                # Se já existia e deveria estar quitado automaticamente por data, atualiza de imediato
                if should_auto_pay and existing_trans.status == 'PENDING':
                    existing_trans.status = 'PAID'
                    existing_trans.save(update_fields=['status'])

    trans_form = TransactionForm(workspace=current_workspace, initial={'transaction_date': today, 'status': 'PAID'}) if current_workspace else None
    cat_form = CategoryForm()
    ws_form = WorkspaceForm()
    recurring_form = RecurringExpenseForm(workspace=current_workspace) if current_workspace else None

    transactions = []
    workspace_categories = []
    recurring_expenses = []
    total_income = Decimal('0.00')
    total_expense = Decimal('0.00')
    balance = Decimal('0.00')
    pending_income = Decimal('0.00')
    pending_expense = Decimal('0.00')
    chart_labels = []
    chart_data = []
    income_chart_labels = []
    income_chart_data = []

    history_labels = []
    history_income_data = []
    history_expense_data = []

    monthly_goal = None
    goal_form = None
    revenue_goal = Decimal('0.00')
    expense_limit = Decimal('0.00')
    revenue_percent = 0
    revenue_bar_width = 0
    expense_percent = 0
    expense_bar_width = 0
    revenue_remaining = Decimal('0.00')
    expense_remaining = Decimal('0.00')

    # Métricas comparativas (Month-over-Month)
    prev_month_label = ""
    income_diff_pct = 0.0
    income_is_up = True
    income_is_neutral = True
    expense_diff_pct = 0.0
    expense_is_up = True
    expense_is_neutral = True
    balance_diff_pct = 0.0
    balance_is_up = True
    balance_is_neutral = True

    month_abbrevs = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }

    if current_workspace:
        workspace_categories = Category.objects.filter(workspace=current_workspace).order_by('name')
        recurring_expenses = RecurringExpense.objects.filter(workspace=current_workspace).order_by('due_day', 'description')

        monthly_goal = MonthlyGoal.objects.filter(
            workspace=current_workspace,
            year=selected_year,
            month=selected_month
        ).first()

        goal_form = MonthlyGoalForm(instance=monthly_goal)

        if monthly_goal:
            revenue_goal = monthly_goal.revenue_goal or Decimal('0.00')
            expense_limit = monthly_goal.expense_limit or Decimal('0.00')

        base_qs = Transaction.objects.filter(
            workspace=current_workspace,
            transaction_date__year=selected_year,
            transaction_date__month=selected_month
        )

        total_income = base_qs.filter(category__category_type='INCOME', status='PAID').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        total_expense = base_qs.filter(category__category_type='EXPENSE', status='PAID').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        balance = total_income - total_expense

        pending_income = base_qs.filter(category__category_type='INCOME', status='PENDING').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        pending_expense = base_qs.filter(category__category_type='EXPENSE', status='PENDING').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        # --- Cálculo Comparativo Mês a Mês (Month-over-Month) ---
        prev_month = 12 if selected_month == 1 else selected_month - 1
        prev_year = selected_year - 1 if selected_month == 1 else selected_year
        prev_month_label = f"{month_abbrevs[prev_month]}/{str(prev_year)[2:]}"

        prev_qs = Transaction.objects.filter(
            workspace=current_workspace,
            transaction_date__year=prev_year,
            transaction_date__month=prev_month,
            status='PAID'
        )

        prev_income = prev_qs.filter(category__category_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        prev_expense = prev_qs.filter(category__category_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        prev_balance = prev_income - prev_expense

        def calculate_mom_delta(current_val, previous_val):
            if previous_val == Decimal('0.00'):
                if current_val > Decimal('0.00'):
                    return 100.0, True, False
                elif current_val < Decimal('0.00'):
                    return 100.0, False, False
                return 0.0, False, True

            delta = ((current_val - previous_val) / abs(previous_val)) * Decimal('100')
            delta_float = round(float(delta), 1)
            return abs(delta_float), delta_float >= 0, delta_float == 0

        income_diff_pct, income_is_up, income_is_neutral = calculate_mom_delta(total_income, prev_income)
        expense_diff_pct, expense_is_up, expense_is_neutral = calculate_mom_delta(total_expense, prev_expense)
        balance_diff_pct, balance_is_up, balance_is_neutral = calculate_mom_delta(balance, prev_balance)

        if revenue_goal > Decimal('0.00'):
            calc_rev = float((total_income / revenue_goal) * Decimal('100'))
            revenue_percent = round(calc_rev, 1)
            revenue_bar_width = min(revenue_percent, 100)
            revenue_remaining = revenue_goal - total_income

        if expense_limit > Decimal('0.00'):
            calc_exp = float((total_expense / expense_limit) * Decimal('100'))
            expense_percent = round(calc_exp, 1)
            expense_bar_width = min(expense_percent, 100)
            expense_remaining = expense_limit - total_expense

        expense_by_cat = base_qs.filter(
            category__category_type='EXPENSE', status='PAID'
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

        for item in expense_by_cat:
            cat_name = item['category__name'] or 'Sem Categoria'
            chart_labels.append(cat_name.upper())
            chart_data.append(float(item['total']))

        income_by_cat = base_qs.filter(
            category__category_type='INCOME', status='PAID'
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

        for item in income_by_cat:
            cat_name = item['category__name'] or 'Sem Categoria'
            income_chart_labels.append(cat_name.upper())
            income_chart_data.append(float(item['total']))

        for offset in range(5, -1, -1):
            calc_m = selected_month - offset
            calc_y = selected_year
            while calc_m <= 0:
                calc_m += 12
                calc_y -= 1

            m_qs = Transaction.objects.filter(
                workspace=current_workspace,
                transaction_date__year=calc_y,
                transaction_date__month=calc_m,
                status='PAID'
            )

            m_inc = m_qs.filter(category__category_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            m_exp = m_qs.filter(category__category_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

            label_str = f"{month_abbrevs[calc_m]}/{str(calc_y)[2:]}"
            history_labels.append(label_str)
            history_income_data.append(float(m_inc))
            history_expense_data.append(float(m_exp))

        table_qs = base_qs

        if search_query:
            table_qs = table_qs.filter(
                Q(description__icontains=search_query) | Q(notes__icontains=search_query)
            )

        if filter_type in ['INCOME', 'EXPENSE']:
            table_qs = table_qs.filter(category__category_type=filter_type)

        if filter_category:
            table_qs = table_qs.filter(category_id=filter_category)

        if filter_payment:
            table_qs = table_qs.filter(payment_method=filter_payment)

        transactions = table_qs.order_by('-transaction_date', '-created_at')

    months_list = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'),
        (4, 'Abril'), (5, 'Maio'), (6, 'Junho'),
        (7, 'Julho'), (8, 'Agosto'), (9, 'Setembro'),
        (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]
    years_list = range(today.year - 2, today.year + 3)

    context = {
        'workspaces': workspaces,
        'current_workspace': current_workspace,
        'workspace_categories': workspace_categories,
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'pending_income': pending_income,
        'pending_expense': pending_expense,
        'form': trans_form,
        'category_form': cat_form,
        'workspace_form': ws_form,
        'recurring_form': recurring_form,
        'recurring_expenses': recurring_expenses,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'months_list': months_list,
        'years_list': years_list,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_data_json': json.dumps(chart_data),
        'income_chart_labels_json': json.dumps(income_chart_labels),
        'income_chart_data_json': json.dumps(income_chart_data),
        'history_labels_json': json.dumps(history_labels),
        'history_income_data_json': json.dumps(history_income_data),
        'history_expense_data_json': json.dumps(history_expense_data),
        'search_query': search_query,
        'filter_type': filter_type,
        'filter_category': filter_category,
        'filter_payment': filter_payment,
        'monthly_goal': monthly_goal,
        'goal_form': goal_form,
        'revenue_goal': revenue_goal,
        'expense_limit': expense_limit,
        'revenue_percent': revenue_percent,
        'revenue_bar_width': revenue_bar_width,
        'expense_percent': expense_percent,
        'expense_bar_width': expense_bar_width,
        'revenue_remaining': revenue_remaining,
        'expense_remaining': expense_remaining,
        'prev_month_label': prev_month_label,
        'income_diff_pct': income_diff_pct,
        'income_is_up': income_is_up,
        'income_is_neutral': income_is_neutral,
        'expense_diff_pct': expense_diff_pct,
        'expense_is_up': expense_is_up,
        'expense_is_neutral': expense_is_neutral,
        'balance_diff_pct': balance_diff_pct,
        'balance_is_up': balance_is_up,
        'balance_is_neutral': balance_is_neutral,
    }
    return render(request, 'finances/dashboard.html', context)


@login_required
def create_recurring_expense_view(request):
    workspace_id = request.GET.get('workspace')
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)

    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST, workspace=workspace)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.workspace = workspace
            rec.save()
    return redirect(f"{reverse('dashboard')}?workspace={workspace.id}")


@login_required
def delete_recurring_expense_view(request, pk):
    rec = get_object_or_404(RecurringExpense, pk=pk, workspace__user=request.user)
    ws_id = rec.workspace.id
    if request.method == 'POST':
        rec.delete()
    return redirect(f"{reverse('dashboard')}?workspace={ws_id}")


@login_required
def toggle_transaction_status(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, workspace__user=request.user)
    transaction.status = 'PENDING' if transaction.status == 'PAID' else 'PAID'
    transaction.save()

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('dashboard')


@login_required
def edit_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, workspace__user=request.user)
    workspace = transaction.workspace

    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES, instance=transaction, workspace=workspace)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('dashboard')}?workspace={workspace.id}&year={transaction.transaction_date.year}&month={transaction.transaction_date.month}")
    else:
        form = TransactionForm(instance=transaction, workspace=workspace)

    return render(request, 'finances/edit_transaction.html', {'form': form, 'workspace': workspace})


@login_required
def delete_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, workspace__user=request.user)
    workspace = transaction.workspace
    t_date = transaction.transaction_date

    if request.method == 'POST':
        transaction.delete()
    return redirect(f"{reverse('dashboard')}?workspace={workspace.id}&year={t_date.year}&month={t_date.month}")


@login_required
def export_transactions_csv(request):
    workspace_id = request.GET.get('workspace')
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)

    today = date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        year = today.year
        month = today.month

    transactions = Transaction.objects.filter(
        workspace=workspace,
        transaction_date__year=year,
        transaction_date__month=month
    ).order_by('transaction_date')

    filename = f"extrato_{workspace.name.lower().replace(' ', '_')}_{month:02d}_{year}.csv"
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Data', 'Descricao', 'Categoria', 'Tipo', 'Forma de Pagamento', 'Status', 'Valor (R$)', 'Observacoes'])

    for t in transactions:
        cat_name = t.category.name if t.category else 'Sem Categoria'
        cat_type = t.category.get_category_type_display() if t.category else '-'
        payment = t.get_payment_method_display()
        status_display = t.get_status_display()
        val_formatted = str(t.amount).replace('.', ',')
        notes = t.notes if t.notes else ''

        writer.writerow([
            t.transaction_date.strftime('%d/%m/%Y'),
            t.description,
            cat_name,
            cat_type,
            payment,
            status_display,
            val_formatted,
            notes
        ])

    return response


@login_required
def manage_categories_view(request):
    workspace_id = request.GET.get('workspace')
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user) if workspace_id else Workspace.objects.filter(user=request.user).first()

    if not workspace:
        return redirect('dashboard')

    if request.method == 'POST' and 'create_category' in request.POST:
        cat_form = CategoryForm(request.POST)
        if cat_form.is_valid():
            new_cat = cat_form.save(commit=False)
            new_cat.workspace = workspace
            new_cat.save()
            return redirect(f"{request.path}?workspace={workspace.id}")

    categories = Category.objects.filter(workspace=workspace).order_by('category_type', 'name')

    for cat in categories:
        cat.transactions_count = Transaction.objects.filter(category=cat).count()

    cat_form = CategoryForm()

    return render(request, 'finances/manage_categories.html', {
        'workspace': workspace,
        'categories': categories,
        'cat_form': cat_form,
    })


@login_required
def edit_category_view(request, pk):
    category = get_object_or_404(Category, pk=pk, workspace__user=request.user)
    workspace = category.workspace

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('manage_categories')}?workspace={workspace.id}")
    else:
        form = CategoryForm(instance=category)

    return render(request, 'finances/edit_category.html', {
        'form': form,
        'category': category,
        'workspace': workspace
    })


@login_required
def delete_category_view(request, pk):
    category = get_object_or_404(Category, pk=pk, workspace__user=request.user)
    workspace = category.workspace

    if request.method == 'POST':
        category.delete()
    return redirect(f"{reverse('manage_categories')}?workspace={workspace.id}")


@login_required
def export_monthly_report_pdf(request):
    workspace_id = request.GET.get('workspace')
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)

    today = date.today()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        year = today.year
        month = today.month

    month_names = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    base_qs = Transaction.objects.filter(
        workspace=workspace,
        transaction_date__year=year,
        transaction_date__month=month
    )

    transactions = base_qs.order_by('transaction_date', 'created_at')

    total_income = base_qs.filter(category__category_type='INCOME', status='PAID').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_expense = base_qs.filter(category__category_type='EXPENSE', status='PAID').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    balance = total_income - total_expense

    expense_cats_raw = base_qs.filter(category__category_type='EXPENSE', status='PAID') \
                              .values('category__name') \
                              .annotate(total=Sum('amount')) \
                              .order_by('-total')

    expense_by_cat = []
    for item in expense_cats_raw:
        cat_total = item['total'] or Decimal('0.00')
        percent = (cat_total / total_expense * Decimal('100')) if total_expense > Decimal('0.00') else Decimal('0.00')
        expense_by_cat.append({
            'name': item['category__name'] or 'Sem Categoria',
            'total': cat_total,
            'percent': float(percent)
        })

    context = {
        'workspace': workspace,
        'selected_year': year,
        'selected_month': month,
        'month_name': month_names.get(month, ''),
        'today_date': datetime.now(),
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'expense_by_cat': expense_by_cat,
    }

    template = get_template('finances/report_pdf.html')
    html = template.render(context)
    result = BytesIO()

    pdf_status = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, encoding='UTF-8')

    if not pdf_status.err:
        filename = f"relatorio_{workspace.name.lower().replace(' ', '_')}_{month:02d}_{year}.pdf"
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    return HttpResponse("Erro ao gerar o relatório em PDF.", status=500)