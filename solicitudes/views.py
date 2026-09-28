from django.shortcuts import render, redirect
from django.http import JsonResponse
# Asegúrate de importar TODOS tus modelos aquí arriba
from .models import SolicitudTerreno, UnidadAprendizaje, Asignatura 
from .forms import SolicitudForm

def lista_solicitudes(request):
    solicitudes = SolicitudTerreno.objects.all().order_by('-fecha_propuesta') # Asumiendo que es así por tu captura anterior
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

def cargar_unidades(request):
    asignatura_id = request.GET.get('asignatura')
    # Añadimos el if para mayor seguridad
    if asignatura_id:
        unidades = UnidadAprendizaje.objects.filter(asignatura_id=asignatura_id).order_by('nombre')
        return JsonResponse(list(unidades.values('id', 'nombre')), safe=False)
    return JsonResponse([], safe=False)

def cargar_asignaturas(request):
    docente_id = request.GET.get('docente')
    if docente_id:
        asignaturas = Asignatura.objects.filter(docente_id=docente_id).order_by('nombre')
        # Formateamos el texto para que se vea igual que en tu imagen
        data = [{'id': asig.id, 'texto': f"{asig.codigo} - {asig.nombre} (Sec. {asig.seccion})"} for asig in asignaturas]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)

from django.shortcuts import render, redirect, get_object_or_404

def detalle_solicitud(request, pk):
    solicitud = get_object_or_404(SolicitudTerreno, pk=pk)
    return render(request, 'solicitudes/detalle_solicitud.html', {'solicitud': solicitud})