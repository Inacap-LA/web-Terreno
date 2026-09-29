import unicodedata
from pathlib import Path
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from solicitudes.models import Docente, Asignatura


def quitar_acentos(texto):
    """Normaliza texto eliminando tildes y caracteres especiales para comparaciones efectivas."""
    if not texto or pd.isna(texto):
        return ""
    texto_norm = unicodedata.normalize('NFD', str(texto))
    return ''.join(c for c in texto_norm if unicodedata.category(c) != 'Mn').upper().strip()


class Command(BaseCommand):
    help = 'Importa la carga docente filtrando solo a los profesores seleccionados'

    def add_arguments(self, parser):
        parser.add_argument('ruta_archivo', nargs='?', type=str, default=None, help='Ruta al archivo Excel')
        parser.add_argument('--limpiar', action='store_true', help='Elimina docentes y asignaturas previas')

    def handle(self, *args, **kwargs):
        ruta_archivo = kwargs['ruta_archivo']
        limpiar = kwargs['limpiar']

        base_dir = Path(settings.BASE_DIR)

        # Autodetectar archivo Excel si no se especifica una ruta por consola
        if not ruta_archivo:
            archivos = list(base_dir.glob("*.xlsx")) + list(base_dir.glob("*.xls"))
            if not archivos:
                self.stdout.write(self.style.ERROR("❌ No se encontró ningún archivo .xlsx o .xls en la raíz del proyecto."))
                return
            ruta_archivo = str(archivos[0])

        self.stdout.write(f"📖 Procesando archivo: {ruta_archivo}")

        # Lista de docentes permitidos (se comparan sin tildes para evitar diferencias)
        DOCENTES_PERMITIDOS_RAW = [
            "VALLEJOS CATRILAO GONZALO HERNÁN",
            "VIDAL CARRASCO PILAR GABRIELA",
            "SANDOVAL ZAPATA LORENA BEATRIZ",
            "PEZOA SEPÚLVEDA YERKA EUGENIA",
            "SARAVIA MARTINEZ ANTONIO JAVIER",
            "ACEVEDO AGUAYO MARIO EDUARDO",
            "CRUCES SOTO SONIA MARGOTH",
            "CIFUENTES BARRIENTOS CARLOS ALFREDO"
        ]
        docentes_permitidos_norm = [quitar_acentos(d) for d in DOCENTES_PERMITIDOS_RAW]

        if limpiar:
            self.stdout.write(self.style.WARNING("⚠️ Limpiando base de datos de Docentes y Asignaturas..."))
            Asignatura.objects.all().delete()
            Docente.objects.all().delete()

        try:
            if ruta_archivo.lower().endswith(('.xlsx', '.xls')):
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
            col_email = next((c for c in df.columns if 'correo' in c.lower() or 'email' in c.lower()), None)
            col_codigo = next((c for c in df.columns if 'cód' in c.lower() or 'cod' in c.lower()), None)
            col_asignatura = next((c for c in df.columns if 'asignatura' in c.lower() and not any(k in c.lower() for k in ['tipo', 'cód', 'cod', 'nivel', 'pe'])), None)
            col_seccion = next((c for c in df.columns if 'sección' in c.lower() or 'seccion' in c.lower()), None)

            if not all([col_rut, col_profesor, col_codigo, col_asignatura]):
                raise ValueError("Faltan columnas requeridas en la planilla Excel.")

            df = df.dropna(subset=[col_rut, col_asignatura])
            docentes_creados = 0
            asignaturas_procesadas = 0

            for _, row in df.iterrows():
                rut = str(row[col_rut]).strip()
                nombre_profesor = str(row[col_profesor]).strip()
                nombre_norm = quitar_acentos(nombre_profesor)

                es_permitido = any(permitido in nombre_norm for permitido in docentes_permitidos_norm)

                if not rut or rut.lower() in ['nan', 'profesor', 'none'] or not es_permitido:
                    continue

                email_profesor = str(row[col_email]).strip() if col_email and pd.notna(row[col_email]) else None
                codigo_asig = str(row[col_codigo]).strip().upper()
                nombre_asig = str(row[col_asignatura]).strip()
                seccion = str(row[col_seccion]).strip() if col_seccion and pd.notna(row[col_seccion]) else "Por definir"

                # 1. Crear o recuperar Docente
                docente, creado = Docente.objects.get_or_create(
                    rut=rut,
                    defaults={'nombre': nombre_profesor, 'email': email_profesor}
                )
                if creado:
                    docentes_creados += 1
                elif email_profesor and not docente.email:
                    docente.email = email_profesor
                    docente.save()

                # 2. Crear o recuperar Asignatura por CÓDIGO único
                asig, asig_creada = Asignatura.objects.get_or_create(
                    codigo=codigo_asig,
                    defaults={
                        'nombre': nombre_asig,
                        'seccion': seccion
                    }
                )

                if not asig_creada:
                    asig.nombre = nombre_asig
                    if seccion and seccion not in (asig.seccion or ""):
                        asig.seccion = f"{asig.seccion}, {seccion}" if asig.seccion else seccion
                    asig.save()

                # 3. Vincular el docente usando .docentes.add()
                asig.docentes.add(docente)

                asignaturas_procesadas += 1

            self.stdout.write(self.style.SUCCESS(
                f'🎉 ¡Éxito! Se procesaron {asignaturas_procesadas} registros y hay {Docente.objects.count()} docentes guardados.'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al procesar: {str(e)}'))