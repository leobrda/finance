from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('cadastro/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Perfil e Alteração de Senha do Usuário Logado
    path('perfil/', views.profile_view, name='profile'),

    # Rotas de redefinição sem depender de e-mail externo
    path('esqueci-senha/', views.request_password_reset_view, name='password_reset_request'),
    path('redefinir-senha/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/auth/login/?reset=success'
        ),
        name='password_reset_confirm_direct'
    ),
    path('api/update-theme-preferences/', views.update_theme_preferences, name='update_theme_preferences'),

    path('api/push/subscribe/', views.save_push_subscription, name='save_push_subscription'),
    path('api/notifications/toggle-email/', views.toggle_email_morning_notification, name='toggle_email_morning'),

    # MONETIZAÇÃO & MERCADO PAGO
    path('planos/', views.pricing_view, name='pricing'),
    path('checkout/mensal/', views.checkout_monthly_view, name='checkout_monthly'),
    path('checkout/anual-pix/', views.checkout_annual_pix_view, name='checkout_annual_pix'),
    path('api/webhooks/mercadopago/', views.mercadopago_webhook, name='mercadopago_webhook'),

    path('simular-ativacao-pro/', views.simulate_pro_activation, name='simulate_pro_activation'),
]