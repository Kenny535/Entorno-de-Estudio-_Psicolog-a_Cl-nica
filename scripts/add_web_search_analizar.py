#!/usr/bin/env python3
"""Add web search to analizar_epub_agente for complementary references"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the analizar_epub_agente function
start = content.find('def analizar_epub_agente(materia_nombre):')
if start == -1:
    print('❌ Function not found')
    exit(1)

# Find next function
next_func = content.find('\ndef ', start + 1)
if next_func == -1:
    next_func = len(content)

# Get current function
current = content[start:next_func]

# Find the subprocess call section
subprocess_idx = current.find('subprocess.run')
if subprocess_idx == -1:
    print('❌ Subprocess not found in analizar')
    exit(1)

# Build new function with web search for complementary topics
new_func = '''def analizar_epub_agente(materia_nombre):
    """Usa un agente para analizar el libro convertido a Markdown.
    Extrae: capítulos, conceptos clave, resúmenes, preguntas de repaso.
    Incluye búsqueda web de referencias complementarias para temas poco cubiertos.
    """
    import subprocess
    
    materia_dir = get_materia_dir(materia_nombre)
    salidas_dir = materia_dir / "salidas"
    md_files = list(salidas_dir.glob("*.md")) if salidas_dir.exists() else []
    
    # Buscar el archivo principal del libro
    libro_file = None
    for f in md_files:
        if "libro" in f.name.lower() or "principal" in f.name.lower() or f.stat().st_size > 50000:
            libro_file = f
            break
    
    if not libro_file and md_files:
        libro_file = max(md_files, key=lambda f: f.stat().st_size)
    
    libro_contenido = ""
    if libro_file:
        try:
            with open(libro_file, "r", encoding="utf-8") as f:
                libro_contenido = f.read()[:8000]
        except:
            pass
    
    if not libro_contenido:
        return "❌ No se encontró material de libro para analizar. Primero importa un PDF."
    
    # === BÚSQUEDA WEB PARA TEMAS COMPLEMENTARIOS ===
    # Identificar temas principales del libro para buscar referencias actualizadas
    temas_para_buscar = []
    # Extraer algunos conceptos clave del contenido (primeras palabras de headers)
    import re
    headers = re.findall(r'^#{1,3}\\s+(.+)$', libro_contenido, re.MULTILINE)
    for h in headers[:5]:
        if len(h) > 5 and len(h) < 80:
            temas_para_buscar.append(h)
    
    referencias_complementarias = ""
    if temas_para_buscar:
        try:
            from web_search import web_search
            for tema in temas_para_buscar[:3]:  # Máximo 3 búsquedas
                try:
                    query = f"{tema} psicología investigación reciente 2022..2024"
                    result = web_search([query])
                    if result:
                        referencias_complementarias += f"\\n--- Referencias web para: {tema} ---\\n{str(result)[:800]}\\n"
                except:
                    pass
        except ImportError:
            pass
        except Exception:
            pass
    
    # Crear prompt para el agente
    prompt = f"""Eres un profesor experto en psicología clínica y análisis académico.
Analiza el siguiente contenido de libro de texto y genera una GUÍA DE ESTUDIO COMPLETA.

CONTENIDO DEL LIBRO (primeros 8000 caracteres):
{libro_contenido}

{referencias_complementarias}

TAREA: Genera en Markdown:

## 1. ESTRUCTURA DEL LIBRO
- Lista de capítulos/secciones principales detectados
- Organización temática general

## 2. CONCEPTOS CLAVE POR CAPÍTULO
Para cada capítulo identificado:
- **Conceptos fundamentales** (3-5 por capítulo)
- **Definiciones clave** (términos técnicos con explicación)
- **Teorías/Modelos** mencionados
- **Autores/Referencias** citados en el libro

## 3. RESÚMENES EJECUTIVOS
- Resumen de 150-200 palabras por capítulo principal
- Idea central y aportación al campo

## 4. PREGUNTAS DE REPASO Y EXAMEN
- 5-10 preguntas tipo examen por capítulo
- Niveles: Recordar, Comprender, Aplicar, Analizar (Bloom)
- Incluir respuestas modelo breves

## 5. MAPA CONCEPTUAL (texto)
- Relaciones entre conceptos principales
- Jerarquía: Teoría → Modelo → Concepto → Aplicación

## 6. REFERENCIAS COMPLEMENTARIAS ACTUALIZADAS (APA 7ma)
**IMPORTANTE**: Usa las fuentes web encontradas arriba + referencias del libro.
Formato APA 7ma con sangría francesa 1,27 cm:
- Libro: Apellido, A. A. (Año). *Título*. Editorial. DOI
- Artículo: Apellido, A. A., & Apellido, B. B. (Año). Título. *Revista*, Vol(Núm), pp-pp. DOI
- Web: Apellido, A. A. (Año, Día Mes). Título. *Sitio*. URL
- **Si usas fuentes web**: Formátalas correctamente con autor, fecha, título, sitio, URL

## 7. APLICACIÓN CLÍNICA
- Casos prácticos sugeridos
- Técnicas/Intervenciones derivadas del material
- Limitaciones y consideraciones éticas

FORMATO: Markdown con headings claros (##, ###). Usa negrita para términos clave.
*Generado con análisis de libro + búsqueda web de referencias actualizadas (APA 7ma).*
"""

    try:
        result = subprocess.run(
            ["python", "-c", f"""
import sys
sys.path.insert(0, r'{SCRIPTS_DIR}')
from subagent import subagent
result = subagent(
    description="Analizar libro EPUB/Markdown + referencias web",
    prompt=prompt
)
print(result)
"""],
            capture_output=True,
            text=True,
            cwd=str(SCRIPTS_DIR)
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Guardar resultado
            output_file = salidas_dir / "analisis_libro_completo.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            return f"✅ **Análisis completo generado y guardado**\\n\\nArchivo: `analisis_libro_completo.md`\\n\\n{result.stdout[:2000]}..."
        else:
            return analisis_basico(materia_nombre)
            
    except Exception as e:
        return analisis_basico(materia_nombre)

'''

content = content[:start] + new_func + content[next_func:]

with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Added web search to analizar_epub_agente')

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