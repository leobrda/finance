from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from datetime import date
from accounts.models import Workspace
from .models import Transaction
from .forms import TransactionForm


@login_required
def dashboard_view(request):
    workspaces = Workspace.objects.filter(user=request.user)

    workspace_id = request.GET.get('workspace')
    current_workspace = None
    if workspace_id:
        current_workspace = workspaces.filter(id=workspace_id).first()
    if not current_workspace and workspaces.exists():
        current_workspace = workspaces.first()

    # Processar envio da nova transação
    if request.method == 'POST' and current_workspace:
        form = TransactionForm(request.POST, workspace=current_workspace)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.workspace = current_workspace
            transaction.save()
            return redirect(f"{request.path}?workspace={current_workspace.id}")
    else:
        initial_data = {'transaction_date': date.today()}
        form = TransactionForm(workspace=current_workspace, initial=initial_data) if current_workspace else None

    transactions = []
    total_income = 0
    total_expense = 0
    balance = 0

    if current_workspace:
        transactions = Transaction.objects.filter(workspace=current_workspace)[:10]

        income_agg = Transaction.objects.filter(
            workspace=current_workspace,
            category__category_type='INCOME',
            status='PAID'
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        expense_agg = Transaction.objects.filter(
            workspace=current_workspace,
            category__category_type='EXPENSE',
            status='PAID'
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
        'form': form,
    }
    return render(request, 'finances/dashboard.html', context)