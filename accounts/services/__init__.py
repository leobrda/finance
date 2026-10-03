# accounts/services/__init__.py
from accounts.models import Workspace

def setup_new_user_workspaces(user):
    """Cria os workspaces padrão para novos usuários cadastrados."""
    Workspace.objects.get_or_create(
        user=user,
        name='Finanças Pessoais',
        workspace_type='PERSONAL'
    )