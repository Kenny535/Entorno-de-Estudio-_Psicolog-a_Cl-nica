#!/usr/bin/env python3
"""Reemplaza la función generar_powerpoint_imágenes_agente con versión corregida"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# Encontrar el inicio de la función
start_marker = "def generar_powerpoint_imágenes_agente(materia Nombre, trabajo_name, titulo):"
start_idx = content.find(start_marker)
if start_idx == -1:
    print("❌ No se encontró la función")
    exit(1)

# Buscar el siguiente "def " después de la función actual
rest = content[start_idx + len(start_marker):]
next_def = rest.find("\ndef ")
if next_def == -1:
    print("❌ No se encontró el siguiente def")
    exit(1)

end_idx = start_idx + len(start_marker) + next_def + 1

# Nueva función corregida
new_func = '''def generar_powerpoint_imágenes_agente(materia Nombre, trabajo_name, titulo):
    """Usa un agente para generar una presentación PowerPoint con imágenes reales
    basadas en el material de la materia, no inventadas.
    """
    import subprocess
    
    materia_dir = get_materia_dir(materia Nombre)
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
        "Eres un experto en creación de presentaciones académicas para psicología clínica. Tu trabajo es crear una presentación PowerPoint profesional con las siguientes características:",
        "",
        "INFORMACIÓN DE LA MATERIA:",
        f"- Materia: {materia Nombre}",
        f"- Título de la presentación: {titulo}",
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
        "REQUERIMIENTOS CRÍTICOS:",
        "1. IMÁGENES REALES O BASADAS EN MATERIAL - SIN INVENTAR: Todas las imágenes deben estar basadas en el contenido real del material de la materia. No uses imágenes genéricas, fotos de stock o inventes descripciones. Cada imagen debe relacionarse directamente con:",
        "   - Conceptos teóricos del libro",
        "   - Experimentos o estudios mencionados",
        "   - Diagramas o modelos del material",
        "   - Datos o estadísticas del contenido",
        "",
        "2. DISEÑO ACADÉMICO PROFESIONAL:",
        "   - Tema coherente (colores psicología clínica: azules, verdes, blancos)",
        "   - Fuentes legibles (Times New Roman, Arial 12-14)",
        "   - Diapositivas con estructura clara: título, contenido, conclusión",
        "   - Máximo 15 diapositivas",
        "",
        "3. CONTENIDO POR DIALECTO:",
        "   - Diapositiva 1: Portada (título, nombre, curso, fecha)",
        "   - Diapositiva 2: Introducción al tema",
        "   - Diapositivas 3-6: Conceptos principales (una idea principal cada una)",
        "   - Diapositivas 7-9: Estudios o investigaciones clave",
        "   - Diapositivas 10-12: Aplicaciones prácticas",
        "   - Diapositiva 11: Preguntas frecuentes",
        "   - Diapositiva 12: Conclusiones",
        "   - Diapositiva 13: Referencias",
        "   - Diapositiva 14: Preguntas del público",
        "   - Diapositiva 15: Agradece tu atención",
        "",
        "4. FORMATO DE CADA DIALECTIVA:",
        "   - En cada diapositiva, especificar:",
        "     * Título de la diapositiva",
        "     * Punto principal (máx 3-4 bullets)",
        "     * Referencia a la imagen basada en material (descripción para inserción)",
        "     * Notas para el orador",
        "",
        "5. SALIDA OBLIGATORIA:",
        "   - Devolver el contenido estructurado en markdown que pueda convertirse a PowerPoint, con esta estructura para CADA diapositiva:",
        "## DIAPOSITIVA # - [Título de la diapositiva]",
        "**Punto Principal:** [3-4 bullets máximos]",
        "**Imagen basada en material:** [Descripción detallada de qué imagen poner, basada ESTRICTAMENTE en el material del libro/artículo - NO INVENTAR. Mencionar capítulos, páginas, conceptos específicos]",
        "**Notas para el orador:** [2-3 frases lo que dirás sobre este tema]",
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
    description="Generador PowerPoint con imágenes reales",
    prompt=\"\"\"{prompt}\"\"\"
)
print(result)
"""],
            capture_output=True,
            text=True,
            cwd=str(SCRIPTS_DIR)
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Guardar el resultado en un archivo para poder usarlo después
            output_file = materia_dir / "salidas" / f"{trabajo_name}_estructura_ppt.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            return f"✅ **Estructura PowerPoint generada**\\n\\nSe guardó en: {output_file.name}\\n\\n{result.stdout[:500]}..."
        else:
            return fallback_powerpoint(materia Nombre, trabajo_name, titulo)
            
    except Exception as e:
        return fallback_powerpoint(materia Nombre, trabajo_name, titulo)
'''

# Reemplazar
new_content = content[:start_idx] + new_func + content[end_idx:]
path.write_text(new_content, encoding='utf-8')
print('✅ Función corregida')