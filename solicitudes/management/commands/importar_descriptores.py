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

    def _limpiar_espacios(self, texto):
        """Remueve saltos de línea y espacios dobles/múltiples."""
        return re.sub(r'\s+', ' ', texto).strip()

    def procesar_texto(self, texto):
        unidades = []
        unidad_actual = None
        ae_actual = None

        # Captura estrictamente las líneas con el formato: "2 . Nombre de Unidad | Horas de la Unidad: ..."
        patron_unidad_encabezado = re.compile(
            r'^(\d+)\s*\.\s*(.+?)\s*\|\s*Horas\s+de\s+la\s+Unidad', 
            re.IGNORECASE
        )
        
        # Captura Aprendizajes Esperados (ej. 1.1, 2.1) ignorando criterios (1.1.1)
        patron_ae = re.compile(r'^(\d+\.\d+)(?!\.\d+)\s+(.+)')
        
        # Captura Criterios de Evaluación (ej. 1.1.1)
        patron_criterio = re.compile(r'^\d+\.\d+\.\d+')

        palabras_ignorar = [
            "APRENDIZAJES ESPERADOS", "CRITERIOS DE EVALUACIÓN", "CONTENIDOS MINIMOS",
            "CONTENIDOS MÍNIMOS", "ACTIVIDADES MINIMAS", "ACTIVIDADES MÍNIMAS",
            "Administrador de Asignaturas", "INACAP", "https://",
            "EVALUACIÓN:", "ESTRATEGIAS", "SISTEMA DE EVALUACIÓN"
        ]

        for linea in texto.splitlines():
            linea = linea.strip()
            if not linea:
                continue

            # 1. Detectar el inicio de Unidad por su encabezado con 'Horas de la Unidad'
            match_unidad = patron_unidad_encabezado.match(linea)
            if match_unidad:
                # Si había un AE acumulándose, lo guardamos antes de cambiar de unidad
                if ae_actual and unidad_actual:
                    ae_actual['descripcion'] = self._limpiar_espacios(ae_actual['descripcion'])
                    unidad_actual['aprendizajes'].append(ae_actual)
                    ae_actual = None

                num_u = int(match_unidad.group(1))
                # Limpiar posibles puntos suspensivos o símbolos finales al final del nombre
                nombre_u = match_unidad.group(2).strip().rstrip('.')
                nombre_u = self._limpiar_espacios(nombre_u)

                unidad_actual = {
                    'numero': num_u,
                    'nombre': nombre_u[:250],
                    'aprendizajes': []
                }
                unidades.append(unidad_actual)
                continue

            # Ignorar palabras clave de títulos de tabla
            if any(ignorar in linea for ignorar in palabras_ignorar):
                if ae_actual and unidad_actual:
                    ae_actual['descripcion'] = self._limpiar_espacios(ae_actual['descripcion'])
                    unidad_actual['aprendizajes'].append(ae_actual)
                    ae_actual = None
                continue

            # 2. Detectar inicio de Criterio de Evaluación (1.1.1) -> Detiene acumulación del AE
            if patron_criterio.match(linea):
                if ae_actual and unidad_actual:
                    ae_actual['descripcion'] = self._limpiar_espacios(ae_actual['descripcion'])
                    unidad_actual['aprendizajes'].append(ae_actual)
                    ae_actual = None
                continue

            # 3. Detectar Aprendizaje Esperado (ej: 1.1, 2.1)
            match_ae = patron_ae.match(linea)
            if match_ae and unidad_actual is not None:
                codigo_cand = match_ae.group(1)
                desc_cand = match_ae.group(2).strip()

                # Garantizar que el AE (ej 2.1) pertenezca a la Unidad actual (ej Unidad 2)
                if codigo_cand.startswith(f"{unidad_actual['numero']}."):
                    if ae_actual:
                        ae_actual['descripcion'] = self._limpiar_espacios(ae_actual['descripcion'])
                        unidad_actual['aprendizajes'].append(ae_actual)

                    ae_actual = {
                        'codigo': codigo_cand,
                        'descripcion': desc_cand
                    }
                    continue

            # 4. Si hay un AE activo, seguir concatenando líneas secundarias
            if ae_actual is not None and unidad_actual is not None:
                ae_actual['descripcion'] += f" {linea}"

        # Guardar el último AE si quedó en memoria
        if ae_actual and unidad_actual:
            ae_actual['descripcion'] = self._limpiar_espacios(ae_actual['descripcion'])
            unidad_actual['aprendizajes'].append(ae_actual)

        return unidades

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
        self.stdout.write(self.style.SUCCESS(f"📂 Procesando {len(archivos)} descriptores PDF desde '{ruta_carpeta}'...\n"))

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
                    self.stdout.write(self.style.WARNING(f"⚠️ No se pudo determinar el código de asignatura en {archivo}"))
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
                    # Limpieza previa de la asignatura
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
                    f"✅ [{codigo}] Extraídas {len(datos_extraidos)} unidades y {total_aes_doc} AEs "
                    f"para {len(asignaturas)} sección(es)."
                ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error al procesar {archivo}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\n🎉 ¡Importación lista! Se registraron {unidades_totales} unidades y {aprendizajes_totales} aprendizajes esperados."
        ))