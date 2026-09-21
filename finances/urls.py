from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('transacao/<int:pk>/editar/', views.edit_transaction_view, name='edit_transaction'),
    path('transacao/<int:pk>/excluir/', views.delete_transaction_view, name='delete_transaction'),
    path('transacao/<int:pk>/status/', views.toggle_transaction_status, name='toggle_transaction_status'),
    path('exportar/csv/', views.export_transactions_csv, name='export_transactions_csv'),
    # Rotas de gestão de categorias
    path('categorias/', views.manage_categories_view, name='manage_categories'),
    path('categorias/<int:pk>/editar/', views.edit_category_view, name='edit_category'),
    path('categorias/<int:pk>/excluir/', views.delete_category_view, name='delete_category'),
]