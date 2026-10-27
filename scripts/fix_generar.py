#!/usr/bin/env python3
"""Fix the powerpoint functions properly"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# The issue: line 362 has the function def but no body
# Line 363 has fallback_powerpoint which should be separate
# We need to add the body to generar_powerpoint_imagenes_agente

# Find the generar function
start = content.find('def generar_powerpoint_imagenes_agente(materia_nombre, trabajo_name, titulo):')
if start == -1:
    print('❌ Function not found')
    exit(1)

# Find the fallback function
fallback_start = content.find('def fallback_powerpoint(materia_nombre, trabajo_name, titulo):', start)
if fallback_start == -1:
    print('❌ Fallback not found')
    exit(1)

# Find the next function after fallback
next_func = content.find('\ndef ', fallback_start + 1)
if next_func == -1:
    next_func = content.find('\nif __name__', fallback_start)
if next_func == -1:
    next_func = len(content)

print(f'generar at {start}, fallback at {fallback_start}, next at {next_func}')

# The current content between them
current = content[start:fallback_start]
print(f'Current generar function:\n{repr(current)}')

# Build the proper generar function body
proper_generar = '''def generar_powerpoint_imagenes_agente(materia_nombre, trabajo_name, titulo):
    """Usa un agente para generar una presentacion PowerPoint con imagenes reales
    basadas en el material de la materia, no inventadas.
    """
    import subprocess
    
    materia_dir = get_materia_dir(materia_nombre)
    salidas_dir = materia_dir / "salidas"
    md_files = list(salidas_dir.glob("*.md")) if salidas_dir.exists() else []
    
    # Obtener contenido del libro principal
    libro_contenido = ""
    libro_file = materia_dir / "libro_principal.md"
    if libro_file.exists():
        try:
            with open(libro_file, "r", encoding="utf-8") as f:
                libro_contenido = f.read()[:3000]
        except:
            pass
    
    # Construir prompt manualmente para evitar problemas con f-strings anidados
    prompt_lines = [
        "Eres un experto en creacion de presentaciones academicas para psicologia clinica. Tu trabajo es crear una presentacion PowerPoint profesional con las siguientes caracteristicas:",
        "",
        "INFORMACION DE LA MATERIA:",
        f"- Materia: {materia_nombre}",
        f"- Titulo de la presentacion: {titulo}",
        f"- Trabajo: {trabajo_name}",
        "",
        "MATERIAL DISPONIBLE (del libro convertido a Markdown):",
    ]
    
    if libro_contenido:
        prompt_lines.append(libro_contenido[:2000])
    else:
        prompt_lines.append("No hay contenido disponible")
    
    prompt_lines.extend([
        "",
        "REQUERIMIENTOS CRITICOS:",
        "1. IMAGENES REALES O BASADAS EN MATERIAL - SIN INVENTAR: Todas las imagenes deben estar basadas en el contenido real del material de la materia. No uses imagenes genericas, fotos de stock o inventes descripciones. Cada imagen debe relacionarse directamente con:",
        "   - Conceptos teoricos del libro",
        "   - Experimentos o estudios mencionados",
        "   - Diagramas o modelos del material",
        "   - Datos o estadisticas del contenido",
        "",
        "2. DISENO ACADEMICO PROFESIONAL:",
        "   - Tema coherente (colores psicologia clinica: azules, verdes, blancos)",
        "   - Fuentes legibles (Times New Roman, Arial 12-14)",
        "   - Diapositivas con estructura clara: titulo, contenido, conclusion",
        "   - Maximo 15 diapositivas",
        "",
        "3. CONTENIDO POR DIALECTO:",
        "   - Diapositiva 1: Portada (titulo, nombre, curso, fecha)",
        "   - Diapositiva 2: Introduccion al tema",
        "   - Diapositivas 3-6: Conceptos principales (una idea principal cada una)",
        "   - Diapositivas 7-9: Estudios o investigaciones clave",
        "   - Diapositivas 10-12: Aplicaciones practicas",
        "   - Diapositiva 11: Preguntas frecuentes",
        "   - Diapositiva 12: Conclusiones",
        "   - Diapositiva 13: Referencias",
        "   - Diapositiva 14: Preguntas del publico",
        "   - Diapositiva 15: Agradece tu atencion",
        "",
        "4. FORMATO DE CADA DIALECTIVA:",
        "   - En cada diapositiva, especificar:",
        "     * Titulo de la diapositiva",
        "     * Punto principal (max 3-4 bullets)",
        "     * Referencia a la imagen basada en material (descripcion para insercion)",
        "     * Notas para el orador",
        "",
        "5. SALIDA OBLIGATORIA:",
        "   - Devolver el contenido estructurado en markdown que pueda convertirse a PowerPoint, con esta estructura para CADA diapositiva:",
        "## DIAPOSITIVA # - [Titulo de la diapositiva]",
        "**Punto Principal:** [3-4 bullets maximos]",
        "**Imagen basada en material:** [Descripcion detallada de que imagen poner, basada ESTRICTAMENTE en el material del libro/articulo - NO INVENTAR. Mencionar capitulos, paginas, conceptos especificos]",
        "**Notas para el orador:** [2-3 frases lo que diras sobre este tema]",
        "---",
    ])
    
    prompt = "\\n".join(prompt_lines)
    
    try:
        result = subprocess.run(
            ["python", "-c", f"""
import sys
sys.path.insert(0, r'{SCRIPTS_DIR}')
from subagent import subagent
result = subagent(
    description="Generador PowerPoint con imagenes reales",
    prompt=\"\"\"{prompt}\"\"\"
)
print(result)
"""],
            capture_output=True,
            text=True,
            cwd=str(SCRIPTS_DIR)
        )
        
        if result.returncode == 0 and result.stdout.strip():
            output_file = materia_dir / "salidas" / f"{trabajo_name}_estructura_ppt.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            return f"✅ **Estructura PowerPoint generada**\\n\\nSe guardo en: {output_file.name}\\n\\n{result.stdout[:500]}..."
        else:
            return fallback_powerpoint(materia_nombre, trabajo_name, titulo)
            
    except Exception as e:
        return fallback_powerpoint(materia_nombre, trabajo_name, titulo)


'''

# Replace from start of generar to start of fallback
content = content[:start] + proper_generar + content[fallback_start:]
path.write_text(content, encoding='utf-8')
print('✅ Fixed generar function')

# Check syntax
import ast
try:
    ast.parse(content)
    print('✅ Sintaxis correcta')
except SyntaxError as e:
    print(f'❌ Error en línea {e.lineno}: {e.msg}')
    lines = content.split('\n')
    if e.lineno and e.lineno <= len(lines):
        print(f'   Código: {lines[e.lineno-1]}')