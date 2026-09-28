from django.urls import path
from . import views

urlpatterns = [
    # Vistas principales
    path('', views.lista_solicitudes, name='lista_solicitudes'),
    path('nueva/', views.crear_solicitud, name='crear_solicitud'),
    path('solicitud/<int:pk>/', views.detalle_solicitud, name='detalle_solicitud'),

    # Rutas para los filtros dinámicos en cascada (AJAX)
    path('ajax/cargar-asignaturas/', views.cargar_asignaturas, name='ajax_cargar_asignaturas'),
    path('ajax/cargar-unidades/', views.cargar_unidades, name='ajax_cargar_unidades'),
    path('ajax/cargar-aprendizajes/', views.cargar_aprendizajes, name='ajax_cargar_aprendizajes'),
]