from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('transacao/<int:pk>/editar/', views.edit_transaction_view, name='edit_transaction'),
    path('transacao/<int:pk>/excluir/', views.delete_transaction_view, name='delete_transaction')
]