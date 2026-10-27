#!/usr/bin/env python3
"""
Convierte/importa un PDF o EPUB del libro del facilitador a la materia correspondiente.
Uso: python convert_pdf_md.py "ruta/al/archivo.(pdf|epub)" "Nombre de la Materia"
Nota: Este script copia el archivo y prepara un placeholder para Markdown.
Para conversion real usar pandoc: pandoc archivo.(pdf|epub) -o archivo.md
"""
import sys
import shutil
import pathlib

sys.path.insert(0, pathlib.Path(__file__).parent)
from config import get_materia_dir, ensure_dirs, list_materias

def main():
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Uso: python convert_pdf_md.py \"ruta/al/archivo.(pdf|epub)\" [Nombre de la Materia]")
        sys.exit(1)

    file_path = pathlib.Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: El archivo {file_path} no existe.")
        sys.exit(1)

    # Validar extensión
    extension = file_path.suffix.lower()
    if extension not in ['.pdf', '.epub']:
        print(f"Error: Solo se permiten archivos .pdf o .epub. Recibido: {extension}")
        sys.exit(1)

    # Determinar nombre de la materia
    materia_name = None
    if len(sys.argv) >= 3:
        materia_name = sys.argv[2]
    else:
        # Intentar inferir desde el directorio actual
        cwd = pathlib.Path.cwd()
        if "materias" in cwd.parts:
            idx = cwd.parts.index("materias")
            if idx + 1 < len(cwd.parts):
                materia_name = cwd.parts[idx + 1]

    if not materia_name:
        # Listar materias existentes y preguntar
        materias = list_materias()
        if materias:
            print("Materias existentes:")
            for i, m in enumerate(materias, 1):
                print(f"  {i}. {m}")
            choice = input("Selecciona numero o escribe nombre de la materia: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(materias):
                materia_name = materias[int(choice)-1]
            else:
                materia_name = choice
        else:
            materia_name = input("Nombre de la materia: ").strip()

    if not materia_name:
        print("Error: Se necesita un nombre de materia.")
        sys.exit(1)

    materia_dir = get_materia_dir(materia_name)
    materia_dir.mkdir(parents=True, exist_ok=True)

    # Copiar archivo (PDF o EPUB)
    dest_file = materia_dir / file_path.name
    try:
        shutil.copy2(file_path, dest_file)
        print(f"[OK] Archivo copiado a: {dest_file}")
    except Exception as e:
        print(f"Error copiando archivo: {e}")
        sys.exit(1)

    # Crear placeholder de libro_principal.md si no existe
    md_path = materia_dir / "libro_principal.md"
    if not md_path.exists():
        file_type = "PDF" if extension == '.pdf' else "EPUB"
        placeholder = (
            f"# Libro Principal\n\n"
            f"*Archivo {file_type} original: {file_path.name}*\n\n"
            "## Instrucciones\n\n"
            "1. **Instala pandoc** (si no lo tienes): `winget install pandoc` o https://pandoc.org\n"
            f"2. Convierte el {file_type.lower()} a Markdown:\n"
            f"   ```bash\n"
            f"   pandoc \"{dest_file.name}\" -o libro_principal.md\n"
            f"   ```\n"
            "3. Esto genera el archivo en la misma carpeta.\n"
            "4. La IA usara este archivo como referencia principal.\n\n"
            "## Notas importantes\n\n"
            "- El archivo original se conserva como copia de respaldo.\n"
            "- El archivo Markdown consume menos recursos y es mas rapido de procesar.\n"
            "- Manten siempre actualizado este archivo con el contenido del libro.\n"
            "- Para EPUB: pandoc preserva mejor la estructura que con PDFs complejos.\n"
        )
        md_path.write_text(placeholder, encoding="utf-8")
        print(f"[OK] Placeholder creado: {md_path}")

    print("\nProximos pasos:")
    print(f"1. Ve a la carpeta de la materia: {materia_dir}")
    file_type_name = "PDF" if extension == '.pdf' else "EPUB"
    print(f"2. Convierte el {file_type_name} a Markdown con pandoc:")
    print(f"   pandoc \"{dest_file.name}\" -o libro_principal.md")
    print(f"3. Reemplaza el contenido del placeholder con el resultado.")
    print(f"4. La IA ahora usara principalmente ese libro para responder preguntas!")

if __name__ == "__main__":
    main()