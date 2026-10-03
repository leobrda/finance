import resend
import json
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from .models import UserPreference
from .forms import RegisterForm, UserProfileForm, CustomPasswordChangeForm
from .services import setup_new_user_workspaces


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            setup_new_user_workspaces(user)
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def request_password_reset_view(request):
    email_sent = False
    user_found = False

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email__iexact=email).first()

        if user:
            user_found = True
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            path = reverse('password_reset_confirm_direct', kwargs={'uidb64': uid, 'token': token})
            reset_url = request.build_absolute_uri(path)

            resend.api_key = getattr(settings, 'RESEND_API_KEY', '')

            try:
                resend.Emails.send({
                    "from": settings.DEFAULT_FROM_EMAIL,
                    "to": user.email,
                    "subject": "[FIN. FINANCE] Redefinição de Senha",
                    "html": f"""
                    <div style="font-family: 'Courier New', monospace; padding: 24px; border: 3px solid #000; max-width: 520px; background: #FFF;">
                        <div style="background: #FFE600; padding: 12px; border: 2px solid #000; margin-bottom: 20px;">
                            <h1 style="margin: 0; font-size: 20px; text-transform: uppercase;">FIN. FINANCE</h1>
                        </div>
                        <h2 style="font-size: 16px; text-transform: uppercase;">Recuperação de Senha</h2>
                        <p style="font-size: 13px; line-height: 1.5; color: #222;">
                            Olá <strong>{user.first_name or user.username}</strong>,<br>
                            Recebemos uma solicitação para redefinir sua senha de acesso.
                        </p>
                        <div style="margin: 24px 0;">
                            <a href="{reset_url}" style="display: block; text-align: center; background: #000; color: #FFF; padding: 12px; font-weight: bold; text-decoration: none; border: 2px solid #000; text-transform: uppercase;">
                                Clique aqui para criar nova senha →
                            </a>
                        </div>
                        <p style="font-size: 11px; color: #777; margin-top: 20px;">
                            Se você não solicitou essa redefinição, apenas desconsidere esta mensagem.
                        </p>
                    </div>
                    """
                })
                email_sent = True
            except Exception as e:
                print(f"Erro ao enviar via Resend: {e}")
                email_sent = False

    return render(request, 'accounts/password_reset_request.html', {
        'submitted': request.method == 'POST',
        'user_found': user_found,
        'email_sent': email_sent
    })


@login_required
def profile_view(request):
    profile_form = UserProfileForm(instance=request.user)
    password_form = CustomPasswordChangeForm(user=request.user)

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Perfil atualizado com sucesso!")
                return redirect('profile')

        elif 'change_password' in request.POST:
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Senha alterada com sucesso!")
                return redirect('profile')

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form
    })


@login_required
@require_POST
def update_theme_preferences(request):
    try:
        user_sub = getattr(request.user, 'subscription', None)
        is_pro = user_sub.is_pro if user_sub else False

        data = json.loads(request.body)
        pref, _ = UserPreference.objects.get_or_create(user=request.user)

        # Modo claro / escuro permanece disponível para todos
        if 'theme_mode' in data and data['theme_mode']:
            pref.theme_mode = data['theme_mode']

        # Personalização de cores exclusiva para usuários PRO
        if is_pro:
            if 'accent_primary' in data and data['accent_primary']:
                pref.accent_primary = data['accent_primary']

            if 'accent_secondary' in data and data['accent_secondary']:
                pref.accent_secondary = data['accent_secondary']
        else:
            if 'accent_primary' in data or 'accent_secondary' in data:
                pref.save()
                return JsonResponse({
                    'status': 'error',
                    'message': 'Recurso Exclusivo PRO: A personalização de paletas e cores está disponível apenas nos planos Mensal e Anual.'
                }, status=403)

        pref.save()
        return JsonResponse({'status': 'success', 'message': 'Preferências salvas com sucesso!'})
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)