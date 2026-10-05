import resend
import json
from datetime import date, timedelta
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse

from .models import UserPreference, PushSubscription, Subscription
from .forms import RegisterForm, UserProfileForm, CustomPasswordChangeForm
from .services import setup_new_user_workspaces
from .services.payment_service import get_mp_sdk, create_pix_payment_annual, create_monthly_subscription_preference


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    plan_intent = request.GET.get('plan') or request.POST.get('plan_intent', '')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            setup_new_user_workspaces(user)
            login(request, user)

            # Redirecionamento direto ao checkout caso o usuário tenha clicado em um plano na landing page
            if plan_intent == 'annual':
                return redirect('checkout_annual_pix')
            elif plan_intent == 'monthly':
                return redirect('checkout_monthly')

            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {
        'form': form,
        'plan_intent': plan_intent
    })


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

    has_push = PushSubscription.objects.filter(user=request.user).exists()
    vapid_key = getattr(settings, 'VAPID_PUBLIC_KEY', '')

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'has_push': has_push,
        'vapid_public_key': vapid_key,
    })


@login_required
@require_POST
def update_theme_preferences(request):
    try:
        user_sub = getattr(request.user, 'subscription', None)
        is_pro = user_sub.is_pro if user_sub else False

        data = json.loads(request.body)
        pref, _ = UserPreference.objects.get_or_create(user=request.user)

        if 'theme_mode' in data and data['theme_mode']:
            pref.theme_mode = data['theme_mode']

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


@login_required
@require_POST
def save_push_subscription(request):
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        if not endpoint or not p256dh or not auth:
            return JsonResponse({'status': 'error', 'message': 'Dados de inscrição incompletos.'}, status=400)

        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh': p256dh,
                'auth': auth,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255]
            }
        )
        return JsonResponse({'status': 'success', 'message': 'Dispositivo registrado com sucesso!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
def toggle_email_morning_notification(request):
    pref, _ = UserPreference.objects.get_or_create(user=request.user)
    pref.notify_email_morning = not pref.notify_email_morning
    pref.save(update_fields=['notify_email_morning'])
    return JsonResponse({'status': 'success', 'enabled': pref.notify_email_morning})


# ============================================================
# CHECKOUT & PLANOS MERCADO PAGO
# ============================================================

@login_required
def pricing_view(request):
    """Renderiza a página neobrutalista de comparação de planos."""
    sub, _ = Subscription.objects.get_or_create(user=request.user)
    return render(request, 'accounts/pricing.html', {
        'subscription': sub
    })


@login_required
def checkout_monthly_view(request):
    """Inicia o checkout do plano Mensal PRO (R$ 9,90)."""
    result = create_monthly_subscription_preference(request.user, request)
    if result.get('success') and result.get('init_point'):
        return redirect(result['init_point'])

    messages.error(request, f"Mercado Pago: {result.get('error', 'Erro ao iniciar assinatura mensal')}")
    return render(request, 'accounts/checkout_pix.html', {
        'pix_data': result,
        'plan_name': 'Mensal PRO (R$ 9,90/mês)'
    })


@login_required
def checkout_annual_pix_view(request):
    """Inicia o checkout do plano Anual PRO (R$ 79,90) via Pix/Preferência."""
    result = create_pix_payment_annual(request.user, request)
    if result.get('success') and result.get('init_point'):
        return redirect(result['init_point'])

    messages.error(request, f"Mercado Pago: {result.get('error', 'Erro ao gerar checkout Pix')}")
    return render(request, 'accounts/checkout_pix.html', {
        'pix_data': result,
        'plan_name': 'Anual PRO (R$ 79,90/ano)'
    })


@login_required
def simulate_pro_activation(request):
    """Rota de conveniência para desenvolvimento: ativa o plano ANUAL PRO instantaneamente."""
    sub, _ = Subscription.objects.get_or_create(user=request.user)
    sub.plan = 'ANNUAL_PRO'
    sub.status = 'ACTIVE'
    sub.starts_at = date.today()
    sub.expires_at = date.today() + timedelta(days=365)
    sub.gateway_subscription_id = 'SIMULATED_PRO_LOCAL'
    sub.save()
    messages.success(request, "🎉 Sucesso! Sua conta foi atualizada para o Plano Anual PRO!")
    return redirect('profile')


@csrf_exempt
def mercadopago_webhook(request):
    """Webhook para confirmação em tempo real de pagamentos Pix e assinaturas do Mercado Pago."""
    if request.method != 'POST':
        return HttpResponse(status=405)

    topic = request.GET.get('topic') or request.GET.get('type')
    resource_id = request.GET.get('id') or request.GET.get('data.id')

    if not resource_id:
        try:
            body_data = json.loads(request.body)
            resource_id = body_data.get('data', {}).get('id')
            topic = body_data.get('type') or topic
        except Exception:
            pass

    if not resource_id:
        return HttpResponse(status=200)

    try:
        sdk = get_mp_sdk()

        # 1. Notificação de Pagamento Pix / Cartão Único
        if topic == 'payment':
            payment_info = sdk.payment().get(resource_id).get('response', {})
            status = payment_info.get('status')
            ext_ref = payment_info.get('external_reference', '')

            if status == 'approved' and ext_ref.startswith('USER_'):
                parts = ext_ref.split('_')
                user_id = int(parts[1])
                plan_type = 'ANNUAL_PRO' if 'ANNUAL' in ext_ref else 'MONTHLY_PRO'

                sub = Subscription.objects.filter(user_id=user_id).first()
                if sub:
                    sub.plan = plan_type
                    sub.status = 'ACTIVE'
                    sub.starts_at = date.today()
                    sub.expires_at = date.today() + (
                        timedelta(days=365) if plan_type == 'ANNUAL_PRO' else timedelta(days=30))
                    sub.gateway_customer_id = str(payment_info.get('payer', {}).get('id', ''))
                    sub.gateway_subscription_id = str(resource_id)
                    sub.save()

        # 2. Notificação de Assinatura Recorrente (Preapproval)
        elif topic in ['subscription_preapproval', 'preapproval']:
            preapproval_info = sdk.preapproval().get(resource_id).get('response', {})
            status = preapproval_info.get('status')
            ext_ref = preapproval_info.get('external_reference', '')

            if status == 'authorized' and ext_ref.startswith('USER_'):
                user_id = int(ext_ref.split('_')[1])
                sub = Subscription.objects.filter(user_id=user_id).first()
                if sub:
                    sub.plan = 'MONTHLY_PRO'
                    sub.status = 'ACTIVE'
                    sub.starts_at = date.today()
                    sub.expires_at = date.today() + timedelta(days=30)
                    sub.gateway_subscription_id = str(resource_id)
                    sub.save()

    except Exception as e:
        print(f"Erro no webhook do Mercado Pago: {e}")

    return HttpResponse(status=200)