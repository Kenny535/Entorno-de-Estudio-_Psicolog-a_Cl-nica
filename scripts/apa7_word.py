#!/usr/bin/env python3
"""
Generador de documentos Word con formato APA 7a edicion
Uso: python apa7_word.py <ruta_materia> <nombre_trabajo> "<titulo_del_trabajo>"
Ejemplo: python apa7_word.py materias/Metodologia_Cuanti trabajo1 "Efecto de la terapia cognitivo-conductual en la ansiedad"
"""
import os
import sys
import pathlib
from datetime import datetime

try:
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.style import WD_STYLE_TYPE
except ImportError:
    print("Error: Se requiere python-docx. Instalalo con: pip install python-docx")
    sys.exit(1)

def setup_apa_styles(doc):
    """Configura estilos básicos para APA 7"""
    styles = doc.styles
    
    # Estilo Normal (interlineado doble, sangrado primera línea)
    style = styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    style.paragraph_format.line_spacing = 2.0
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.space_before = Pt(0)
    style.paragraph_format.first_line_indent = Inches(0.5)
    
    # Estilo para encabezados centrados (ej. título principal)
    if 'Heading 1' not in styles:
        heading1 = styles.add_style('Heading 1', WD_STYLE_TYPE.PARAGRAPH)
        heading1.font.name = 'Times New Roman'
        heading1.font.size = Pt(12)
        heading1.font.bold = True
        heading1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        heading1.paragraph_format.line_spacing = 2.0
        heading1.paragraph_format.space_after = Pt(12)
        heading1.paragraph_format.space_before = Pt(0)
    
    # Estilo para encabezados izquierdos (ej. secciones)
    if 'Heading 2' not in styles:
        heading2 = styles.add_style('Heading 2', WD_STYLE_TYPE.PARAGRAPH)
        heading2.font.name = 'Times New Roman'
        heading2.font.size = Pt(12)
        heading2.font.bold = True
        heading2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        heading2.paragraph_format.line_spacing = 2.0
        heading2.paragraph_format.space_after = Pt(12)
        heading2.paragraph_format.space_before = Pt(0)
        heading2.paragraph_format.first_line_indent = Inches(0)
    
    # Estilo para referencias (sangrado francés)
    if 'APA Reference' not in styles:
        ref_style = styles.add_style('APA Reference', WD_STYLE_TYPE.PARAGRAPH)
        ref_style.font.name = 'Times New Roman'
        ref_style.font.size = Pt(12)
        ref_style.paragraph_format.line_spacing = 2.0
        ref_style.paragraph_format.space_after = Pt(0)
        ref_style.paragraph_format.space_before = Pt(0)
        ref_style.paragraph_format.left_indent = Inches(0)
        ref_style.paragraph_format.first_line_indent = Inches(-0.5)  # sangrado francés

def add_title_page(doc, title, author, institution, course, professor, date):
    """Agrega la portada APA 7"""
    # Título (centrado, negrita, mayúsculas y minúsculas)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(title.upper())
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    run.font.bold = True
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(24)
    
    # Autor
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(author)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(12)
    
    # Institución
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(institution)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(12)
    
    # Curso
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(course)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(12)
    
    # Profesor
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(professor)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(12)
    
    # Fecha
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(date)
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    p.paragraph_format.line_spacing = 2.0
    p.paragraph_format.space_after = Pt(24)
    
    # Salto de página después de la portada
    doc.add_page_break()

