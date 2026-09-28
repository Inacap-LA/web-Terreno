from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import (
    SolicitudTerreno, 
    Docente, 
    Asignatura, 
    UnidadAprendizaje, 
    AprendizajeEsperado
)
from .forms import SolicitudForm


def lista_solicitudes(request):
    """
    Muestra la lista general de solicitudes de terreno.
    Se utiliza select_related para traer todas las relaciones en 1 sola consulta SQL.
    """
    solicitudes = SolicitudTerreno.objects.select_related(
        'docente', 'asignatura', 'unidad', 'aprendizaje_esperado'
    ).order_by('-fecha_propuesta')
    
    return render(request, 'solicitudes/lista_solicitudes.html', {'solicitudes': solicitudes})


def crear_solicitud(request):
    """Procesa el formulario para registrar una nueva salida a terreno."""
    if request.method == 'POST':
        form = SolicitudForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_solicitudes')
    else:
        form = SolicitudForm()
        
    return render(request, 'solicitudes/crear_solicitud.html', {'form': form})


def detalle_solicitud(request, pk):
    """Muestra la información detallada de una solicitud específica."""
    solicitud = get_object_or_404(
        SolicitudTerreno.objects.select_related(
            'docente', 'asignatura', 'unidad', 'aprendizaje_esperado'
        ), 
        pk=pk
    )
    return render(request, 'solicitudes/detalle_solicitud.html', {'solicitud': solicitud})


# ==========================================
# VISTAS AJAX (FILTROS DESPLEGABLES EN CASCADA)
# ==========================================

def cargar_asignaturas(request):
    """Devuelve en JSON las asignaturas filtradas por el docente seleccionado."""
    docente_id = request.GET.get('docente')
    if docente_id and docente_id.isdigit():
        asignaturas = Asignatura.objects.filter(docente_id=docente_id).order_by('codigo', 'seccion')
        data = [
            {
                'id': asig.id, 
                'texto': f"{asig.codigo} - {asig.nombre} (Sec. {asig.seccion})"
            } 
            for asig in asignaturas
        ]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


def cargar_unidades(request):
    """Devuelve en JSON las unidades filtradas por la asignatura seleccionada."""
    asignatura_id = request.GET.get('asignatura')
    if asignatura_id and asignatura_id.isdigit():
        unidades = UnidadAprendizaje.objects.filter(asignatura_id=asignatura_id).order_by('numero', 'id')
        data = [
            {
                'id': u.id,
                'texto': f"Unidad {u.numero}: {u.nombre}" if u.numero else u.nombre
            }
            for u in unidades
        ]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


def cargar_aprendizajes(request):
    """Devuelve en JSON los aprendizajes esperados filtrados por la unidad seleccionada."""
    unidad_id = request.GET.get('unidad')
    if unidad_id and unidad_id.isdigit():
        aprendizajes = AprendizajeEsperado.objects.filter(unidad_id=unidad_id).order_by('codigo')
        data = [
            {
                'id': ae.id,
                'texto': f"{ae.codigo} - {ae.descripcion[:80]}..."
            }
            for ae in aprendizajes
        ]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)