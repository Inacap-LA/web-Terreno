import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from django.contrib import admin
from django.http import HttpResponse
from .models import SolicitudTerreno, Docente, Asignatura, UnidadAprendizaje, AprendizajeEsperado


@admin.action(description='Descargar seleccionadas como Excel (.xlsx)')
def exportar_solicitudes_excel(modeladmin, request, queryset):
    """
    Acción de administración para exportar todas o las solicitudes
    seleccionadas a una planilla Excel con formato institucional.
    """
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="solicitudes_terreno.xlsx"'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Solicitudes"

    # Encabezados de la tabla
    headers = [
        'ID', 
        'Docente', 
        'Asignatura', 
        'Unidad de Aprendizaje', 
        'Aprendizaje Esperado', 
        'Fecha Propuesta', 
        'Duración (Horas)'
    ]
    ws.append(headers)

    # Estilos para la cabecera (Azul/Gris profesional con texto blanco en negrita)
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    for col_num, _ in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Borde delgado para datos
    thin_border = Border(
        left=Side(style='thin', color='D3D3D3'),
        right=Side(style='thin', color='D3D3D3'),
        top=Side(style='thin', color='D3D3D3'),
        bottom=Side(style='thin', color='D3D3D3')
    )

    # Cargar los datos optimizando la consulta SQL
    solicitudes = queryset.select_related('docente', 'asignatura', 'unidad', 'aprendizaje_esperado')

    for solicitud in solicitudes:
        # Formatear la fecha si existe
        fecha_str = ''
        if hasattr(solicitud, 'fecha_propuesta') and solicitud.fecha_propuesta:
            fecha_str = solicitud.fecha_propuesta.strftime('%d/%m/%Y')

        row = [
            solicitud.id,
            str(solicitud.docente) if solicitud.docente else 'N/A',
            str(solicitud.asignatura) if solicitud.asignatura else 'N/A',
            str(solicitud.unidad) if solicitud.unidad else 'N/A',
            str(solicitud.aprendizaje_esperado) if solicitud.aprendizaje_esperado else 'N/A',
            fecha_str,
            getattr(solicitud, 'duracion', '')
        ]
        ws.append(row)

        # Aplicar bordes a la fila agregada
        for col_num in range(1, len(row) + 1):
            cell = ws.cell(row=ws.max_row, column=col_num)
            cell.border = thin_border

    # Ajustar automáticamente el ancho de las columnas según el contenido
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(response)
    return response


@admin.register(SolicitudTerreno)
class SolicitudTerrenoAdmin(admin.ModelAdmin):
    list_display = ('id', 'docente', 'asignatura', 'unidad', 'fecha_propuesta')
    list_filter = ('docente', 'asignatura')
    search_fields = ('docente__nombre', 'asignatura__nombre', 'asignatura__codigo')
    actions = [exportar_solicitudes_excel]


# Registro opcional del resto de modelos en el panel de administración
@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ('id', 'rut', 'nombre', 'email')
    search_fields = ('rut', 'nombre', 'email')


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ('id', 'codigo', 'nombre', 'seccion', 'docente')
    list_filter = ('docente',)


@admin.register(UnidadAprendizaje)
class UnidadAprendizajeAdmin(admin.ModelAdmin):
    list_display = ('id', 'numero', 'nombre', 'asignatura')


@admin.register(AprendizajeEsperado)
class AprendizajeEsperadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'codigo', 'descripcion', 'unidad')