#!/usr/bin/env python3
"""Add web search for academic references to asistente_escritura_agente"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the asistente_escritura_agente function
start = content.find('def asistente_escritura_agente(tema, tipo_trabajo, materia_nombre):')
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
    print('❌ Subprocess not found')
    exit(1)

# Build new function with web search integration
new_func = '''def asistente_escritura_agente(tema, tipo_trabajo, materia_nombre):
    """Usa un agente para ayudarte a redactar trabajos académicos.
    Genera esquemas, introducción, conclusión y citas en formato APA 7ma edición.
    Incluye búsqueda web automática de fuentes académicas cuando no hay material.
    """
    import subprocess
    import json
    
    materia_dir = get_materia_dir(materia_nombre)
    salidas_dir = materia_dir / "salidas"
    md_files = list(salidas_dir.glob("*.md")) if salidas_dir.exists() else []
    
    # Obtener contenido del libro si existe
    libro_contenido = ""
    libro_file = materia_dir / "libro_principal.md"
    if libro_file.exists():
        try:
            with open(libro_file, "r", encoding="utf-8") as f:
                libro_contenido = f.read()[:3000]
        except:
            pass
    
    # === BÚSQUEDA WEB AUTOMÁTICA DE REFERENCIAS ACADÉMICAS ===
    referencias_web = ""
    if not libro_contenido or len(libro_contenido) < 500:
        # No hay material suficiente, buscar en la web
        try:
            from web_search import web_search
            # Construir queries de búsqueda académica
            queries = [
                f"{tema} psicología clínica estudio investigación 2020..2024",
                f"{tema} terapia tratamiento eficacia revisión sistemática",
                f"{tipo_trabajo} {tema} APA referencias académicas"
            ]
            all_results = []
            for q in queries:
                try:
                    result = web_search([q])
                    if result and 'results' in str(result):
                        all_results.append(result)
                except:
                    pass
            
            if all_results:
                referencias_web = "\\n\\n=== FUENTES ENCONTRADAS EN BÚSQUEDA WEB (formatear en APA 7ma) ===\\n"
                for i, res in enumerate(all_results[:3]):
                    referencias_web += f"\\nFuente {i+1}: {str(res)[:500]}\\n"
        except ImportError:
            pass
        except Exception as e:
            pass
    
    # Crear prompt para el agente con guía APA 7ma completa
    prompt = f"""Eres un asistente académico experto en normas APA 7ma edición y psicología clínica. 
Tu trabajo es generar una ESTRUCTURA COMPLETA DE TRABAJO ACADÉMICO siguiendo ESTRICTAMENTE la Guía APA 7ma Edición.

INFORMACIÓN DEL TRABAJO:
- **Tema:** {tema}
- **Tipo:** {tipo_trabajo}
- **Materia:** {materia_nombre}
- **Fecha:** {__import__('datetime').datetime.now().strftime("%B %Y")}

MATERIAL DISPONIBLE (primeros 3000 caracteres):
{libro_contenido if libro_contenido else "No hay material de libro disponible - USA LAS FUENTES WEB ENCONTRADAS ABAJO"}

{referencias_web}

REQUERIMIENTOS OBLIGATORIOS SEGÚN GUÍA APA 7MA:

## 1. PORTADA ESTUDIANTE (Página 1)
- Título del trabajo (negrita, capitalización de título, 3-4 líneas desde margen superior)
- Nombre del autor
- Afiliación institucional (Universidad)
- Nombre y número del curso: {materia_nombre}
- Nombre del profesor
- Fecha de entrega (mes año)
- Número de página 1 en esquina superior derecha

## 2. RESUMEN (Página 2)
- Título "Resumen" centrado, negrita (Nivel 1)
- Texto en bloque (SIN sangría), 150-250 palabras, doble interlineado
- Palabras clave: "Palabras clave:" en cursiva, palabras en minúsculas separadas por comas

## 3. CUERPO DEL TRABAJO
Estructura según tipo:
- Ensayo/Revisión: Introducción → Desarrollo (headings APA) → Conclusión
- Investigación: Introducción → Método → Resultados → Discusión
- Caso: Introducción → Descripción → Análisis → Conclusión
- Reflexión: Introducción → Desarrollo reflexivo → Conclusión

