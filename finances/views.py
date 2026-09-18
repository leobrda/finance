from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from datetime import date
from accounts.models import Workspace
from accounts.forms import WorkspaceForm
from .models import Transaction, Category
from .forms import TransactionForm, CategoryForm
from django.shortcuts import get_object_or_404


@login_required
def dashboard_view(request):
    workspaces = Workspace.objects.filter(user=request.user)

    workspace_id = request.GET.get('workspace')
    current_workspace = None
    if workspace_id:
        current_workspace = workspaces.filter(id=workspace_id).first()
    if not current_workspace and workspaces.exists():
        current_workspace = workspaces.first()

    # Criação de Novo Workspace (ex: Loja de Celular)
    if request.method == 'POST' and 'create_workspace' in request.POST:
        ws_form = WorkspaceForm(request.POST)
        if ws_form.is_valid():
            new_ws = ws_form.save(commit=False)
            new_ws.user = request.user
            new_ws.save()
            return redirect(f"{request.path}?workspace={new_ws.id}")

    # Criação de Nova Categoria para o Workspace ativo
    if request.method == 'POST' and 'create_category' in request.POST and current_workspace:
        cat_form = CategoryForm(request.POST)
        if cat_form.is_valid():
            new_cat = cat_form.save(commit=False)
            new_cat.workspace = current_workspace
            new_cat.save()
            return redirect(f"{request.path}?workspace={current_workspace.id}")

    # Criação de Transação
    if request.method == 'POST' and 'create_transaction' in request.POST and current_workspace:
        trans_form = TransactionForm(request.POST, workspace=current_workspace)
        if trans_form.is_valid():
            trans = trans_form.save(commit=False)
            trans.workspace = current_workspace
            trans.save()
            return redirect(f"{request.path}?workspace={current_workspace.id}")

    # Formulários para exibição
    trans_form = TransactionForm(workspace=current_workspace,
                                 initial={'transaction_date': date.today()}) if current_workspace else None
    cat_form = CategoryForm()
    ws_form = WorkspaceForm()

    transactions = []
    total_income = 0
    total_expense = 0
    balance = 0

    if current_workspace:
        transactions = Transaction.objects.filter(workspace=current_workspace)[:15]
        income_agg = Transaction.objects.filter(
            workspace=current_workspace, category__category_type='INCOME', status='PAID'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        expense_agg = Transaction.objects.filter(
            workspace=current_workspace, category__category_type='EXPENSE', status='PAID'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        total_income = income_agg
        total_expense = expense_agg
        balance = total_income - total_expense

    context = {
        'workspaces': workspaces,
        'current_workspace': current_workspace,
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'form': trans_form,
        'category_form': cat_form,
        'workspace_form': ws_form,
    }
    return render(request, 'finances/dashboard.html', context)


@login_required
def edit_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, workspace__user=request.user)
    workspace = transaction.workspace

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, workspace=workspace)
        if form.is_valid():
            form.save()
            return redirect(f"/dashboard/?workspace={workspace.id}")
    else:
        form = TransactionForm(instance=transaction, workspace=workspace)

    return render(request, 'finances/edit_transaction.html', {
        'form': form,
        'transaction': transaction,
        'workspace': workspace
    })


@login_required
def delete_transaction_view(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, workspace__user=request.user)
    workspace_id = transaction.workspace.id
    if request.method == 'POST':
        transaction.delete()
    return redirect(f"/dashboard/?workspace={workspace_id}")