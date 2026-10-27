#!/usr/bin/env python3
"""Add web search to generar_powerpoint_imagenes_agente"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the generar_powerpoint_imagenes_agente function
start = content.find('def generar_powerpoint_imagenes_agente(materia_nombre, trabajo_name, titulo):')
if start == -1:
    print('❌ Function not found')
    exit(1)

# Find next function
next_func = content.find('\ndef ', start + 1)
if next_func == -1:
    next_func = len(content)

# Get current function
current = content[start:next_func]

# Build new function with web search for images and references
new_func = '''def generar_powerpoint_imagenes_agente(materia_nombre, trabajo_name, titulo):
    """Usa un agente para generar una presentación PowerPoint con imágenes reales
    basadas en el material de la materia, no inventadas.
    Incluye búsqueda web de imágenes académicas y referencias actualizadas.
    """
    import subprocess
    
    materia_dir = get_materia_dir(materia_nombre)
    salidas_dir = materia_dir / "salidas"
    trabajo_file = salidas_dir / f"{trabajo_name}.md"
    
    # Leer el trabajo base
    trabajo_contenido = ""
    if trabajo_file.exists():
        try:
            with open(trabajo_file, "r", encoding="utf-8") as f:
                trabajo_contenido = f.read()[:5000]
        except:
            pass
    
    # También leer el libro principal para imágenes basadas en material
    libro_file = materia_dir / "libro_principal.md"
    libro_contenido = ""
    if libro_file.exists():
        try:
            with open(libro_file, "r", encoding="utf-8") as f:
                libro_contenido = f.read()[:4000]
        except:
            pass
    
    if not trabajo_contenido and not libro_contenido:
        return "❌ No hay material (trabajo ni libro) para generar la presentación."
    
    # === BÚSQUEDA WEB PARA IMÁGENES Y REFERENCIAS ACTUALES ===
    # Extraer temas clave para buscar imágenes y referencias
    import re
    temas_slides = []
    # Headers del trabajo
    headers = re.findall(r'^#{1,3}\\s+(.+)$', trabajo_contenido, re.MULTILINE)
    for h in headers[:8]:
        if len(h) > 5:
            temas_slides.append(h)
    # Si no hay headers en trabajo, usar libro
    if not temas_slides and libro_contenido:
        headers = re.findall(r'^#{1,3}\\s+(.+)$', libro_contenido, re.MULTILINE)
        for h in headers[:8]:
            if len(h) > 5:
                temas_slides.append(h)
    
    imagenes_web = ""
    referencias_actuales = ""
    if temas_slides:
        try:
            from web_search import web_search
            for i, tema in enumerate(temas_slides[:5]):  # Máx 5 búsquedas
                try:
                    # Buscar imágenes académicas (diagramas, figuras, modelos)
                    query_img = f"{tema} diagrama figura modelo psicología site:edu OR site:org OR site:gov"
                    result_img = web_search([query_img])
                    if result_img:
                        imagenes_web += f"\\n--- Imágenes/Figuras para Slide {i+1}: {tema} ---\\n{str(result_img)[:600]}\\n"
                    
                    # Buscar referencias actuales para ese tema
                    query_ref = f"{tema} investigación 2023 2024 psicología clínica"
                    result_ref = web_search([query_ref])
                    if result_ref:
                        referencias_actuales += f"\\n--- Referencias 2023-2024 para: {tema} ---\\n{str(result_ref)[:600]}\\n"
                except:
                    pass
        except ImportError:
            pass
        except Exception:
            pass
    
    # Crear prompt para el agente
    prompt = f"""Eres un diseñador experto en presentaciones académicas APA 7ma edición para psicología clínica.
Genera una ESTRUCTURA COMPLETA DE POWERPOINT (15-20 diapositivas) con IMÁGENES REALES basadas en material.

INFORMACIÓN:
- **Título:** {titulo}
- **Trabajo base:** {trabajo_name}
- **Materia:** {materia_nombre}

CONTENIDO BASE (trabajo):
{trabajo_contenido[:3000] if trabajo_contenido else "No hay trabajo previo"}

CONTENIDO LIBRO (para imágenes basadas en material):
{libro_contenido[:2000] if libro_contenido else "No hay libro"}

{imagenes_web}

{referencias_actuales}