def add_headings(doc, text):
    """
    Procesa texto simple y agrega encabezados detectados por sintaxis markdown básica
    Soporta: # Título, ## Subtítulo, ### Subsubtítulo
    También maneja listas y párrafos normales.
    """
    lines = text.split('\\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            doc.add_paragraph()  # línea vacía
            continue
            
        # Encabezados markdown
        if stripped.startswith('# '):
            p = doc.add_paragraph(stripped[2:])
            p.style = 'Heading 1'
        elif stripped.startswith('## '):
            p = doc.add_paragraph(stripped[3:])
            p.style = 'Heading 2'
        elif stripped.startswith('### '):
            p = doc.add_paragraph(stripped[4:])
            p.style = 'Heading 3'
        elif stripped.startswith('- ') or stripped.startswith('* '):
            # Lista con viñeta
            p = doc.add_paragraph(stripped[2:], style='List Bullet')
        elif stripped[0].isdigit() and '. ' in stripped[:5]:
            # Lista numerada simple (ej. "1. Texto")
            p = doc.add_paragraph(stripped[stripped.find('. ')+2:], style='List Number')
        else:
            # Párrafo normal
            p = doc.add_paragraph(stripped)
            p.style = 'Normal'

def add_references(doc, references):
    """Agrega la sección de referencias"""
    if not references:
        return
        
    doc.add_page_break()
    p = doc.add_paragraph('Referencias')
    p.style = 'Heading 1'
    p.paragraph_format.space_after = Pt(12)
    
    for ref in references:
        p = doc.add_paragraph(ref)
        p.style = 'APA Reference'

def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    
    materia_dir = pathlib.Path(sys.argv[1])
    trabajo_name = sys.argv[2]
    title = sys.argv[3]
    
    if not materia_dir.exists():
        print(f"Error: La carpeta de materia {materia_dir} no existe.")
        sys.exit(1)
    
    # Datos por defecto (en un futuro se podrían leer de un config)
    author = "Tu Nombre"
    institution = "Nombre de tu Universidad"
    course = materia_dir.name.replace('_', ' ')
    professor = "Nombre del Profesor"
    date = datetime.now().strftime("%B %d, %Y")
    
    # Crear documento
    doc = Document()
    setup_apa_styles(doc)
    
    # Portada
    add_title_page(doc, title, author, institution, course, professor, date)
    
    # Contenido: intentar leer desde memory.md o fuentes_usadas.md
    content_parts = []
    
    memory_file = materia_dir / "memory.md"
    if memory_file.exists():
        content_parts.append(memory_file.read_text(encoding="utf-8"))
    
    fuentes_file = materia_dir / "fuentes_usadas.md"
    if fuentes_file.exists():
        content_parts.append("\\n\\n## Fuentes Consultadas\\n\\n" + fuentes_file.read_text(encoding="utf-8"))
    
    libro_file = materia_dir / "libro_principal.md"
    if libro_file.exists():
        content_parts.append("\\n\\n## Contenido del Libro Principal\\n\\n" + libro_file.read_text(encoding="utf-8"))
    
    full_content = "\\n\\n".join(content_parts) if content_parts else "# Contenido\\n\\nEscribe aquí tu trabajo..."
    
    add_headings(doc, full_content)
    
    # Referencias de ejemplo (en un futuro se extraerían de fuentes_usadas.md)
    example_references = [
        "American Psychological Association. (2020). *Publication manual of the American Psychological Association* (7th ed.). https://doi.org/10.1037/0000165-000",
        "Smith, J. A., & Jones, L. M. (2019). Efectos de la terapia cognitivo-conductual en trastornos de ansiedad. *Journal of Clinical Psychology*, 75(3), 456-467. https://doi.org/10.1002/jclp.22745"
    ]
    add_references(doc, example_references)
    
    # Guardar
    output_dir = materia_dir / "salidas"
    output_dir.mkdir(exist_ok=True)
    safe_title = "".join(c for c in title if c.isalnum() or c in " _-").rstrip()
    filename = output_dir / f"{trabajo_name}_{safe_title}.docx"
    doc.save(filename)
    
    print(f"Documento Word generado: {filename}")
    print("\\nProximos pasos:")
    print("1. Abre el documento en Microsoft Word o LibreOffice")
    print("2. Revisa y edita el contenido como necesites")
    print("3. Verifica que las referencias sigan exactamente el formato APA 7")
    print("4. Guarda una copia en tu unidad de almacenamiento universitaria")

if __name__ == "__main__":
    main()