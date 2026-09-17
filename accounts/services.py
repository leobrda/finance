from accounts.models import Workspace
from finances.models import Category

def setup_new_user_workspaces(user):
    salon_workspace = Workspace.objects.create(
        user=user,
        name="Salão de Beleza",
        workspace_type="BUSINESS"
    )
    salon_categories = [
        ("Serviços de Cabelo", "INCOME"),
        ("Manicure / Pedicure", "INCOME"),
        ("Venda de Cosméticos", "INCOME"),
        ("Produtos e Insumos", "EXPENSE"),
        ("Aluguel e Ponto", "EXPENSE"),
        ("Energia e Água do Salão", "EXPENSE"),
    ]
    for name, cat_type in salon_categories:
        Category.objects.create(workspace=salon_workspace, name=name, category_type=cat_type)

    personal_workspace = Workspace.objects.create(
        user=user,
        name="Finanças Pessoais",
        workspace_type="PERSONAL"
    )
    personal_categories = [
        ("Pró-Labore / Retirada", "INCOME"),
        ("Supermercado", "EXPENSE"),
        ("Moradia", "EXPENSE"),
        ("Saúde e Lazer", "EXPENSE"),
    ]
    for name, cat_type in personal_categories:
        Category.objects.create(workspace=personal_workspace, name=name, category_type=cat_type)