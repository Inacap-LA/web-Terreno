from django import forms
from .models import SolicitudTerreno, Asignatura, UnidadAprendizaje, Docente

class SolicitudForm(forms.ModelForm):
    class Meta:
        model = SolicitudTerreno
        fields = [
            'docente', 
            'asignatura', 
            'unidad', 
            'fecha_propuesta', 
            'duracion_horas',
            'cantidad_estudiantes',  # <-- Se agrega este campo
            'institucion_destino',
            'trabajo_a_realizar',
        ]
        labels = {
            'docente': 'Docente',
            'asignatura': 'Asignatura',
            'unidad': 'Unidad de Aprendizaje',
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
        
        # Opciones iniciales para selectores dependientes
        self.fields['docente'].queryset = Docente.objects.all().order_by('nombre')
        self.fields['asignatura'].queryset = Asignatura.objects.none()
        self.fields['unidad'].queryset = UnidadAprendizaje.objects.none()

        # Mantener las opciones seleccionadas en POST o revalidación
        if 'docente' in self.data:
            try:
                docente_id = int(self.data.get('docente'))
                self.fields['asignatura'].queryset = Asignatura.objects.filter(docente_id=docente_id).order_by('nombre')
            except (ValueError, TypeError):
                pass
                
        if 'asignatura' in self.data:
            try:
                asignatura_id = int(self.data.get('asignatura'))
                self.fields['unidad'].queryset = UnidadAprendizaje.objects.filter(asignatura_id=asignatura_id).order_by('nombre')
            except (ValueError, TypeError):
                pass