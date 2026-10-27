#!/usr/bin/env python3
"""
Menú interactivo para el entorno de estudio de Psicología Clínica
Ruta base fija: C:\\Universidad\\estudio-psicologia
"""
import os
import sys
import subprocess
import pathlib

# Añadir el directorio de scripts al path para importar config
SCRIPTS_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from config import BASE_DIR, MATERIAS_DIR, list_materias, get_materia_dir

def clear_screen():
    """Limpia la pantalla según el sistema operativo."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Imprime el encabezado del menú."""
    print("=" * 60)
    print("[Estudio] ENTORNO DE ESTUDIO - PSICOLOGIA CLINICA")
    print("=" * 60)
    print(f"[Carpeta] Ruta base: {BASE_DIR}")
    print(f"[Libros] Materias configuradas: {len(list_materias())}")
    print("-" * 60)

def print_menu():
    """Imprime las opciones del menú."""
    print("\n[Menu] MENU PRINCIPAL:")
    print("  1. [Libros] Crear nueva materia")
    print("  2. [Libro] Importar libro del facilitador (PDF -> Markdown)")
    print("  3. [Trabajo] Generar trabajo en Word (APA 7a edicion)")
    print("  4. [Estadistica] Ver materias existentes")
    print("  5. [Salida] Salir")
    print("-" * 60)

