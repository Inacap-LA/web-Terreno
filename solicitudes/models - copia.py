from django.db import models

class Docente(models.Model):
    rut = models.CharField(max_length=12, unique=True, verbose_name="RUT")
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

class Asignatura(models.Model):
    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=20, default="", blank=True)
    nombre = models.CharField(max_length=100)
    seccion = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.codigo} - {self.nombre} (Sec. {self.seccion})"

class UnidadAprendizaje(models.Model):
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=200)

    def __str__(self):
        return self.nombre

class SolicitudTerreno(models.Model):
    ESTADOS = [('PENDIENTE', 'Pendiente'), ('APROBADA', 'Aprobada'), ('RECHAZADA', 'Rechazada')]

    docente = models.ForeignKey(Docente, on_delete=models.CASCADE)
    asignatura = models.ForeignKey(Asignatura, on_delete=models.CASCADE)
    unidad = models.ForeignKey(UnidadAprendizaje, on_delete=models.CASCADE)
    
    fecha_propuesta = models.DateField()
    duracion_horas = models.IntegerField(null=True, blank=True, verbose_name="Duración en horas")
    cantidad_estudiantes = models.PositiveIntegerField()
    institucion_destino = models.CharField(max_length=200)
    trabajo_a_realizar = models.TextField(
        verbose_name="Trabajo / Actividad a realizar en terreno",
        help_text="Descripción de las actividades y objetivos que se llevarán a cabo."
    )
    
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    contratada = models.BooleanField(default=False, verbose_name="¿Contratada?")
    realizada = models.BooleanField(default=False, verbose_name="¿Realizada?")

    def __str__(self):
        return f"Solicitud {self.asignatura.nombre} - {self.fecha_propuesta}"