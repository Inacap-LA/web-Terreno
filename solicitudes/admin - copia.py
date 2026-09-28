from django.contrib import admin
from .models import SolicitudTerreno, Docente, Asignatura, UnidadAprendizaje

@admin.register(Docente)
class DocenteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre')
    search_fields = ('nombre',)

@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'codigo', 'docente')
    search_fields = ('nombre', 'codigo')
    list_filter = ('docente',)

@admin.register(UnidadAprendizaje)
class UnidadAprendizajeAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'asignatura')
    search_fields = ('nombre',)
    list_filter = ('asignatura',)

@admin.register(SolicitudTerreno)
class SolicitudTerrenoAdmin(admin.ModelAdmin):
    # Columnas que se mostrarán en la tabla
    list_display = (
        'id', 
        'docente', 
        'asignatura', 
        'fecha_propuesta', 
        'institucion_destino',
        'contratada',   # Casilla 1
        'realizada',    # Casilla 2
    )
    
    # Permite marcar/desmarcar los checkboxes directamente desde la lista y guardar de una sola vez
    list_editable = ('contratada', 'realizada')
    
    # Filtros laterales para buscar rápidamente cuáles están contratadas o realizadas
    list_filter = ('contratada', 'realizada', 'fecha_propuesta', 'asignatura')
    
    search_fields = ('docente__nombre', 'asignatura__nombre', 'institucion_destino')