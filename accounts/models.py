from django.db import models
from django.contrib.auth.models import User

class Workspace(models.Model):
    WORKSPACE_TYPE_CHOICES = [
        ('BUSINESS', 'Salão de Beleza / PJ'),
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