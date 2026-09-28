import os
import django

# Configura el entorno de Django (apunta al settings de tu carpeta 'portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portal.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Lee las credenciales desde variables de entorno o usa valores por defecto
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'orobles@inacap.cl')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin1234')

if not User.objects.filter(username=username).exists():
    print(f"Creando superusuario '{username}'...")
    User.objects.create_superuser(username=username, email=email, password=password)
    print("¡Superusuario creado con éxito!")
else:
    print(f"El superusuario '{username}' ya existe.")