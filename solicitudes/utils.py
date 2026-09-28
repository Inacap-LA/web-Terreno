# solicitudes/utils.py
import re

def procesar_texto_descriptor(texto_pdf):
    """
    Recibe el texto extraído de un PDF y devuelve una lista de diccionarios
    con las Unidades y sus respectivos Aprendizajes Esperados.
    """
    unidades = []
    unidad_actual = None
    
    patron_unidad = re.compile(r'^(\d+)\s*\.\s*(.+?)(?:\s*\||$)')
    patron_aprendizaje = re.compile(r'^(\d+\.\d+)\s+(.+)')

    lineas = texto_pdf.split('\n')
    
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        match_unidad = patron_unidad.match(linea)
        if match_unidad:
            unidad_actual = {
                'numero': int(match_unidad.group(1)),
                'nombre': match_unidad.group(2).strip(),
                'aprendizajes': []
            }
            unidades.append(unidad_actual)
            continue
            
        match_ae = patron_aprendizaje.match(linea)
        if match_ae and unidad_actual is not None:
            codigo = match_ae.group(1)
            if codigo.startswith(str(unidad_actual['numero']) + "."):
                unidad_actual['aprendizajes'].append({
                    'codigo': codigo,
                    'descripcion': match_ae.group(2).strip()
                })

    return unidades