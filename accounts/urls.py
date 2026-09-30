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
]