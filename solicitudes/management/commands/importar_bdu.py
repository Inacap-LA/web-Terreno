import pandas as pd
from django.core.management.base import BaseCommand
from solicitudes.models import Docente, Asignatura

class Command(BaseCommand):
    help = 'Importa la carga docente filtrando solo a los profesores seleccionados'

    def add_arguments(self, parser):
        parser.add_argument('ruta_archivo', type=str, help='Ruta al archivo Excel')
        # Nuevo argumento opcional para limpiar la base de datos antes de importar
        parser.add_argument('--limpiar', action='store_true', help='Elimina docentes y asignaturas previas')

    def handle(self, *args, **kwargs):
        ruta_archivo = kwargs['ruta_archivo']
        limpiar = kwargs['limpiar']
        
        # Lista de profesores permitidos (en mayúsculas para evitar problemas de formato)
        DOCENTES_PERMITIDOS = [
            "VALLEJOS CATRILAO GONZALO HERNÁN",
            "VIDAL CARRASCO PILAR GABRIELA",
            "SANDOVAL ZAPATA LORENA BEATRIZ",
            "PEZOA SEPÚLVEDA YERKA EUGENIA",
            "SARAVIA MARTINEZ ANTONIO JAVIER",
            "ACEVEDO AGUAYO MARIO EDUARDO",
            "CRUCES SOTO SONIA MARGOTH",
            "CIFUENTES BARRIENTOS CARLOS ALFREDO"
        ]

        if limpiar:
            self.stdout.write("Limpiando base de datos de Docentes y Asignaturas...")
            Docente.objects.all().delete()
            Asignatura.objects.all().delete()

        try:
            self.stdout.write(f"Leyendo archivo {ruta_archivo}...")
            
            if ruta_archivo.lower().endswith('.xlsx'):
                df = pd.read_excel(ruta_archivo)
            else:
                tablas = pd.read_html(ruta_archivo)
                df = tablas[0]
                if df.iloc[0].str.contains('Asignatura|Profesor|Corr', case=False, na=False).any():
                    df.columns = df.iloc[0]
                    df = df[1:]

            df.columns = [' '.join(str(col).replace('\n', ' ').split()) for col in df.columns]
            
            col_rut = next((c for c in df.columns if 'rut' in c.lower()), None)
            col_profesor = next((c for c in df.columns if 'profesor' in c.lower()), None)
            col_codigo = next((c for c in df.columns if 'cód' in c.lower() or 'cod' in c.lower()), None)
            col_asignatura = next((c for c in df.columns if 'asignatura' in c.lower() and not any(k in c.lower() for k in ['tipo', 'cód', 'cod', 'nivel', 'pe'])), None)
            col_seccion = next((c for c in df.columns if 'sección' in c.lower() or 'seccion' in c.lower()), None)

            if not all([col_rut, col_profesor, col_codigo, col_asignatura]):
                raise ValueError("Faltan columnas requeridas en el Excel.")

            df = df.dropna(subset=[col_rut, col_asignatura])
            docentes_creados = 0
            asignaturas_procesadas = 0

            for index, row in df.iterrows():
                rut = str(row[col_rut]).strip()
                nombre_profesor = str(row[col_profesor]).strip()
                nombre_upper = nombre_profesor.upper()
                
                # ---------------------------------------------------------
                # FILTRO ESTRICTO DE DOCENTES
                # ---------------------------------------------------------
                es_permitido = any(docente_permitido in nombre_upper for docente_permitido in DOCENTES_PERMITIDOS)
                
                if not rut or rut.lower() == 'nan' or rut.lower() == 'profesor' or not es_permitido:
                    continue
                # ---------------------------------------------------------

                codigo_asig = str(row[col_codigo]).strip().upper()
                nombre_asig = str(row[col_asignatura]).strip()
                seccion = str(row[col_seccion]).strip() if col_seccion and pd.notna(row[col_seccion]) else "Por definir"

                docente, creado = Docente.objects.get_or_create(
                    rut=rut, defaults={'nombre': nombre_profesor}
                )
                if creado: docentes_creados += 1
                
                asig = Asignatura.objects.filter(codigo=codigo_asig, seccion=seccion).first()
                if asig:
                    asig.docente = docente
                    asig.nombre = nombre_asig
                    asig.save()
                else:
                    Asignatura.objects.create(codigo=codigo_asig, nombre=nombre_asig, docente=docente, seccion=seccion)
                
                asignaturas_procesadas += 1

            self.stdout.write(self.style.SUCCESS(
                f'¡Éxito! Se procesaron {asignaturas_procesadas} asignaturas y quedaron {Docente.objects.count()} docentes en el sistema.'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al procesar: {str(e)}'))