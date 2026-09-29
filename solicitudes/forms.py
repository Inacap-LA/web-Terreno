from django import forms
from .models import (
    SolicitudTerreno, 
    Docente, 
    Asignatura, 
    UnidadAprendizaje, 
    AprendizajeEsperado
)

class SolicitudForm(forms.ModelForm):
    class Meta:
        model = SolicitudTerreno
        fields = [
            'docente', 
            'asignatura', 
            'unidad', 
            'aprendizaje_esperado',
            'fecha_propuesta', 
            'duracion_horas',
            'cantidad_estudiantes',
            'institucion_destino',
            'trabajo_a_realizar',
        ]
        labels = {
            'docente': 'Docente',
            'asignatura': 'Asignatura',
            'unidad': 'Unidad de Aprendizaje',
            'aprendizaje_esperado': 'Aprendizaje Esperado',
            'fecha_propuesta': 'Fecha Propuesta de Salida',
            'duracion_horas': 'Duración (en horas)',
            'cantidad_estudiantes': 'Cantidad de Estudiantes',
            'institucion_destino': 'Lugar / Institución de Destino',
            'trabajo_a_realizar': 'Trabajo / Actividades a realizar en terreno',
        }
        widgets = {
            'fecha_propuesta': forms.DateInput(attrs={'type': 'date'}),
            'duracion_horas': forms.NumberInput(attrs={'placeholder': 'Ej. 4', 'min': 1}),
            'cantidad_estudiantes': forms.NumberInput(attrs={'placeholder': 'Ej. 25', 'min': 1}),
            'trabajo_a_realizar': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Describa detalladamente los objetivos y actividades académicas a desarrollar...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Opciones iniciales vacías para los selectores dependientes
        self.fields['docente'].queryset = Docente.objects.all().order_by('nombre')
        self.fields['asignatura'].queryset = Asignatura.objects.none()
        self.fields['unidad'].queryset = UnidadAprendizaje.objects.none()
        self.fields['aprendizaje_esperado'].queryset = AprendizajeEsperado.objects.none()

        # Reconstrucción de querysets al enviar formulario (POST)
        if 'docente' in self.data:
            try:
                docente_id = int(self.data.get('docente'))
                # Búsqueda actualizada usando docentes__id
                self.fields['asignatura'].queryset = Asignatura.objects.filter(docentes__id=docente_id).order_by('codigo', 'seccion')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.docente_id:
            self.fields['asignatura'].queryset = Asignatura.objects.filter(docentes__id=self.instance.docente_id).order_by('codigo', 'seccion')
                
        if 'asignatura' in self.data:
            try:
                asignatura_id = int(self.data.get('asignatura'))
                self.fields['unidad'].queryset = UnidadAprendizaje.objects.filter(asignatura_id=asignatura_id).order_by('numero', 'id')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.asignatura_id:
            self.fields['unidad'].queryset = UnidadAprendizaje.objects.filter(asignatura_id=self.instance.asignatura_id).order_by('numero', 'id')

        if 'unidad' in self.data:
            try:
                unidad_id = int(self.data.get('unidad'))
                self.fields['aprendizaje_esperado'].queryset = AprendizajeEsperado.objects.filter(unidad_id=unidad_id).order_by('codigo')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.unidad_id:
            self.fields['aprendizaje_esperado'].queryset = AprendizajeEsperado.objects.filter(unidad_id=self.instance.unidad_id).order_by('codigo')