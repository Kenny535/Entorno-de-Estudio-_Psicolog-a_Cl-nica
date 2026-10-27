#!/usr/bin/env python3
"""Integrate full APA 7th edition guide into streamlit_app.py - Fixed"""
import pathlib

# Read the APA guide
apa_path = pathlib.Path(r'C:\Users\kenny\OneDrive\Desktop\Teoría  de  la  Personalidad (PSI-245)\Guia-Normas-APA-7ma-edicion.md')
apa_guide = apa_path.read_text(encoding='utf-8')

# Read current streamlit_app
app_path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = app_path.read_text(encoding='utf-8')

# Find the asistente_escritura_agente function
start = content.find('def asistente_escritura_agente(tema, tipo_trabajo, materia_nombre):')
if start == -1:
    print('❌ Function not found')
    exit(1)

# Find the prompt construction
prompt_start = content.find('prompt = """', start)
if prompt_start == -1:
    prompt_start = content.find("prompt = '''", start)
if prompt_start == -1:
    prompt_start = content.find('prompt = f"""', start)
if prompt_start == -1:
    print('❌ Prompt not found')
    exit(1)

# Find the end of the prompt (triple quotes)
prompt_end = content.find('"""', prompt_start + 10)
if prompt_end == -1:
    print('❌ Prompt end not found')
    exit(1)

print(f'Found prompt at {prompt_start} to {prompt_end}')

