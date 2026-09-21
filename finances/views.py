import json
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from datetime import date
from accounts.models import Workspace
from accounts.forms import WorkspaceForm
from .models import Transaction, Category
from .forms import TransactionForm, CategoryForm


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

    # Ações POST (Workspace, Categoria, Transação)
    if request.method == 'POST' and 'create_workspace' in request.POST:
        ws_form = WorkspaceForm(request.POST)
        if ws_form.is_valid():
            new_ws = ws_form.save(commit=False)
            new_ws.user = request.user
            new_ws.save()
            return redirect(f"{request.path}?workspace={new_ws.id}&year={selected_year}&month={selected_month}")

    if request.method == 'POST' and 'create_category' in request.POST and current_workspace:
        cat_form = CategoryForm(request.POST)
        if cat_form.is_valid():
            new_cat = cat_form.save(commit=False)
            new_cat.workspace = current_workspace
            new_cat.save()
            return redirect(
                f"{request.path}?workspace={current_workspace.id}&year={selected_year}&month={selected_month}")

    if request.method == 'POST' and 'create_transaction' in request.POST and current_workspace:
        trans_form = TransactionForm(request.POST, workspace=current_workspace)
        if trans_form.is_valid():
            trans = trans_form.save(commit=False)
            trans.workspace = current_workspace
            trans.save()
            return redirect(
                f"{request.path}?workspace={current_workspace.id}&year={selected_year}&month={selected_month}")

    trans_form = TransactionForm(workspace=current_workspace,
                                 initial={'transaction_date': today, 'status': 'PAID'}) if current_workspace else None
    cat_form = CategoryForm()
    ws_form = WorkspaceForm()

    transactions = []
    total_income = 0
    total_expense = 0
    balance = 0
    pending_income = 0
    pending_expense = 0
    chart_labels = []
    chart_data = []

    if current_workspace:
        qs = Transaction.objects.filter(
            workspace=current_workspace,
            transaction_date__year=selected_year,
            transaction_date__month=selected_month
        )
        transactions = qs.order_by('-transaction_date', '-created_at')

        # Realizado (Concluído/Pago)
        total_income = qs.filter(category__category_type='INCOME', status='PAID').aggregate(Sum('amount'))[
                           'amount__sum'] or 0
        total_expense = qs.filter(category__category_type='EXPENSE', status='PAID').aggregate(Sum('amount'))[
                            'amount__sum'] or 0
        balance = total_income - total_expense

        # Previsão (Pendente)
        pending_income = qs.filter(category__category_type='INCOME', status='PENDING').aggregate(Sum('amount'))[
                             'amount__sum'] or 0
        pending_expense = qs.filter(category__category_type='EXPENSE', status='PENDING').aggregate(Sum('amount'))[
                              'amount__sum'] or 0

        # Gráfico de despesas pagas
        expense_by_cat = qs.filter(
            category__category_type='EXPENSE', status='PAID'
        ).values('category__name').annotate(total=Sum('amount')).order_by('-total')

        for item in expense_by_cat:
            cat_name = item['category__name'] or 'Sem Categoria'
            chart_labels.append(cat_name.upper())
            chart_data.append(float(item['total']))

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
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'pending_income': pending_income,
        'pending_expense': pending_expense,
        'form': trans_form,
        'category_form': cat_form,
        'workspace_form': ws_form,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'months_list': months_list,
        'years_list': years_list,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_data_json': json.dumps(chart_data),
    }
    return render(request, 'finances/dashboard.html', context)


@login_required
def toggle_transaction_status(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, workspace__user=request.user)
    # Alterna o status
    transaction.status = 'PENDING' if transaction.status == 'PAID' else 'PAID'
    transaction.save()

    # Redireciona mantendo os filtros atuais
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('dashboard')


@login_required
def edit_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, workspace__user=request.user)
    workspace = transaction.workspace

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, workspace=workspace)
        if form.is_valid():
            form.save()
            return redirect(f"/dashboard/?workspace={workspace.id}&year={transaction.transaction_date.year}&month={transaction.transaction_date.month}")
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
    return redirect(f"/dashboard/?workspace={workspace.id}&year={t_date.year}&month={t_date.month}")


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