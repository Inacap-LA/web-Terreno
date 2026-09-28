from django.db import models
from django.core.exceptions import ValidationError

class Docente(models.Model):
    rut = models.CharField(max_length=12, unique=True, verbose_name="RUT")
    nombre = models.CharField(max_length=100, verbose_name="Nombre Completo")

    class Meta:
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.rut})"


class Asignatura(models.Model):
    docente = models.ForeignKey(
        Docente, 
        on_delete=models.CASCADE, 
        related_name='asignaturas',
        verbose_name="Docente"
    )
    codigo = models.CharField(max_length=20, default="", blank=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre de Asignatura")
    seccion = models.CharField(max_length=50, verbose_name="Sección")

    class Meta:
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        ordering = ['codigo', 'seccion']

    def __str__(self):
        return f"{self.codigo} - {self.nombre} (Sec. {self.seccion})"


class UnidadAprendizaje(models.Model):
    asignatura = models.ForeignKey(
        Asignatura, 
        on_delete=models.CASCADE, 
        related_name='unidades',
        verbose_name="Asignatura"
    )
    numero = models.PositiveIntegerField(null=True, blank=True, verbose_name="Número de Unidad")
    nombre = models.CharField(max_length=250, verbose_name="Nombre de la Unidad")

    class Meta:
        verbose_name = "Unidad de Aprendizaje"
        verbose_name_plural = "Unidades de Aprendizaje"
        ordering = ['numero', 'id']

    def __str__(self):
        if self.numero:
            return f"Unidad {self.numero}: {self.nombre}"
        return self.nombre


class AprendizajeEsperado(models.Model):
    unidad = models.ForeignKey(
        UnidadAprendizaje, 
        on_delete=models.CASCADE, 
        related_name='aprendizajes',
        verbose_name="Unidad de Aprendizaje"
    )
    codigo = models.CharField(max_length=20, verbose_name="Código (ej: 1.1)")
    descripcion = models.TextField(verbose_name="Descripción")

    class Meta:
        verbose_name = "Aprendizaje Esperado"
        verbose_name_plural = "Aprendizajes Esperados"
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.descripcion[:70]}..."


class SolicitudTerreno(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
    ]

    docente = models.ForeignKey(
        Docente, 
        on_delete=models.CASCADE, 
        related_name='solicitudes',
        verbose_name="Docente"
    )
    asignatura = models.ForeignKey(
        Asignatura, 
        on_delete=models.CASCADE, 
        related_name='solicitudes',
        verbose_name="Asignatura"
    )
    unidad = models.ForeignKey(
        UnidadAprendizaje, 
        on_delete=models.CASCADE, 
        related_name='solicitudes',
        verbose_name="Unidad de Aprendizaje"
    )
    
    # Campo para almacenar el Aprendizaje Esperado asociado
    aprendizaje_esperado = models.ForeignKey(
        AprendizajeEsperado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes',
        verbose_name="Aprendizaje Esperado"
    )
    
    fecha_propuesta = models.DateField(verbose_name="Fecha Propuesta")
    duracion_horas = models.IntegerField(null=True, blank=True, verbose_name="Duración en Horas")
    cantidad_estudiantes = models.PositiveIntegerField(verbose_name="Cantidad de Estudiantes")
    institucion_destino = models.CharField(max_length=200, verbose_name="Lugar / Destino")
    trabajo_a_realizar = models.TextField(
        verbose_name="Trabajo / Actividad a realizar en terreno",
        help_text="Descripción de las actividades y objetivos que se llevarán a cabo."
    )
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE', verbose_name="Estado")
    contratada = models.BooleanField(default=False, verbose_name="¿Contratada?")
    realizada = models.BooleanField(default=False, verbose_name="¿Realizada?")
    
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

    class Meta:
        verbose_name = "Solicitud de Terreno"
        verbose_name_plural = "Solicitudes de Terreno"
        ordering = ['-fecha_creacion']

    def clean(self):
        """Validación de integridad para asegurar que el AE pertenece a la Unidad seleccionada."""
        super().clean()
        if self.aprendizaje_esperado and self.unidad:
            if self.aprendizaje_esperado.unidad_id != self.unidad_id:
                raise ValidationError({
                    'aprendizaje_esperado': 'El aprendizaje esperado seleccionado no pertenece a la unidad de aprendizaje indicada.'
                })

    def __str__(self):
        return f"Solicitud #{self.id} - {self.asignatura.nombre} ({self.fecha_propuesta})"