# Build new comprehensive prompt - ESCAPE curly braces that should remain as template
# Use {{ and }} for literal braces in the final f-string
new_prompt = '''prompt = f"""Eres un asistente académico experto en normas APA 7ma edición y psicología clínica. 
Tu trabajo es generar una ESTRUCTURA COMPLETA DE TRABAJO ACADÉMICO siguiendo ESTRICTAMENTE la Guía APA 7ma Edición que se proporciona abajo.

=== GUÍA NORMAS APA 7MA EDICIÓN (DE TU ARCHIVO OFICIAL) ===

{apa_guide}

=== FIN GUÍA APA ===

INFORMACIÓN DEL TRABAJO:
- **Tema:** {{tema}}
- **Tipo:** {{tipo_trabajo}}
- **Materia:** {{materia_nombre}}
- **Fecha:** {{__import__('datetime').datetime.now().strftime("%B %Y")}}

REQUERIMIENTOS OBLIGATORIOS SEGÚN GUÍA APA 7MA:

## 1. PORTADA ESTUDIANTE (Página 1)
Según la guía, la portada para estudiantes debe incluir (en este orden, centrado, doble espacio):
1. Título del trabajo (en negrita, capitalización de título, 3-4 líneas desde el margen superior)
2. Nombre del autor (tu nombre)
3. Afiliación institucional (Universidad)
4. Nombre y número del curso: {{materia_nombre}}
5. Nombre del profesor
6. Fecha de entrega (mes año)
7. Número de página 1 en esquina superior derecha

## 2. RESUMEN (Página 2 - OBLIGATORIO si el trabajo lo requiere)
- Título "Resumen" centrado, en negrita (Nivel 1)
- Texto en bloque (SIN sangría), 150-250 palabras
- Doble interlineado
- Palabras clave: en nueva línea, "Palabras clave:" en cursiva, luego palabras en minúsculas separadas por comas

## 3. CUERPO DEL TRABAJO (desde Página 3)
### Estructura según tipo de trabajo:
- **Ensayo/Revisión teórica**: Introducción → Desarrollo (con headings APA) → Conclusión
- **Investigación empírica**: Introducción → Método → Resultados → Discusión
- **Análisis de caso**: Introducción → Descripción del caso → Análisis → Conclusión
- **Reflexión**: Introducción → Desarrollo reflexivo → Conclusión

### Headings APA 7ma (Niveles 1-5) - TODOS EN NEGRITA:
- **Nivel 1**: Centrado, Negrita, Capitalización de Título → Texto en nuevo párrafo
- **Nivel 2**: Izquierda, Negrita, Capitalización de Título → Texto en nuevo párrafo  
- **Nivel 3**: Izquierda, Negrita, Cursiva, Capitalización de Título → Texto en nuevo párrafo
- **Nivel 4**: Sangrado, Negrita, Capitalización de Título, Punto final. Texto continúa en misma línea.
- **Nivel 5**: Sangrado, Negrita, Cursiva, Capitalización de Título, Punto final. Texto continúa en misma línea.

## 4. CITAS EN EL TEXTO (Autor-Año)
### Un autor: (Apellido, Año) o Apellido (Año)
### Dos autores: (Apellido1 & Apellido2, Año) o Apellido1 y Apellido2 (Año)
### Tres o más autores: (Apellido1 et al., Año) o Apellido1 et al. (Año) - ¡Desde la primera cita!
### Autor grupal con abreviatura: Primera: (Nombre Completo [Siglas], Año); Siguientes: (Siglas, Año)
### Mismo autor, mismo año: (Apellido, Añoa), (Apellido, Añob) - asignar letras por orden alfabético de título
### Cita directa corta (< 40 palabras): Entre comillas, con página: (Apellido, Año, p. X)
### Cita directa larga (≥ 40 palabras): Bloque separado, sangría 1.27 cm, SIN comillas, cita al final
### Parafraseo: (Apellido, Año) - PÁGINA OPCIONAL pero recomendada
### Fuente secundaria: (Autor original, Año, como se citó en Autor secundario, Año)

## 5. REFERENCIAS (Página final separada)
### Formato general: Sangría francesa (hanging indent) 1.27 cm
### Orden: Alfabético por apellido del primer autor
### Formatos principales:

**Libro:**
Apellido, A. A. (Año). *Título en cursiva: Subtítulo también en cursiva*. Editorial. https://doi.org/xxxxx

**Capítulo de libro editado:**
Apellido, A. A. (Año). Título del capítulo. En E. Editor (Ed.), *Título del libro en cursiva* (pp. xx-xx). Editorial.

**Artículo de revista (con DOI):**
Apellido, A. A., & Apellido, B. B. (Año). Título del artículo. *Nombre de la Revista en Cursiva*, Volumen(Número), pp-pp. https://doi.org/xxxxx

**Artículo de revista (SIN DOI, versión impresa):**
Apellido, A. A. (Año). Título del artículo. *Nombre de la Revista en Cursiva*, Volumen(Número), pp-pp.

**Página web:**
Apellido, A. A. (Año, Día Mes). Título de la página. *Nombre del Sitio*. URL

**Informe/Reporte:**
Autor/Organización. (Año). *Título en cursiva* (Número de reporte si aplica). Editorial/URL.

**Tesis/Disertación:**
Apellido, A. A. (Año). *Título en cursiva* [Tesis doctoral/maestría no publicada]. Universidad.

## 6. FORMATO GENERAL (Seguir guía al pie de la letra)
- **Papel**: Tamaño Carta (21.59 x 27.94 cm)
- **Márgenes**: 2.54 cm (1 pulgada) TODOS los lados
- **Fuente**: Times New Roman 12 pt (con serifa) O Calibri 11 pt / Arial 11 pt (sin serifa) - USAR LA MISMA EN TODO EL DOCUMENTO
- **Interlineado**: DOBLE en TODO el documento (incluyendo referencias, tablas, notas)
- **Sangría primera línea**: 1.27 cm para párrafos (NO en resumen, NO en referencias, NO en bloques de cita larga)
- **Alineación**: Izquierda (NO justificada)
- **Espaciado después de párrafos**: 0 pt (no agregar espacio extra)
- **Números de página**: Esquina superior derecha, TODAS las páginas (portada = página 1)
- **Running head**: SOLO para trabajos profesionales (NO para estudiantes) - máx 50 caracteres, MAYÚSCULAS, alineado izquierda

## 7. TABLAS Y FIGURAS (si aplica)
- Numeración consecutiva: Tabla 1, Tabla 2... / Figura 1, Figura 2...
- Título en cursiva, capitalización de título, arriba de la tabla/figura
- Nota debajo si es necesario (general, específica, probabilidad)

## 8. NOTAS AL PIE / FINALES
- Solo si son necesarias para contenido complementario
- Numeración superíndice en el texto
- Formato específico según guía

---

FORMATO DE SALIDA REQUERIDO:
Devuelve el trabajo COMPLETO en Markdown con esta estructura exacta:

# [TÍTULO DEL TRABAJO EN NEGRITA Y CAPITALIZACIÓN DE TÍTULO]

**Nombre del Autor**  
**Universidad**  
**{{materia_nombre}}**  
**Profesor: [Nombre del Profesor]**  
**Mes Año**

---

## Resumen

[Resumen de 150-250 palabras en bloque, sin sangría, doble interlineado implícito]

**Palabras clave:** palabra1, palabra2, palabra3

---

## Introducción

[Introducción al tema según tipo de trabajo. Nivel 1 heading implícito.]

### [Heading Nivel 2 según estructura]

[Contenido con citas APA correctas: (Apellido, Año) o Apellido (Año)]

#### [Heading Nivel 3 si necesario]

[Más contenido]

---

## [Conclusión / Discusión / Conclusiones según tipo]

[Conclusiones apropiadas al tipo de trabajo]

---

## Referencias

[Lista completa con sangría francesa, orden alfabético, formatos exactos según guía]
Apellido, A. A. (Año). *Título en cursiva*. Editorial. https://doi.org/xxxxx
Apellido, B. B., & Apellido, C. C. (Año). Título del artículo. *Revista en Cursiva*, Vol(Núm), pp-pp. https://doi.org/xxxxx
...

---

*Generado siguiendo estrictamente la Guía Normas APA 7ma Edición (normas-apa.org). Revisa y adapta según tu material específico.*
"""'''

