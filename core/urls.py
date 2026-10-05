from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from finances import views as finance_views
from accounts import views as account_views

urlpatterns = [
    # 1. Raiz limpa (http://127.0.0.1:8000/):
    # Usa a landing_page_view do finances (se logado vai pro dashboard; se deslogado, exibe a landing page)
    path('', finance_views.landing_page_view, name='landing'),

    # 2. Rotas do sistema
    path('admin/', admin.site.urls),
    path('auth/', include('accounts.urls')),
    path('dashboard/', include('finances.urls')),
    path('planos/', account_views.pricing_view, name='pricing'),
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw_js'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)