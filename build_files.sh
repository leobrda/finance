#!/bin/bash

# Instala as dependências
python3 -m pip install -r requirements.txt

# Cria a pasta de saída para os estáticos
mkdir -p staticfiles_build/static

# Coleta os arquivos estáticos do Django
python3 manage.py collectstatic --no-input --clear