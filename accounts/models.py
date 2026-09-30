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