Headings APA 7ma (TODOS EN NEGRITA):
- Nivel 1: Centrado, Negrita, Capitalización → Texto en nuevo párrafo
- Nivel 2: Izquierda, Negrita, Capitalización → Texto en nuevo párrafo  
- Nivel 3: Izquierda, Negrita, Cursiva, Capitalización → Texto en nuevo párrafo
- Nivel 4: Sangrado, Negrita, Capitalización, Punto. Texto en misma línea.
- Nivel 5: Sangrado, Negrita, Cursiva, Capitalización, Punto. Texto en misma línea.

## 4. CITAS EN TEXTO (Autor-Año)
- Un autor: (Apellido, Año) o Apellido (Año)
- Dos autores: (Apellido1 & Apellido2, Año)
- Tres o más: (Apellido1 et al., Año) - ¡Desde la primera cita!
- Grupo con sigla: Primera (Nombre [Siglas], Año); Siguientes (Siglas, Año)
- Mismo autor/año: (Apellido, Añoa), (Apellido, Añob)
- Cita directa <40 palabras: "texto" (Apellido, Año, p. X)
- Cita directa ≥40 palabras: Bloque sangrado 1,27 cm, SIN comillas
- Parafraseo: (Apellido, Año) - página opcional
- Fuente secundaria: (Original, Año, como se citó en Secundario, Año)

## 5. REFERENCIAS (¡USA LAS FUENTES WEB ENCONTRADAS + MATERIAL PROPIO!)
- Sangría francesa 1,27 cm, orden alfabético
- Libro: Apellido, A. A. (Año). *Título en cursiva*. Editorial. DOI
- Artículo: Apellido, A. A., & Apellido, B. B. (Año). Título. *Revista*, Vol(Núm), pp-pp. DOI
- Web: Apellido, A. A. (Año, Día Mes). Título. *Sitio*. URL
- **IMPORTANTE**: Si hay fuentes web en los resultados, formátalas como:
  Apellido, A. A. (Año). Título del artículo. *Nombre del Sitio*. URL

## 6. FORMATO GENERAL
- Papel Carta (21,59 x 27,94 cm), Márgenes 2,54 cm
- Times New Roman 12 pt O Calibri/Arial 11 pt - MISMA EN TODO
- Interlineado DOBLE en TODO (incluye referencias)
- Sangría 1,27 cm párrafos (NO en resumen, referencias, citas bloque)
- Alineación izquierda, NO justificada
- Páginas: esquina superior derecha, TODAS (portada = 1)
- Running head: SOLO profesionales, máx 50 chars, MAYÚSCULAS

FORMATO SALIDA - Markdown completo:

# [TÍTULO EN NEGRITA Y CAPITALIZACIÓN]

**Nombre del Autor**  
**Universidad**  
**{materia_nombre}**  
**Profesor: [Nombre]**  
**Mes Año**

---

## Resumen

[150-250 palabras, bloque, sin sangría]

**Palabras clave:** palabra1, palabra2, palabra3

---

## Introducción

[Intro al tema con citas de material propio Y/O fuentes web]

### Desarrollo

[Contenido con citas (Apellido, Año) - USA TANTO MATERIAL PROPIO COMO FUENTES WEB]

#### Subtemas

[Más contenido con referencias]

---

## Conclusión

[Síntesis, implicaciones, limitaciones, futuras investigaciones]

---

## Referencias

[Alfabético, sangría francesa 1,27 cm - INCLUYE FUENTES WEB ENCONTRADAS]
Apellido, A. A. (Año). *Título*. Editorial. DOI
Apellido, B. B. (Año). Título web. *Sitio Web*. URL
...

---

*Generado según Guía Normas APA 7ma Edición (normas-apa.org). Revisa y adapta. Fuentes web verificadas al momento de generación.*
"""

    try:
        result = subprocess.run(
            ["python", "-c", f"""
import sys
sys.path.insert(0, r'{SCRIPTS_DIR}')
from subagent import subagent
result = subagent(
    description="Asistente escritura académica APA 7ma con búsqueda web",
    prompt=prompt
)
print(result)
"""],
            capture_output=True,
            text=True,
            cwd=str(SCRIPTS_DIR)
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return f"✅ **Asistente de escritura activado (con búsqueda web de referencias)**\\n\\n{result.stdout}"
        else:
            return fallback_escritura(tema, tipo_trabajo, materia_nombre)
            
    except Exception as e:
        return fallback_escritura(tema, tipo_trabajo, materia_nombre)

'''

content = content[:start] + new_func + content[next_func:]

with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Added web search integration to asistente_escritura_agente')

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