from django.db import models
from accounts.models import Workspace

class Category(models.Model):
    CATEGORY_TYPE_CHOICES = [
        ('INCOME', 'Receita'),
        ('EXPENSE', 'Despesa'),
    ]

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name='Workspace'
    )
    name = models.CharField('Nome da Categoria', max_length=80)
    category_type = models.CharField('Tipo', max_length=10, choices=CATEGORY_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        unique_together = ('workspace', 'name', 'category_type')

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()}) - {self.workspace.name}"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('PAID', 'Concluído/Pago'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('PIX', 'Pix'),
        ('CREDIT_CARD', 'Cartão de Crédito'),
        ('DEBIT_CARD', 'Cartão de Débito'),
        ('CASH', 'Dinheiro'),
        ('TRANSFER', 'Transferência / TED'),
    ]

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Workspace'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Categoria'
    )

    recurring_expense = models.ForeignKey(
        'RecurringExpense',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_transactions'
    )

    description = models.CharField('Descrição', max_length=255)
    amount = models.DecimalField('Valor (R$)', max_digits=12, decimal_places=2)
    transaction_date = models.DateField('Data da Transação')
    payment_method = models.CharField('Forma de Pagamento', max_length=20, choices=PAYMENT_METHOD_CHOICES, default='PIX')
    status = models.CharField('Status', max_length=10, choices=STATUS_CHOICES, default='PAID')
    notes = models.TextField('Observações', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        ordering = ['-transaction_date', '-created_at']

    def __str__(self):
        return f"{self.description} - R$ {self.amount} ({self.workspace.name})"


class MonthlyGoal(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='goals')
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()
    revenue_goal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True)
    expense_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('workspace', 'year', 'month')

    def __str__(self):
        return f"Metas {self.month}/{self.year} - {self.workspace.name}"


class RecurringExpense(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='recurring_expenses')
    description = models.CharField('Descrição', max_length=255)
    amount = models.DecimalField('Valor (R$)', max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Categoria')
    payment_method = models.CharField('Forma de Pagamento', max_length=20, choices=Transaction.PAYMENT_METHOD_CHOICES, default='CREDIT_CARD')
    due_day = models.PositiveSmallIntegerField('Dia de Cobrança', help_text="Dia de cobrança no mês (1-31)")
    notes = models.TextField('Observações', blank=True, null=True)
    auto_pay = models.BooleanField('Baixa Automática (Débito em Conta / Cartão)', default=True,
                                   help_text="Se marcado, confirma como Pago automaticamente após o dia de cobrança.")
    is_active = models.BooleanField('Ativo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Despesa Recorrente'
        verbose_name_plural = 'Despesas Recorrentes'
        ordering = ['due_day', 'description']

    def __str__(self):
        return f"{self.description} (Dia {self.due_day}) - R$ {self.amount}"