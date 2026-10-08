import mercadopago
from django.conf import settings


def get_mp_sdk():
    access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', '')
    if not access_token:
        raise ValueError("MERCADOPAGO_ACCESS_TOKEN não configurado no settings/.env")
    return mercadopago.SDK(access_token)


def _get_base_url(request):
    host = request.get_host()
    # Em produção (Vercel) sempre força https://
    if not any(h in host for h in ['127.0.0.1', 'localhost']):
        return f"https://{host}"
    return request.build_absolute_uri('/')[:-1]


"""def _get_redirect_url(response, access_token):
    # Se estiver usando token de teste oficial (TEST-...), usa sandbox
    if access_token.startswith('TEST-'):
        return response.get("sandbox_init_point") or response.get("init_point")
    # Caso use credenciais de produção (APP_USR-...), usa init_point padrão
    return response.get("init_point") or response.get("sandbox_init_point")"""

def _get_redirect_url(response, access_token):
    # Enquanto estiver a testar com credenciais de teste, prioriza sempre o sandbox_init_point
    return response.get("sandbox_init_point") or response.get("init_point")


def create_pix_payment_annual(user, request):
    """
    Cria a Preferência oficial de pagamento no Mercado Pago para o Plano Anual (R$ 79,90).
    Abre o Checkout Pro nativo com suporte a PIX, Cartão e Boleto.
    """
    access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', '')
    sdk = get_mp_sdk()

    payer_email = user.email if (user.email and '@' in user.email and not user.email.endswith('@testuser.com')) else f"user_{user.id}@testuser.com"

    preference_data = {
        "items": [
            {
                "id": "PLAN_ANNUAL_PRO",
                "title": "FIN. FINANCE — Plano Anual PRO",
                "description": "1 ano de acesso completo com Workspaces e lançamentos ilimitados",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": 79.90
            }
        ],
        "payer": {
            "name": user.first_name or user.username,
            "surname": user.last_name or "Finance",
            "email": payer_email
        },
        "external_reference": f"USER_{user.id}_PLAN_ANNUAL",
    }

    host = request.get_host()
    if not any(h in host for h in ['127.0.0.1', 'localhost']):
        base_url = _get_base_url(request)
        preference_data["back_urls"] = {
            "success": f"{base_url}/auth/perfil/?status=payment_success",
            "failure": f"{base_url}/planos/?status=payment_failure",
            "pending": f"{base_url}/auth/perfil/?status=payment_pending"
        }
        preference_data["auto_return"] = "approved"

    result = sdk.preference().create(preference_data)
    response = result.get("response", {})

    if result.get("status") in [200, 201]:
        return {
            "success": True,
            "preference_id": response.get("id"),
            "init_point": _get_redirect_url(response, access_token),
        }

    return {
        "success": False,
        "error": response.get("message", "Falha ao gerar cobrança Anual no Mercado Pago.")
    }


def create_monthly_subscription_preference(user, request):
    """
    Cria a Preferência oficial de checkout para o Plano Mensal PRO (R$ 9,90).
    """
    access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', '')
    sdk = get_mp_sdk()

    payer_email = user.email if (user.email and '@' in user.email and not user.email.endswith('@testuser.com')) else f"user_{user.id}@testuser.com"

    preference_data = {
        "items": [
            {
                "id": "PLAN_MONTHLY_PRO",
                "title": "FIN. FINANCE — Plano Mensal PRO",
                "description": "Assinatura mensal com múltiplos workspaces e categorias ilimitadas",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": 9.90
            }
        ],
        "payer": {
            "name": user.first_name or user.username,
            "surname": user.last_name or "Finance",
            "email": payer_email
        },
        "external_reference": f"USER_{user.id}_PLAN_MONTHLY",
    }

    host = request.get_host()
    if not any(h in host for h in ['127.0.0.1', 'localhost']):
        base_url = _get_base_url(request)
        preference_data["back_urls"] = {
            "success": f"{base_url}/auth/perfil/?status=payment_success",
            "failure": f"{base_url}/planos/?status=payment_failure",
            "pending": f"{base_url}/auth/perfil/?status=payment_pending"
        }
        preference_data["auto_return"] = "approved"

    result = sdk.preference().create(preference_data)
    response = result.get("response", {})

    if result.get("status") in [200, 201]:
        return {
            "success": True,
            "preference_id": response.get("id"),
            "init_point": _get_redirect_url(response, access_token),
        }

    return {
        "success": False,
        "error": response.get("message", "Falha ao gerar assinatura Mensal no Mercado Pago.")
    }