from django.db import models
from django.core.exceptions import ValidationError


class Docente(models.Model):
    rut = models.CharField(max_length=12, unique=True, verbose_name="RUT")
    nombre = models.CharField(max_length=150, verbose_name="Nombre Completo")
    email = models.EmailField(max_length=150, blank=True, null=True, verbose_name="Correo Electrónico")

    class Meta:
        verbose_name = "Docente"
        verbose_name_plural = "Docentes"
        ordering = ['nombre']

    def __str__(self):
        if self.email:
            return f"{self.nombre} ({self.rut}) - {self.email}"
        return f"{self.nombre} ({self.rut})"


class Asignatura(models.Model):
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre de Asignatura")
    seccion = models.CharField(max_length=200, blank=True, null=True, verbose_name="Sección(es)")
    
    # Relación de Muchos a Muchos: Permite que varios profesores dicten la misma asignatura (ej: AGP441)
    docentes = models.ManyToManyField(
        Docente, 
        blank=True, 
        related_name='asignaturas',
        verbose_name="Docentes"
    )

    class Meta:
        verbose_name = "Asignatura"
        verbose_name_plural = "Asignaturas"
        ordering = ['codigo']

    def __str__(self):
        sec_str = f" (Sec. {self.seccion})" if self.seccion else ""
        return f"{self.codigo} - {self.nombre}{sec_str}"


class UnidadAprendizaje(models.Model):
    asignatura = models.ForeignKey(
        Asignatura, 
        on_delete=models.CASCADE, 
        related_name='unidades',
        verbose_name="Asignatura"
    )
    # CharField para soportar formatos como "1", "I" o "Unidad 1"
    numero = models.CharField(max_length=20, null=True, blank=True, verbose_name="Número de Unidad")
    nombre = models.TextField(verbose_name="Nombre / Descripción de la Unidad")

    class Meta:
        verbose_name = "Unidad de Aprendizaje"
        verbose_name_plural = "Unidades de Aprendizaje"
        ordering = ['numero', 'id']

    def __str__(self):
        if self.numero:
            return f"Unidad {self.numero}: {self.nombre[:80]}"
        return self.nombre[:80]


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

    # Usar PROTECT evita que al borrar un docente o asignatura se eliminen sus solicitudes históricas
    docente = models.ForeignKey(
        Docente, 
        on_delete=models.PROTECT, 
        related_name='solicitudes',
        verbose_name="Docente"
    )
    asignatura = models.ForeignKey(
        Asignatura, 
        on_delete=models.PROTECT, 
        related_name='solicitudes',
        verbose_name="Asignatura"
    )
    unidad = models.ForeignKey(
        UnidadAprendizaje, 
        on_delete=models.PROTECT, 
        related_name='solicitudes',
        verbose_name="Unidad de Aprendizaje"
    )
    aprendizaje_esperado = models.ForeignKey(
        AprendizajeEsperado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes',
        verbose_name="Aprendizaje Esperado"
    )
    
    fecha_propuesta = models.DateField(verbose_name="Fecha Propuesta")
    duracion_horas = models.PositiveIntegerField(null=True, blank=True, verbose_name="Duración en Horas")
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
        """Validación de integridad jerárquica (Docente -> Asignatura -> Unidad -> Aprendizaje)."""
        super().clean()
        errors = {}

        # Validar si la asignatura está asociada al docente seleccionado
        if self.docente_id and self.asignatura_id:
            if not self.asignatura.docentes.filter(id=self.docente_id).exists():
                errors['asignatura'] = 'La asignatura seleccionada no está asociada al docente indicado.'

        if self.asignatura_id and self.unidad_id and self.unidad.asignatura_id != self.asignatura_id:
            errors['unidad'] = 'La unidad seleccionada no pertenece a la asignatura indicada.'

        if self.unidad_id and self.aprendizaje_esperado_id and self.aprendizaje_esperado.unidad_id != self.unidad_id:
            errors['aprendizaje_esperado'] = 'El aprendizaje esperado seleccionado no pertenece a la unidad indicada.'

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Solicitud #{self.id} - {self.asignatura.nombre} ({self.fecha_propuesta})"