# Replace the prompt
content = content[:prompt_start] + new_prompt + content[prompt_end+3:]

print('✅ Updated asistente_escritura_agente prompt')

# Now update fallback_escritura function
fallback_start = content.find('def fallback_escritura(tema, tipo_trabajo, materia_nombre):')
if fallback_start != -1:
    return_idx = content.find('return f"""', fallback_start)
    if return_idx != -1:
        end_return = content.find('"""', return_idx + 10)
        if end_return != -1:
            end_return += 3
            
            new_fallback_return = '''return f"""# {tema.upper()}

**Nombre del Autor**  
**Universidad**  
**{materia_nombre}**  
**Profesor: [Nombre del Profesor]**  
**{__import__('datetime').datetime.now().strftime("%B %Y")}}

---

## Resumen

[Resumen de 150-250 palabras en bloque, sin sangría. Describe el objetivo, método, resultados principales y conclusiones del trabajo sobre {tema}.]

**Palabras clave:** {tema.lower()}, psicología clínica, {tipo_trabajo.lower()}

---

## Introducción

[Introducción al tema {tema}. Presenta la importancia del tema en psicología clínica, define términos clave y establece el propósito del trabajo.]

### Desarrollo del Tema

[Desarrolla los puntos principales según el tipo de trabajo ({tipo_trabajo}). Usa headings APA Nivel 2 y 3 según sea necesario. Incluye citas en formato (Apellido, Año) o Apellido (Año).]

#### Concepto Clave 1

[Explicación con referencias al material de estudio.]

#### Concepto Clave 2

[Explicación con referencias al material de estudio.]

---

## Conclusión

[Síntesis de los puntos principales. Implicaciones para la práctica clínica. Limitaciones y futuras líneas de investigación.]

---

## Referencias

[Lista en orden alfabético con sangría francesa (1.27 cm). Formatos APA 7ma:]

Apellido, A. A. (Año). *Título del libro en cursiva*. Editorial. https://doi.org/xxxxx
Apellido, B. B., & Apellido, C. C. (Año). Título del artículo. *Revista en Cursiva*, Volumen(Número), pp-pp. https://doi.org/xxxxx
Organización. (Año). *Título del informe en cursiva*. URL

---

*Generado siguiendo Guía Normas APA 7ma Edición (normas-apa.org). Revisa y adapta citas y referencias a tu material específico.*
"""'''

            content = content[:return_idx] + new_fallback_return + content[end_return:]
            print('✅ Updated fallback_escritura')

# Now update generate_word_with_office references
word_func_start = content.find('def generate_word_with_office(materia_dir, trabajo_name, titulo):')
if word_func_start != -1:
    ref_section = content.find('referencias = [', word_func_start)
    if ref_section != -1:
        ref_end = content.find(']', ref_section)
        if ref_end != -1:
            ref_end += 1
            new_refs = '''referencias = [
            "American Psychological Association. (2020). *Publication manual of the American Psychological Association* (7th ed.). https://doi.org/10.1037/0000165-000",
            "Smith, J. A., & Jones, L. M. (2019). Efectos de la terapia cognitivo-conductual en trastornos de ansiedad. *Journal of Clinical Psychology*, 75(3), 456-467. https://doi.org/10.1002/jclp.22745",
            "Rodríguez, R. (2019). *Una guía para combatir el acoso escolar* [Archivo PDF]. https://www.url.com"
        ]'''
            content = content[:ref_section] + new_refs + content[ref_end:]
            print('✅ Updated Word references')

# Save
app_path.write_text(content, encoding='utf-8')
print('✅ Saved streamlit_app.py')

# Verify syntax
import ast
try:
    ast.parse(content)
    print('✅ Sintaxis correcta')
except SyntaxError as e:
    print(f'❌ Error en línea {e.lineno}: {e.msg}')
    lines = content.split('\\n')
    if e.lineno and e.lineno <= len(lines):
        print(f'   Código: {lines[e.lineno-1]}')