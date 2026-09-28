import os
import re
from django.core.management.base import BaseCommand
from solicitudes.models import Asignatura, UnidadAprendizaje
from pypdf import PdfReader

class Command(BaseCommand):
    help = 'Importa unidades de aprendizaje desde los PDFs en la carpeta indicada'

    def add_arguments(self, parser):
        parser.add_argument('carpeta', type=str, help='Nombre de la carpeta de descriptores')

    def handle(self, *args, **options):
        carpeta = options['carpeta']
        if not os.path.exists(carpeta):
            self.stdout.write(self.style.ERROR(f"La carpeta '{carpeta}' no existe."))
            return

        archivos = [f for f in os.listdir(carpeta) if f.lower().endswith('.pdf')]
        self.stdout.write(f"Procesando {len(archivos)} archivos PDF...")

        unidades_totales_creadas = 0

        # Patrón flexible que reconoce:
        # "UNIDAD DE APRENDIZAJE 1: ...", "UNIDAD DE APRENDIZAJE N° 1: ...", "UNIDAD 1: ...", "Unidad I: ..."
        patron_unidad = r'((?:UNIDAD|Unidad)(?:\s+(?:DE\s+APRENDIZAJE|DE|N[°º]?))*\s*(?:\d+|[I|V|X]+)[\s\:\.\-–—]*[^\n\r]+)'

        for archivo in archivos:
            ruta = os.path.join(carpeta, archivo)
            
            # Extraer código de la asignatura entre paréntesis, ej: (AGB122)
            match = re.search(r'\((.*?)\)', archivo)
            if not match:
                continue
            
            codigo = match.group(1).strip().upper()
            asignaturas = list(Asignatura.objects.filter(codigo=codigo))

            if not asignaturas:
                self.stdout.write(self.style.WARNING(f"Sin asignatura en BD con código {codigo} ({archivo})"))
                continue

            try:
                reader = PdfReader(ruta)
                texto = ""
                for page in reader.pages:
                    texto += (page.extract_text() or "") + "\n"

                # 1. Búsqueda principal con regex flexible
                unidades = re.findall(patron_unidad, texto, re.IGNORECASE)

                # 2. Búsqueda secundaria si el regex no encuentra nada
                if not unidades:
                    for linea in texto.splitlines():
                        l_str = linea.strip()
                        if 'UNIDAD' in l_str.upper() and any(char.isdigit() for char in l_str):
                            unidades.append(l_str)

                # Limpiar duplicados manteniendo el orden original
                unidades_limpias = []
                vistas = set()
                for u in unidades:
                    u_normalizada = ' '.join(u.strip().split())
                    if u_normalizada.lower() not in vistas and len(u_normalizada) > 5:
                        vistas.add(u_normalizada.lower())
                        unidades_limpias.append(u_normalizada[:200])

                unidades_asociadas = 0

                # Asociar las unidades a todas las secciones existentes de esa asignatura
                for asig in asignaturas:
                    for u_nombre in unidades_limpias:
                        _, u_creada = UnidadAprendizaje.objects.get_or_create(
                            asignatura=asig,
                            nombre=u_nombre
                        )
                        if u_creada:
                            unidades_asociadas += 1

                unidades_totales_creadas += unidades_asociadas
                self.stdout.write(f"Asignatura {codigo}: Se asociaron {len(unidades_limpias)} unidades a {len(asignaturas)} sección(es).")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error al procesar {archivo}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"¡Proceso finalizado! Se crearon {unidades_totales_creadas} registros de unidades de aprendizaje."
        ))