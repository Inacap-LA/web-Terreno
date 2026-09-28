import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from .models import (
    SolicitudTerreno, 
    Docente, 
    Asignatura, 
    UnidadAprendizaje, 
    AprendizajeEsperado
)
from .forms import SolicitudForm

logger = logging.getLogger(__name__)

# Correos institucionales del área
CORREOS_COORDINACION = [
    'ypezoa@inacap.cl',  # Coordinadora de Carrera
    'orobles@inacap.cl',  # Director de Carrera (DC)
]


def enviar_correo_notificacion(solicitud):
    """
    Función auxiliar a prueba de fallos para el envío de notificaciones.
    Si falla la plantilla HTML o la conexión SMTP, no interrumpe el flujo de la aplicación.
    """
    destinatarios = list(CORREOS_COORDINACION)
    
    # Agregar el correo del docente si está disponible
    if hasattr(solicitud, 'docente') and getattr(solicitud.docente, 'email', None):
        destinatarios.append(solicitud.docente.email)

    asunto = f"[Nueva Solicitud] Salida a Terreno - {solicitud.asignatura}"
    contexto = {'solicitud': solicitud}

    # 1. Intentar cargar la plantilla HTML; si no existe, genera un texto plano de respaldo
    try:
        html_content = render_to_string('emails/notificacion_solicitud.html', contexto)
        text_content = strip_tags(html_content)
    except Exception as e:
        logger.warning(f"No se pudo cargar la plantilla HTML de correo: {e}")
        html_content = None
        # Texto alternativo de emergencia
        fecha = getattr(solicitud, 'fecha_propuesta', getattr(solicitud, 'fecha_salida', 'No especificada'))
        duracion = getattr(solicitud, 'duracion', 'N/A')
        text_content = (
            f"Se ha registrado una nueva solicitud de salida a terreno.\n\n"
            f"Docente: {solicitud.docente}\n"
            f"Asignatura: {solicitud.asignatura}\n"
            f"Unidad: {getattr(solicitud, 'unidad', 'N/A')}\n"
            f"Fecha propuesta: {fecha}\n"
            f"Duración: {duracion} horas\n"
        )

    # 2. Despachar el correo con fail_silently=True
    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@inacap.cl')
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=from_email,
            to=destinatarios
        )
        if html_content:
            email.attach_alternative(html_content, "text/html")
            
        email.send(fail_silently=True)
        return True
    except Exception as e:
        logger.error(f"Error al enviar correo de la solicitud #{solicitud.pk}: {e}")
        return False


def lista_solicitudes(request):
    """Muestra la lista general de solicitudes de terreno."""
    solicitudes = SolicitudTerreno.objects.select_related(
        'docente', 'asignatura', 'unidad', 'aprendizaje_esperado'
    ).order_by('-fecha_propuesta')
    
    return render(request, 'solicitudes/lista_solicitudes.html', {'solicitudes': solicitudes})


def crear_solicitud(request):
    """Procesa el formulario para registrar una nueva salida a terreno."""
    if request.method == 'POST':
        form = SolicitudForm(request.POST)
        if form.is_valid():
            # 1. Guardar la solicitud primero (Nunca fallará por temas de correo)
            solicitud = form.save()

            # 2. Enviar el correo de forma segura
            correo_exitoso = enviar_correo_notificacion(solicitud)

            if correo_exitoso:
                messages.success(request, 'Solicitud registrada y notificada exitosamente por correo.')
            else:
                messages.warning(
                    request, 
                    'Solicitud guardada con éxito en la base de datos, pero no se pudo enviar la notificación por correo.'
                )

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
    docente_id = request.GET.get('docente')
    if docente_id and docente_id.isdigit():
        asignaturas = Asignatura.objects.filter(docente_id=docente_id).order_by('codigo', 'seccion')
        data = [
            {'id': asig.id, 'texto': f"{asig.codigo} - {asig.nombre} (Sec. {asig.seccion})"} 
            for asig in asignaturas
        ]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


def cargar_unidades(request):
    asignatura_id = request.GET.get('asignatura')
    if asignatura_id and asignatura_id.isdigit():
        unidades = UnidadAprendizaje.objects.filter(asignatura_id=asignatura_id).order_by('numero', 'id')
        data = [
            {'id': u.id, 'texto': f"Unidad {u.numero}: {u.nombre}" if u.numero else u.nombre}
            for u in unidades
        ]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


def cargar_aprendizajes(request):
    unidad_id = request.GET.get('unidad')
    if unidad_id and unidad_id.isdigit():
        aprendizajes = AprendizajeEsperado.objects.filter(unidad_id=unidad_id).order_by('codigo')
        data = [
            {'id': ae.id, 'texto': f"{ae.codigo} - {ae.descripcion[:80]}..."}
            for ae in aprendizajes
        ]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)