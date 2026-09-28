import os
import re
from django.core.management.base import BaseCommand
# Asegúrate de haber creado e importado el modelo AprendizajeEsperado
from solicitudes.models import Asignatura, UnidadAprendizaje, AprendizajeEsperado
from pypdf import PdfReader

class Command(BaseCommand):
    help = 'Importa unidades y aprendizajes esperados desde los PDFs en la carpeta indicada'

    def add_arguments(self, parser):
        parser.add_argument('carpeta', type=str, help='Nombre de la carpeta de descriptores')

    def procesar_texto(self, texto):
        """
        Extrae Unidades y Aprendizajes Esperados basándose en el formato numérico de INACAP:
        '1 . Nombre de la Unidad' y '1.1 Nombre del Aprendizaje'
        """
        unidades = []
        unidad_actual = None
        
        # Patrón para Unidad: "1 . Organización de labores..." (captura número y nombre)
        patron_unidad = re.compile(r'^(\d+)\s*\.\s*(.+?)(?:\s*\||$)')
        
        # Patrón para Aprendizaje Esperado: "1.1 Organiza labores agrícolas..." (captura código y descripción)
        patron_aprendizaje = re.compile(r'^(\d+\.\d+)\s+(.+)')

        for linea in texto.splitlines():
            linea = linea.strip()
            if not linea:
                continue

            # Buscar coincidencias de Unidad
            match_unidad = patron_unidad.match(linea)
            if match_unidad:
                numero = int(match_unidad.group(1))
                nombre = match_unidad.group(2).strip()
                
                # Filtrar posibles falsos positivos muy cortos
                if len(nombre) > 3:
                    unidad_actual = {
                        'numero': numero,
                        'nombre': nombre[:200],  # Límite de seguridad para la BD
                        'aprendizajes': []
                    }
                    unidades.append(unidad_actual)
                continue
                
            # Buscar coincidencias de Aprendizaje Esperado
            match_ae = patron_aprendizaje.match(linea)
            if match_ae and unidad_actual is not None:
                codigo = match_ae.group(1)
                descripcion = match_ae.group(2).strip()
                
                # Validar que el aprendizaje (ej. 1.1) corresponde a la unidad actual (ej. Unidad 1)
                if codigo.startswith(f"{unidad_actual['numero']}."):
                    unidad_actual['aprendizajes'].append({
                        'codigo': codigo,
                        'descripcion': descripcion
                    })

        return unidades

    def handle(self, *args, **options):
        carpeta = options['carpeta']
        if not os.path.exists(carpeta):
            self.stdout.write(self.style.ERROR(f"La carpeta '{carpeta}' no existe."))
            return

        archivos = [f for f in os.listdir(carpeta) if f.lower().endswith('.pdf')]
        self.stdout.write(f"Procesando {len(archivos)} archivos PDF...")

        unidades_totales = 0
        aprendizajes_totales = 0

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

                # Procesar el texto usando el método interno
                datos_extraidos = self.procesar_texto(texto)

                if not datos_extraidos:
                    self.stdout.write(self.style.WARNING(f"No se encontraron unidades con el formato esperado en {archivo}"))
                    continue

                unidades_asociadas = 0
                aes_asociados = 0

                # Asociar a todas las secciones existentes de esa asignatura
                for asig in asignaturas:
                    for datos_unidad in datos_extraidos:
                        # 1. Crear o actualizar la Unidad (se añade el campo 'numero' para ordenarlo mejor)
                        unidad_obj, u_creada = UnidadAprendizaje.objects.get_or_create(
                            asignatura=asig,
                            numero=datos_unidad['numero'],
                            defaults={'nombre': datos_unidad['nombre']}
                        )
                        if u_creada:
                            unidades_asociadas += 1

                        # 2. Crear los Aprendizajes Esperados vinculados a esa Unidad
                        for datos_ae in datos_unidad['aprendizajes']:
                            ae_obj, ae_creado = AprendizajeEsperado.objects.get_or_create(
                                unidad=unidad_obj,
                                codigo=datos_ae['codigo'],
                                defaults={'descripcion': datos_ae['descripcion']}
                            )
                            if ae_creado:
                                aes_asociados += 1

                unidades_totales += unidades_asociadas
                aprendizajes_totales += aes_asociados
                
                total_aes_extraidos = sum(len(u['aprendizajes']) for u in datos_extraidos)
                self.stdout.write(f"Asignatura {codigo}: {len(datos_extraidos)} unidades y {total_aes_extraidos} aprendizajes vinculados a {len(asignaturas)} sección(es).")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error al procesar {archivo}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"¡Proceso finalizado! Se crearon {unidades_totales} unidades y {aprendizajes_totales} aprendizajes esperados."
        ))