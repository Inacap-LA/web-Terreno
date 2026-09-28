import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from solicitudes.models import Asignatura, UnidadAprendizaje, AprendizajeEsperado
from pypdf import PdfReader

class Command(BaseCommand):
    help = 'Importa unidades y aprendizajes esperados desde los PDFs de descriptores'

    def add_arguments(self, parser):
        # Permite ejecutar sin parámetros y asumir 'descriptores' por defecto
        parser.add_argument(
            'carpeta',
            nargs='?',
            type=str,
            default='descriptores',
            help='Nombre o ruta de la carpeta con descriptores (por defecto: descriptores)'
        )

    def procesar_texto(self, texto):
        """
        Extrae Unidades y Aprendizajes Esperados soportando descripciones multilínea.
        """
        unidades = []
        unidad_actual = None
        ae_actual = None

        patron_unidad = re.compile(r'^(\d+)\s*\.\s*(.+?)(?:\s*\|.*|$)', re.IGNORECASE)
        patron_ae = re.compile(r'^(\d+\.\d+)\s+(.+)')
        patron_criterio = re.compile(r'^\d+\.\d+\.\d+')

        palabras_ignorar = [
            "APRENDIZAJES ESPERADOS", "CRITERIOS DE EVALUACIÓN", "CONTENIDOS MINIMOS",
            "CONTENIDOS MÍNIMOS", "ACTIVIDADES MINIMAS", "ACTIVIDADES MÍNIMAS",
            "Horas de la Unidad:", "Administrador de Asignaturas", "INACAP", "https://"
        ]

        for linea in texto.splitlines():
            linea = linea.strip()
            if not linea:
                continue

            if any(ignorar in linea for ignorar in palabras_ignorar):
                continue

            # 1. Detectar Unidad de Aprendizaje
            match_unidad = patron_unidad.match(linea)
            if match_unidad:
                num_u = int(match_unidad.group(1))
                nombre_u = match_unidad.group(2).strip()

                if not patron_criterio.match(linea) and len(nombre_u) > 3 and num_u < 20:
                    if ae_actual and unidad_actual:
                        unidad_actual['aprendizajes'].append(ae_actual)
                        ae_actual = None

                    unidad_actual = {
                        'numero': num_u,
                        'nombre': nombre_u[:250],
                        'aprendizajes': []
                    }
                    unidades.append(unidad_actual)
                    continue

            # 2. Si detecta inicio de Criterio de Evaluación (1.1.1), cierra el AE actual
            if patron_criterio.match(linea):
                if ae_actual and unidad_actual:
                    unidad_actual['aprendizajes'].append(ae_actual)
                    ae_actual = None
                continue

            # 3. Detectar Aprendizaje Esperado (ej: 1.1)
            match_ae = patron_ae.match(linea)
            if match_ae and unidad_actual is not None:
                codigo_cand = match_ae.group(1)
                desc_cand = match_ae.group(2).strip()

                if not patron_criterio.match(codigo_cand):
                    if codigo_cand.startswith(f"{unidad_actual['numero']}."):
                        if ae_actual:
                            unidad_actual['aprendizajes'].append(ae_actual)

                        ae_actual = {
                            'codigo': codigo_cand,
                            'descripcion': desc_cand
                        }
                        continue

            # 4. Concatenar líneas secundarias de la descripción del AE
            if ae_actual is not None and unidad_actual is not None:
                ae_actual['descripcion'] += f" {linea}"

        if ae_actual and unidad_actual:
            unidad_actual['aprendizajes'].append(ae_actual)

        # Limpieza de espacios en blanco múltiples
        for u in unidades:
            for ae in u['aprendizajes']:
                ae['descripcion'] = re.sub(r'\s+', ' ', ae['descripcion']).strip()

        return unidades

    def handle(self, *args, **options):
        nombre_carpeta = options['carpeta']

        # Localizar la carpeta desde la raíz del proyecto Django
        if hasattr(settings, 'BASE_DIR'):
            ruta_carpeta = os.path.join(settings.BASE_DIR, nombre_carpeta)
            if not os.path.exists(ruta_carpeta):
                ruta_carpeta = os.path.abspath(nombre_carpeta)
        else:
            ruta_carpeta = os.path.abspath(nombre_carpeta)

        if not os.path.exists(ruta_carpeta):
            self.stdout.write(self.style.ERROR(f"❌ La carpeta '{ruta_carpeta}' no existe."))
            return

        archivos = [f for f in os.listdir(ruta_carpeta) if f.lower().endswith('.pdf')]
        self.stdout.write(self.style.SUCCESS(f"📂 Se encontraron {len(archivos)} archivos PDF en '{ruta_carpeta}'...\n"))

        unidades_totales = 0
        aprendizajes_totales = 0

        for archivo in archivos:
            ruta = os.path.join(ruta_carpeta, archivo)
            
            # Buscar el código entre paréntesis en el nombre del archivo (ej: "(ASAS03)")
            match_cod = re.search(r'\((.*?)\)', archivo)
            codigo = match_cod.group(1).strip().upper() if match_cod else None

            try:
                reader = PdfReader(ruta)
                texto = "\n".join([page.extract_text() or "" for page in reader.pages])

                # Buscar código en el texto del PDF si no venía en el nombre del archivo
                if not codigo:
                    match_pdf_cod = re.search(r'\b([A-Z]{3,5}\d{2,4})\b', texto)
                    if match_pdf_cod:
                        codigo = match_pdf_cod.group(1).upper()

                if not codigo:
                    self.stdout.write(self.style.WARNING(f"⚠️ No se pudo determinar el código para {archivo}"))
                    continue

                asignaturas = list(Asignatura.objects.filter(codigo=codigo))

                if not asignaturas:
                    self.stdout.write(self.style.WARNING(f"⚠️ Sin asignatura registrada en BD con código '{codigo}' ({archivo})"))
                    continue

                datos_extraidos = self.procesar_texto(texto)

                if not datos_extraidos:
                    self.stdout.write(self.style.WARNING(f"⚠️ No se encontraron unidades con formato válido en {archivo}"))
                    continue

                unidades_creadas = 0
                aes_creados = 0

                for asig in asignaturas:
                    # Limpieza preventiva para actualizar con datos limpios
                    asig.unidades.all().delete()

                    for d_unidad in datos_extraidos:
                        unidad_obj = UnidadAprendizaje.objects.create(
                            asignatura=asig,
                            numero=d_unidad['numero'],
                            nombre=d_unidad['nombre']
                        )
                        unidades_creadas += 1

                        for d_ae in d_unidad['aprendizajes']:
                            AprendizajeEsperado.objects.create(
                                unidad=unidad_obj,
                                codigo=d_ae['codigo'],
                                descripcion=d_ae['descripcion']
                            )
                            aes_creados += 1

                unidades_totales += unidades_creadas
                aprendizajes_totales += aes_creados
                
                self.stdout.write(self.style.SUCCESS(
                    f"✅ [{codigo}] Procesadas {len(datos_extraidos)} unidades y {sum(len(u['aprendizajes']) for u in datos_extraidos)} AEs "
                    f"para {len(asignaturas)} sección(es)."
                ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error al procesar {archivo}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\n🎉 ¡Proceso finalizado! Se registraron {unidades_totales} unidades y {aprendizajes_totales} aprendizajes esperados."
        ))