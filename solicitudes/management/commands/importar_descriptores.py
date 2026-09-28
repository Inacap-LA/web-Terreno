import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from solicitudes.models import Asignatura, UnidadAprendizaje, AprendizajeEsperado
from pypdf import PdfReader

class Command(BaseCommand):
    help = 'Importa unidades y aprendizajes esperados desde los PDFs de descriptores'

    def add_arguments(self, parser):
        parser.add_argument(
            'carpeta',
            nargs='?',
            type=str,
            default='descriptores',
            help='Nombre o ruta de la carpeta con descriptores (por defecto: descriptores)'
        )

    def _guardar_ae(self, lista_aprendizajes, ae):
        """Limpia espacios extra y evita aprendizajes duplicados en la misma unidad."""
        ae['descripcion'] = re.sub(r'\s+', ' ', ae['descripcion']).strip()
        if not any(item['codigo'] == ae['codigo'] for item in lista_aprendizajes):
            lista_aprendizajes.append(ae)

    def procesar_texto(self, texto):
        unidades_dict = {}  # Agrupa las unidades por número para evitar duplicados
        unidad_actual_num = None
        ae_actual = None

        patron_unidad = re.compile(r'^(\d+)\s*\.\s*(.+)', re.IGNORECASE)
        # Lookahead negativo (?!\.\d+) para asegurar que captura "1.1" pero NO "1.1.1"
        patron_ae = re.compile(r'^(\d+\.\d+)(?!\.\d+)\s+(.+)')
        patron_criterio = re.compile(r'^\d+\.\d+\.\d+')

        palabras_ignorar = [
            "APRENDIZAJES ESPERADOS", "CRITERIOS DE EVALUACIÓN", "CONTENIDOS MINIMOS",
            "CONTENIDOS MÍNIMOS", "ACTIVIDADES MINIMAS", "ACTIVIDADES MÍNIMAS",
            "Horas de la Unidad:", "Administrador de Asignaturas", "INACAP", "https://",
            "EVALUACIÓN:", "ESTRATEGIAS", "SISTEMA DE EVALUACIÓN"
        ]

        for linea in texto.splitlines():
            linea = linea.strip()
            if not linea:
                continue

            if any(ignorar in linea for ignorar in palabras_ignorar):
                if ae_actual and unidad_actual_num in unidades_dict:
                    self._guardar_ae(unidades_dict[unidad_actual_num]['aprendizajes'], ae_actual)
                    ae_actual = None
                continue

            # 1. Detectar Criterio de Evaluación (ej: 1.1.1)
            if patron_criterio.match(linea):
                if ae_actual and unidad_actual_num in unidades_dict:
                    self._guardar_ae(unidades_dict[unidad_actual_num]['aprendizajes'], ae_actual)
                    ae_actual = None
                continue

            # 2. Detectar Aprendizaje Esperado (ej: 1.1)
            match_ae = patron_ae.match(linea)
            if match_ae:
                codigo_cand = match_ae.group(1)
                desc_cand = match_ae.group(2).strip()

                num_u_from_code = int(codigo_cand.split('.')[0])
                unidad_actual_num = num_u_from_code

                if unidad_actual_num not in unidades_dict:
                    unidades_dict[unidad_actual_num] = {
                        'numero': unidad_actual_num,
                        'nombre': f"Unidad {unidad_actual_num}",
                        'aprendizajes': []
                    }

                if ae_actual:
                    self._guardar_ae(unidades_dict[unidad_actual_num]['aprendizajes'], ae_actual)

                ae_actual = {
                    'codigo': codigo_cand,
                    'descripcion': desc_cand
                }
                continue

            # 3. Detectar Unidad de Aprendizaje (ej: 1. Aportes nutricionales..)
            match_unidad = patron_unidad.match(linea)
            if match_unidad and not patron_criterio.match(linea):
                num_u = int(match_unidad.group(1))
                nombre_raw = match_unidad.group(2).strip()
                
                nombre_u = re.sub(r'\s*\|.*$', '', nombre_raw).strip().rstrip('.')
                nombre_u = re.sub(r'\s+', ' ', nombre_u)

                if len(nombre_u) > 2 and num_u < 20:
                    if ae_actual and unidad_actual_num in unidades_dict:
                        self._guardar_ae(unidades_dict[unidad_actual_num]['aprendizajes'], ae_actual)
                        ae_actual = None

                    unidad_actual_num = num_u

                    if num_u not in unidades_dict:
                        unidades_dict[num_u] = {
                            'numero': num_u,
                            'nombre': nombre_u[:250],
                            'aprendizajes': []
                        }
                    else:
                        # Conservar el nombre más largo y descriptivo
                        if len(nombre_u) > len(unidades_dict[num_u]['nombre']):
                            unidades_dict[num_u]['nombre'] = nombre_u[:250]
                    continue

            # 4. Concatenar texto secundario de descripciones multilínea del AE
            if ae_actual is not None:
                ae_actual['descripcion'] += f" {linea}"

        if ae_actual and unidad_actual_num in unidades_dict:
            self._guardar_ae(unidades_dict[unidad_actual_num]['aprendizajes'], ae_actual)

        return sorted(unidades_dict.values(), key=lambda x: x['numero'])

    def handle(self, *args, **options):
        nombre_carpeta = options['carpeta']

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
        self.stdout.write(self.style.SUCCESS(f"📂 Procesando {len(archivos)} archivos PDF en '{ruta_carpeta}'...\n"))

        unidades_totales = 0
        aprendizajes_totales = 0

        for archivo in archivos:
            ruta = os.path.join(ruta_carpeta, archivo)
            
            match_cod = re.search(r'\((.*?)\)', archivo)
            codigo = match_cod.group(1).strip().upper() if match_cod else None

            try:
                reader = PdfReader(ruta)
                texto = "\n".join([page.extract_text() or "" for page in reader.pages])

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
                    self.stdout.write(self.style.WARNING(f"⚠️ No se encontraron unidades válidas en {archivo}"))
                    continue

                unidades_creadas = 0
                aes_creados = 0

                for asig in asignaturas:
                    # Limpieza total de unidades de la asignatura antes de la reinserción
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
                
                total_aes_doc = sum(len(u['aprendizajes']) for u in datos_extraidos)
                self.stdout.write(self.style.SUCCESS(
                    f"✅ [{codigo}] Procesadas {len(datos_extraidos)} unidades y {total_aes_doc} AEs "
                    f"para {len(asignaturas)} sección(es)."
                ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error al procesar {archivo}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\n🎉 ¡Proceso finalizado! Se registraron {unidades_totales} unidades y {aprendizajes_totales} aprendizajes esperados."
        ))