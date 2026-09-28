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
    # 'select_related' pre-carga las relaciones en una sola consulta SQL (evita el problema N+1)
    solicitudes = SolicitudTerreno.objects.select_related(
        'docente', 'asignatura', 'unidad', 'aprendizaje_esperado'
    ).order_by('-fecha_propuesta')
    
    return render(request, 'solicitudes/lista_solicitudes.html', {'solicitudes': solicitudes})


def crear_solicitud(request):
    if request.method == 'POST':
        form = SolicitudForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_solicitudes')
    else:
        form = SolicitudForm()
        
    return render(request, 'solicitudes/crear_solicitud.html', {'form': form})


def detalle_solicitud(request, pk):
    solicitud = get_object_or_404(
        SolicitudTerreno.objects.select_related(
            'docente', 'asignatura', 'unidad', 'aprendizaje_esperado'
        ), 
        pk=pk
    )
    return render(request, 'solicitudes/detalle_solicitud.html', {'solicitud': solicitud})


# --- VISTAS AJAX PARA FILTROS DESPLEGABLES EN CASCADA ---

def cargar_asignaturas(request):
    """Devuelve las asignaturas asociadas al docente seleccionado."""
    docente_id = request.GET.get('docente')
    if docente_id:
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
    """Devuelve las unidades asociadas a la asignatura seleccionada."""
    asignatura_id = request.GET.get('asignatura')
    if asignatura_id:
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
    """Devuelve los aprendizajes esperados asociados a la unidad seleccionada."""
    unidad_id = request.GET.get('unidad')
    if unidad_id:
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