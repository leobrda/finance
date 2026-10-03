from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Sum

from finances.models import Transaction, RecurringExpense
from accounts.services.notification_service import send_morning_email_resend, send_web_push_notification


class Command(BaseCommand):
    help = 'Processa e dispara o Resumo Matinal por E-mail (Resend) e Web Push'

    def handle(self, *args, **options):
        today = date.today()
        today_str = today.strftime('%d/%m/%Y')
        users = User.objects.filter(is_active=True).select_related('preferences')

        self.stdout.write(f"Iniciando rotina matinal para {users.count()} usuário(s)...")

        for user in users:
            workspaces = user.workspaces.all()
            if not workspaces.exists():
                continue

            # 1. Transações pendentes com vencimento para hoje
            trans_hoje = Transaction.objects.filter(
                workspace__in=workspaces,
                transaction_date=today,
                status='PENDING'
            )

            total_expense = trans_hoje.filter(category__category_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
            total_income = trans_hoje.filter(category__category_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

            # 2. Assinaturas / Despesas fixas vencendo hoje
            recorrentes_hoje = RecurringExpense.objects.filter(
                workspace__in=workspaces,
                due_day=today.day,
                is_active=True
            )

            transactions_list = []
            for t in trans_hoje:
                transactions_list.append({
                    'description': t.description,
                    'amount': float(t.amount),
                    'is_income': t.category.category_type == 'INCOME' if t.category else False
                })

            context_data = {
                'today_str': today_str,
                'total_expense': total_expense,
                'total_income': total_income,
                'transactions': transactions_list,
            }

            # Envio 1: E-mail via Resend (se o usuário marcou a opção)
            pref = getattr(user, 'preferences', None)
            if pref and pref.notify_email_morning:
                send_morning_email_resend(user, context_data)

            # Envio 2: Notificação Web Push para dispositivos cadastrados
            if user.push_subscriptions.exists():
                if total_expense > 0:
                    body_text = f"Você tem R$ {total_expense:.2f} em contas para pagar hoje."
                elif total_income > 0:
                    body_text = f"Você tem R$ {total_income:.2f} previsto a receber hoje."
                else:
                    body_text = "Nenhuma conta pendente para hoje! Suas finanças estão em dia."

                send_web_push_notification(
                    user=user,
                    title="☀️ FIN. Resumo de Hoje",
                    body=body_text,
                    url="/dashboard/"
                )

        self.stdout.write(self.style.SUCCESS("Rotina de resumos matinais finalizada com sucesso!"))