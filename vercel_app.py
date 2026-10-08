import os
from django.core.wsgi import get_wsgi_application

# Ajuste 'core.settings' para o caminho real do seu settings.py se seu projeto tiver outro nome
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = get_wsgi_application()