REGLAS CRÍTICAS - IMÁGENES:
✅ SOLO imágenes BASADAS EN MATERIAL REAL:
   - Figuras/diagramas del libro (capítulo X, página Y)
   - Gráficos de estudios citados en el material
   - Modelos teóricos explicados en el contenido
   - Capturas de tablas/datos del libro/trabajo

❌ PROHIBIDO INVENTAR:
   - "Imagen ilustrativa de..."
   - "Diagrama conceptual genérico"
   - Cualquier imagen NO referenciada al material específico

CADA SLIDE CON IMAGEN DEBE INCLUIR:
- Descripción exacta: "Figura 3.2 del Capítulo 5, página 142: Diagrama del modelo ABC"
- O: "Gráfico de resultados del Estudio Smith (2023) citado en página 89"
- O: "Tabla 1 del material: Comparación de tratamientos"

ESTRUCTURA REQUERIDA (15-20 slides):

## Slide 1: PORTADA APA
- Título completo, autor, universidad, {materia_nombre}, fecha
- Running head si profesional

## Slide 2: ÍNDICE / AGENDA
- Lista de secciones principales

## Slide 3: INTRODUCCIÓN / PROBLEMA
- Planteamiento del tema
- **Imagen**: Diagrama del problema del libro (cap/pág)

## Slides 4-8: DESARROLLO TEÓRICO (una por concepto clave)
- Concepto + definición
- **Imagen OBLIGATORIA por slide**: Figura/modelo/gráfico del MATERIAL
- Cita APA en slide: (Autor, Año)

## Slides 9-12: EVIDENCIA EMPÍRICA / APLICACIÓN
- Estudios de caso / investigaciones
- **Imagen**: Gráficos de resultados, tablas de datos DEL MATERIAL
- Referencias web 2023-2024 encontradas arriba

## Slide 13: DISCUSIÓN / IMPLICACIONES CLÍNICAS
- Puntos clave para práctica

## Slide 14: LIMITACIONES Y FUTURA INVESTIGACIÓN

## Slide 15: REFERENCIAS PRINCIPALES (APA 7ma)
- Top 8-10 referencias (material + web 2023-2024)
- Sangría francesa visual

## Slide 16+: PREGUNTAS / CONTACTO

FORMATO SALIDA - Markdown para cada slide:

---
### Slide 1: [Título Slide]
**Tipo:** Portada / Contenido / Evidencia / Referencias
**Contenido:**
- Punto 1
- Punto 2
**Imagen REQUERIDA:** [Descripción exacta con cap/pág del material O "No aplica"]
**Nota del ponente:** [Guión sugerido]
**Cita en slide:** (Apellido, Año)

---
### Slide 2: [Título Slide]
...

IMPORTANTE: 
- Si NO hay imagen del material para un slide, escribe: **Imagen REQUERIDA: No hay material visual en el libro/trabajo para este slide - buscar figura original**
- USA las referencias web 2023-2024 encontradas arriba en slides de evidencia
- Formato APA 7ma en todo momento
"""

    try:
        result = subprocess.run(
            ["python", "-c", f"""
import sys
sys.path.insert(0, r'{SCRIPTS_DIR}')
from subagent import subagent
result = subagent(
    description="Generar PowerPoint APA 7ma con imágenes reales + búsqueda web",
    prompt=prompt
)
print(result)
"""],
            capture_output=True,
            text=True,
            cwd=str(SCRIPTS_DIR)
        )
        
        if result.returncode == 0 and result.stdout.strip():
            output_file = salidas_dir / f"{trabajo_name}_powerpoint_estructura.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            return f"✅ **Estructura PowerPoint generada con búsqueda web de imágenes/referencias**\\n\\nArchivo: `{trabajo_name}_powerpoint_estructura.md`\\n\\n{result.stdout[:2000]}..."
        else:
            return fallback_powerpoint(materia_nombre, trabajo_name, titulo)
            
    except Exception as e:
        return fallback_powerpoint(materia_nombre, trabajo_name, titulo)

'''

content = content[:start] + new_func + content[next_func:]

with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Added web search to generar_powerpoint_imagenes_agente')

# Verify syntax
import ast
try:
    ast.parse(content)
    print('✅ Sintaxis correcta')
except SyntaxError as e:
    print(f'❌ Error en línea {e.lineno}: {e.msg}')
    lines = content.split('\\n')
    if e.lineno and e.lineno <= len(lines):
        for i in range(max(0, e.lineno-5), min(len(lines), e.lineno+5)):
            print(f'{i+1}: {lines[i]}')