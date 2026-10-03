from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Workspace, UserPreference, Subscription


# 1. Administração de Workspaces
@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'workspace_type', 'user', 'created_at')
    list_filter = ('workspace_type', 'user')
    search_fields = ('name', 'user__username', 'user__email')


# 2. Seções integradas dentro da tela de detalhes do Usuário
class SubscriptionInline(admin.StackedInline):
    model = Subscription
    can_delete = False
    verbose_name = 'Plano de Assinatura'
    verbose_name_plural = 'Plano de Assinatura'
    extra = 0
    fields = ('plan', 'status', 'starts_at', 'expires_at', 'gateway_customer_id', 'gateway_subscription_id')


class UserPreferenceInline(admin.StackedInline):
    model = UserPreference
    can_delete = False
    verbose_name = 'Preferência de Tema e Cores'
    verbose_name_plural = 'Preferências de Tema e Cores'
    extra = 0
    fields = ('theme_mode', 'accent_primary', 'accent_secondary')


# 3. Customização da listagem padrão de Usuários do Django
class CustomUserAdmin(BaseUserAdmin):
    inlines = (SubscriptionInline, UserPreferenceInline)
    list_display = (
        'username',
        'email',
        'first_name',
        'get_plan_badge',
        'get_status_badge',
        'is_active',
        'date_joined',
    )
    list_filter = (
        'is_active',
        'subscription__plan',
        'subscription__status',
        'date_joined',
    )
    search_fields = ('username', 'email', 'first_name', 'last_name')

    @admin.display(description='Plano Atual')
    def get_plan_badge(self, obj):
        sub = getattr(obj, 'subscription', None)
        return sub.get_plan_display() if sub else 'Sem Assinatura'

    @admin.display(description='Status da Assinatura')
    def get_status_badge(self, obj):
        sub = getattr(obj, 'subscription', None)
        return sub.get_status_display() if sub else '-'


# 4. Tela dedicada e direta para listar e gerenciar todas as Assinaturas
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'starts_at', 'expires_at', 'updated_at')
    list_filter = ('plan', 'status', 'starts_at', 'expires_at')
    search_fields = (
        'user__username',
        'user__email',
        'gateway_customer_id',
        'gateway_subscription_id',
    )
    ordering = ('-updated_at',)


# Re-registra o modelo User com os Inlines e novas colunas
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)