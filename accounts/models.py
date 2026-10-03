from datetime import date
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Workspace(models.Model):
    WORKSPACE_TYPE_CHOICES = [
        ('BUSINESS', 'Empresa / PJ'),
        ('PERSONAL', 'Finanças Pessoais / PF'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workspaces',
        verbose_name='Usuário Proprietário'
    )
    name = models.CharField('Nome do Workspace', max_length=100)
    workspace_type = models.CharField(
        'Tipo de Carteira',
        max_length=10,
        choices=WORKSPACE_TYPE_CHOICES,
        default='PERSONAL'
    )
    created_at = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Workspace'
        verbose_name_plural = 'Workspaces'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_workspace_type_display()})"


class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    accent_primary = models.CharField(max_length=7, default='#FFE600')      # Cor destaque / principal
    accent_secondary = models.CharField(max_length=7, default='#FF4A22')    # Cor de despesas / alerta
    theme_mode = models.CharField(max_length=10, default='light')           # 'light' ou 'dark'

    def __str__(self):
        return f"Preferências de {self.user.username}"


# Garante que o novo usuário criado já ganha um registro de preferências
@receiver(post_save, sender=User)
def create_or_save_user_preference(sender, instance, created, **kwargs):
    if created:
        UserPreference.objects.create(user=instance)
    else:
        # Se for um usuário antigo que ainda não tinha o registro criado
        UserPreference.objects.get_or_create(user=instance)


class Subscription(models.Model):
    PLAN_CHOICES = [
        ('FREE', 'Gratuito'),
        ('MONTHLY_PRO', 'Mensal Pro (R$ 9,90/mês)'),
        ('ANNUAL_PRO', 'Anual Pro (R$ 79,90/ano)'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Ativa'),
        ('TRIALING', 'Período de Testes (Trial)'),
        ('PAST_DUE', 'Pagamento Pendente / Atrasado'),
        ('CANCELED', 'Cancelada'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription', verbose_name='Usuário')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='FREE', verbose_name='Plano')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='Status')
    starts_at = models.DateField(default=date.today, verbose_name='Início da Assinatura')
    expires_at = models.DateField(null=True, blank=True, verbose_name='Vencimento / Expiração')

    # Identificadores para futuras integrações (ex.: Asaas, Mercado Pago)
    gateway_customer_id = models.CharField(max_length=100, blank=True, null=True,
                                           verbose_name='ID do Cliente no Gateway')
    gateway_subscription_id = models.CharField(max_length=100, blank=True, null=True,
                                               verbose_name='ID da Assinatura no Gateway')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'

    def __str__(self):
        user_name = self.user.get_full_name() or self.user.username
        return f"{user_name} — {self.get_plan_display()} ({self.get_status_display()})"

    @property
    def is_pro(self):
        """Retorna True se o usuário tiver plano pago ativo ou em teste."""
        return self.status in ['ACTIVE', 'TRIALING'] and self.plan in ['MONTHLY_PRO', 'ANNUAL_PRO']

    @property
    def is_annual(self):
        """Retorna True apenas se tiver o plano Anual ativo."""
        return self.status in ['ACTIVE', 'TRIALING'] and self.plan == 'ANNUAL_PRO'

    @property
    def max_workspaces(self):
        """Limite de workspaces: Free=1, Mensal=3, Anual=Ilimitado."""
        if self.is_annual:
            return float('inf')
        if self.is_pro:  # MONTHLY_PRO
            return 3
        return 1

    @property
    def max_transactions_month(self):
        """Limite de lançamentos no mês: Free=30, Mensal=45, Anual=Ilimitado."""
        if self.is_annual:
            return float('inf')
        if self.is_pro:  # MONTHLY_PRO
            return 45
        return 30

    @property
    def max_categories(self):
        """Limite de categorias por workspace: Free=8, Mensal=12, Anual=Ilimitado."""
        if self.is_annual:
            return float('inf')
        if self.is_pro:  # MONTHLY_PRO
            return 12
        return 8

    @property
    def max_exports_month(self):
        """Limite de exportações (PDF/CSV) no mês: Free=1, Mensal=2, Anual=Ilimitado."""
        if self.is_annual:
            return float('inf')
        if self.is_pro:  # MONTHLY_PRO
            return 2
        return 1


class ExportLog(models.Model):
    EXPORT_TYPE_CHOICES = [
        ('PDF', 'Relatório em PDF'),
        ('CSV', 'Planilha em CSV'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_logs')
    export_type = models.CharField(max_length=10, choices=EXPORT_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Exportação'
        verbose_name_plural = 'Logs de Exportações'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.export_type} em {self.created_at.strftime('%d/%m/%Y %H:%M')}"


# Signal: Cria automaticamente uma assinatura gratuita para qualquer novo usuário cadastrado
@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    if created:
        Subscription.objects.create(user=instance, plan='FREE', status='ACTIVE')