def run_script(script_name, *args):
    """Ejecuta un script de Python con los argumentos dados."""
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"[ERROR] Error: No se encontró el script {script_name}")
        return False
    
    try:
        cmd = [sys.executable, str(script_path)] + list(args)
        result = subprocess.run(cmd, cwd=str(SCRIPTS_DIR), capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
            if result.stderr:
                print("[WARNING]  Advertencias:", result.stderr)
            return True
        else:
            print(f"[ERROR] Error al ejecutar {script_name}:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return False

def crear_materia():
    """Opcion para crear una nueva materia."""
    clear_screen()
    print_header()
    print("\n[Libros] CREAR NUEVA MATERIA")
    print("-" * 30)
    
    materia_name = input("Nombre de la materia: ").strip()
    if not materia_name:
        print("[ERROR] El nombre no puede estar vacio.")
        input("\nPresione Enter para continuar...")
        return
    
    print(f"\nCreando materia: {materia_name}")
    success = run_script("init_materia.py", materia_name)
    
    if success:
        print(f"\n[OK] Materia '{materia_name}' creada exitosamente.")
    else:
        print(f"\n[ERROR] Falló la creacion de la materia '{materia_name}'.")
    
    input("\nPresione Enter para continuar...")

def importar_libro():
    """Opción para importar un libro PDF."""
    clear_screen()
    print_header()
    print("\n[Libro] IMPORTAR LIBRO DEL FACILITADOR")
    print("-" * 40)
    
    # Primero, pedir la ruta del PDF
    pdf_path = input("Ruta completa al archivo PDF: ").strip().strip('"')
    if not pdf_path:
        print("[ERROR] Debe especificar una ruta.")
        input("\nPresione Enter para continuar...")
        return
    
    pdf_path = pathlib.Path(pdf_path)
    if not pdf_path.exists():
        print(f"[ERROR] El archivo no existe: {pdf_path}")
        input("\nPresione Enter para continuar...")
        return
    
    if pdf_path.suffix.lower() != '.pdf':
        print("[WARNING]  Advertencia: El archivo no tiene extensión .pdf")
        confirm = input("¿Continuar de todos modos? (s/n): ").lower()
        if confirm != 's':
            return
    
    # Luego, pedir o seleccionar la materia
    materias = list_materias()
    materia_name = None
    
    if materias:
        print("\nMaterias existentes:")
        for i, m in enumerate(materias, 1):
            print(f"  {i}. {m}")
        print("  0. Crear nueva materia")
        
        choice = input("\nSeleccione una materia (número) o 0 para crear nueva: ").strip()
        
        if choice == "0":
            materia_name = input("Nombre de la nueva materia: ").strip()
            if not materia_name:
                print("[ERROR] Nombre requerido.")
                input("\nPresione Enter para continuar...")
                return
            # Crear la materia primero
            crear_materia()  # Esto limpiará la pantalla, así que volvemos al menú de importar
            clear_screen()
            print_header()
            print("\n📖 IMPORTAR LIBRO DEL FACILITADOR")
            print("-" * 40)
            print(f"Ruta PDF: {pdf_path}")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(materias):
                    materia_name = materias[idx]
                else:
                    print("[ERROR] Seleccion invalida.")
                    input("\nPresione Enter para continuar...")
                    return
            except ValueError:
                # Quizás el usuario escribió el nombre directamente
                materia_name = choice
    else:
        print("\nNo hay materias existentes. Debe crear una primero.")
        materia_name = input("Nombre de la nueva materia: ").strip()
        if not materia_name:
            print("[ERROR] Nombre requerido.")
            input("\nPresione Enter para continuar...")
            return
        # Crear la materia
        crear_materia()
        clear_screen()
        print_header()
        print("\n📖 IMPORTAR LIBRO DEL FACILITADOR")
        print("-" * 40)
        print(f"Ruta PDF: {pdf_path}")
    
    if not materia_name:
        print("[ERROR] No se especificó materia.")
        input("\nPresione Enter para continuar...")
        return
    
    print(f"\nImportando libro para materia: {materia_name}")
    success = run_script("convert_pdf_md.py", str(pdf_path), materia_name)
    
    if success:
        print(f"\n[OK] Libro importado para materia '{materia_name}'.")
        print(f"📁 Revisa: {get_materia_dir(materia_name)}")
    else:
        print(f"\n[ERROR] Falló la importación del libro.")
    
    input("\nPresione Enter para continuar...")

def generar_word():
    """Opción para generar un trabajo en Word."""
    clear_screen()
    print_header()
    print("\n[Trabajo] GENERAR TRABAJO EN WORD (APA 7)")
    print("-" * 40)
    
    materias = list_materias()
    if not materias:
        print("[ERROR] No hay materias existentes. Cree una primero.")
        input("\nPresione Enter para continuar...")
        return
    
    print("Materias disponibles:")
    for i, m in enumerate(materias, 1):
        print(f"  {i}. {m}")
    
    choice = input("\nSeleccione materia (numero): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(materias):
            materia_name = materias[idx]
        else:
            print("[ERROR] Seleccion invalida.")
            input("\nPresione Enter para continuar...")
            return
    except ValueError:
        print("[ERROR] Por favor ingrese un numero.")
        input("\nPresione Enter para continuar...")
        return
    
    materia_dir = get_materia_dir(materia_name)
    
    trabajo_name = input("\nNombre interno del trabajo (ej. trabajo1, parcial): ").strip()
    if not trabajo_name:
        trabajo_name = "trabajo1"
    
    titulo = input("Titulo completo del trabajo: ").strip()
    if not titulo:
        print("[ERROR] El título es requerido.")
        input("\nPresione Enter para continuar...")
        return
    
    print(f"\nGenerando trabajo para materia: {materia_name}")
    print(f"Nombre interno: {trabajo_name}")
    print(f"Titulo: {titulo}")
    
    # Verificar si existe apa7_word.py
    word_script = SCRIPTS_DIR / "apa7_word.py"
    if not word_script.exists():
        print("[WARNING]  El generador de Word (apa7_word.py) aún no está creado.")
        print("   Se creará automáticamente después de esta opción.")
        # Crearemos el script después
        crear_apa7_word_script()
        if not word_script.exists():
            print("[ERROR] No se pudo crear el generador de Word.")
            input("\nPresione Enter para continuar...")
            return
    
    success = run_script("apa7_word.py", str(materia_dir), trabajo_name, titulo)
    
    if success:
        print(f"\n[OK] Trabajo generado exitosamente.")
        salida_dir = materia_dir / "salidas"
        print(f"[Archivo] Archivo guardado en: {salida_dir}")
        # Mostrar los archivos generados
        if salida_dir.exists():
            docs = list(salida_dir.glob("*.docx"))
            if docs:
                print(f"[Documento] Ultimo documento: {docs[-1].name}")
    else:
        print(f"\n[ERROR] Falló la generación del trabajo.")
    
    input("\nPresione Enter para continuar...")

def ver_materias():
    """Opción para ver materias existentes."""
    clear_screen()
    print_header()
    print("\n[Estadistica] MATERIAS EXISTENTES")
    print("-" * 30)
    
    materias = list_materias()
    if not materias:
        print("[Vacio] No hay materias creadas aun.")
        print("\n[Idea] Use la opcion 1 para crear su primera materia.")
    else:
        for i, materia in enumerate(materias, 1):
            materia_dir = get_materia_dir(materia)
            print(f"\n{i}. [Libros] {materia}")
            print(f"   [Carpeta] {materia_dir}")
            
            # Contar archivos
            guia = materia_dir / "guia_aprendizaje.md"
            libro = materia_dir / "libro_principal.md"
            memory = materia_dir / "memory.md"
            fuentes = materia_dir / "fuentes_usadas.md"
            salidas_dir = materia_dir / "salidas"
            
            archivos = []
            if guia.exists(): archivos.append("guia")
            if libro.exists(): archivos.append("libro")
            if memory.exists(): archivos.append("memory")
            if fuentes.exists(): archivos.append("fuentes")
            if salidas_dir.exists():
                doc_count = len(list(salidas_dir.glob("*.docx")))
                archivos.append(f"{doc_count} trabajos")
            
            if archivos:
                print(f"   [Archivo] Contenido: {', '.join(archivos)}")
    
    print("\n" + "-" * 60)
    input("\nPresione Enter para continuar...")

def crear_apa7_word_script():
    """Crea el script apa7_word.py si no existe."""
    word_script_path = SCRIPTS_DIR / "apa7_word.py"
    if word_script_path.exists():
        return
    
    print("\n[Herramienta] Creando generador de Word (apa7_word.py)...")
    
    # Este es el contenido que deberíamos haber creado antes
    word_script_content = '''#!/usr/bin/env python3
"""
Generador de documentos Word con formato APA 7ª edición
Uso: python apa7_word.py <ruta_materia> <nombre_trabajo> "<titulo_del_trabajo>"
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
    print("Error: Se requiere python-docx. Instálalo con: pip install python-docx")
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
    print("\\nPróximos pasos:")
    print("1. Abre el documento en Microsoft Word o LibreOffice")
    print("2. Revisa y edita el contenido según necesites")
    print("3. Verifica que las referencias sigan exactamente el formato APA 7")
    print("4. Guarda una copia en tu unidad de almacenamiento universitaria")

if __name__ == "__main__":
    main()
'''
    
    try:
        word_script_path.write_text(word_script_content, encoding="utf-8")
        print("[OK] Generador de Word creado exitosamente.")
        return True
    except Exception as e:
        print(f"[ERROR] Error al crear el generador de Word: {e}")
        return False

def main():
    """Función principal del menú."""
    while True:
        clear_screen()
        print_header()
        print_menu()
        
        choice = input("Seleccione una opcion (1-5): ").strip()
        
        if choice == "1":
            crear_materia()
        elif choice == "2":
            importar_libro()
        elif choice == "3":
            generar_word()
        elif choice == "4":
            ver_materias()
        elif choice == "5":
            print("\n[Despedida] Hasta luego! Que tengas un excelente estudio.")
            break
        else:
            print("[ERROR] Opcion no valida. Por favor seleccione 1, 2, 3, 4 o 5.")
            input("\nPresione Enter para continuar...")

if __name__ == "__main__":
    # Asegurarnos de que el directorio base existe
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    main()