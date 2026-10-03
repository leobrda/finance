import json
import resend
from django.conf import settings
from pywebpush import webpush, WebPushException
from accounts.models import PushSubscription


def send_morning_email_resend(user, context_data):
    """
    Envia o e-mail matinal diário com o resumo financeiro neobrutalista via Resend.
    """
    resend.api_key = getattr(settings, 'RESEND_API_KEY', '')
    if not resend.api_key or not user.email:
        return False

    today_str = context_data.get('today_str', '')
    total_expense = context_data.get('total_expense', 0)
    total_income = context_data.get('total_income', 0)
    transactions = context_data.get('transactions', [])

    trans_rows = ""
    for t in transactions[:6]:
        signal = "+" if t['is_income'] else "-"
        color = "#10B981" if t['is_income'] else "#FF4A22"
        trans_rows += f"""
        <tr style="border-bottom: 2px solid #000000;">
            <td style="padding: 10px 8px; font-weight: 700; text-transform: uppercase;">{t['description']}</td>
            <td style="padding: 10px 8px; font-family: monospace; font-weight: 800; color: {color}; text-align: right;">{signal} R$ {t['amount']:.2f}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FIN. Resumo Matinal</title>
    </head>
    <body style="margin: 0; padding: 24px; background-color: #E8E8ED; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #000000;">
        <div style="max-width: 520px; margin: 0 auto; background: #FFFFFF; border: 4px solid #000000; box-shadow: 6px 6px 0px 0px #000000; padding: 24px;">

            <!-- Cabeçalho Neobrutalista -->
            <div style="background-color: #FFE600; border: 2px solid #000000; padding: 12px; margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 24px; text-transform: uppercase; font-weight: 900; letter-spacing: -1px; color: #000000;">FIN. FINANCE</h1>
                <span style="font-size: 11px; font-family: monospace; font-weight: 800; color: #000000;">RESUMO MATINAL • {today_str}</span>
            </div>

            <p style="font-size: 14px; font-weight: 800; text-transform: uppercase; margin: 0 0 6px 0;">Bom dia, {user.first_name or user.username}!</p>
            <p style="font-size: 12px; color: #555555; text-transform: uppercase; margin: 0 0 16px 0;">Aqui está o seu panorama financeiro previsto para hoje:</p>

            <!-- Cards de Totalizador -->
            <table style="width: 100%; border-collapse: separate; border-spacing: 8px 0; margin-bottom: 16px;">
                <tr>
                    <td style="border: 2px solid #000000; padding: 12px; background: #FFFFFF; width: 50%;">
                        <span style="font-size: 10px; font-weight: 800; text-transform: uppercase; color: #666666; display: block;">A Pagar Hoje</span>
                        <strong style="font-size: 18px; font-family: monospace; color: #FF4A22; font-weight: 900;">R$ {total_expense:.2f}</strong>
                    </td>
                    <td style="border: 2px solid #000000; padding: 12px; background: #FFFFFF; width: 50%;">
                        <span style="font-size: 10px; font-weight: 800; text-transform: uppercase; color: #666666; display: block;">A Receber Hoje</span>
                        <strong style="font-size: 18px; font-family: monospace; color: #10B981; font-weight: 900;">R$ {total_income:.2f}</strong>
                    </td>
                </tr>
            </table>

            <!-- Lista de Contas -->
            {f'<table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px;">{trans_rows}</table>' if trans_rows else '<div style="font-size: 12px; font-weight: 800; text-align: center; padding: 14px; background: #F6F6F2; border: 2px solid #000000; text-transform: uppercase;">Nenhum vencimento pendente para hoje! Caixa em dia. ✅</div>'}

            <!-- Ação Principal -->
            <div style="margin-top: 24px; text-align: center;">
                <a href="https://finfinance.com.br/dashboard" style="display: block; background: #000000; color: #FFFFFF; padding: 14px; font-weight: 900; text-transform: uppercase; text-decoration: none; border: 2px solid #000000; font-size: 12px; box-shadow: 3px 3px 0px 0px rgba(0,0,0,0.4);">
                    Acessar Meu Painel →
                </a>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        resend.Emails.send({
            "from": getattr(settings, 'DEFAULT_FROM_EMAIL', 'FIN. FINANCE <onboarding@resend.dev>'),
            "to": user.email,
            "subject": f"[FIN.] Resumo Matinal: Contas e Receitas de Hoje ({today_str})",
            "html": html_content
        })
        return True
    except Exception as e:
        print(f"Erro ao disparar Resend para {user.email}: {e}")
        return False


def send_web_push_notification(user, title, body, url="/dashboard/"):
    """
    Dispara notificações Web Push para todos os navegadores/dispositivos registados do utilizador.
    Se a inscrição do dispositivo estiver expirada (HTTP 404/410), ela é removida automaticamente.
    """
    vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_admin = getattr(settings, 'VAPID_ADMIN_EMAIL', 'mailto:contato@finfinance.com.br')

    if not vapid_private:
        return 0

    subscriptions = PushSubscription.objects.filter(user=user)
    success_count = 0

    payload = json.dumps({
        'title': title,
        'body': body,
        'url': url
    })

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    }
                },
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims={"sub": vapid_admin}
            )
            success_count += 1
        except WebPushException as ex:
            # Token expirado ou revogado no browser -> limpa da base
            if ex.response is not None and ex.response.status_code in [404, 410]:
                sub.delete()
        except Exception as e:
            print(f"Erro ao enviar push para dispositivo de {user.username}: {e}")

    return success_count