#!/usr/bin/env python3
"""
Crea un nuevo entorno de materia en C:\\Universidad\\estudio-psicologia\\materias\\
Uso: python init_materia.py "Nombre de la Materia"
"""
import sys
import pathlib

# Importar configuracion
sys.path.insert(0, pathlib.Path(__file__).parent)
from config import get_materia_dir, ensure_dirs

def main():
    ensure_dirs()

    if len(sys.argv) < 2:
        print("Uso: python init_materia.py \"Nombre de la Materia\"")
        sys.exit(1)

    materia_name = sys.argv[1].strip()
    if not materia_name:
        print("Error: El nombre de la materia no puede estar vacio.")
        sys.exit(1)

    materia_dir = get_materia_dir(materia_name)
    if materia_dir.exists():
        print(f"La materia '{materia_name}' ya existe en: {materia_dir}")
        return

    materia_dir.mkdir(parents=True, exist_ok=True)
    (materia_dir / "salidas").mkdir(exist_ok=True)

    files_to_create = {
        "guia_aprendizaje.md": (
            "# Guia de Aprendizaje\n\n"
            "*Coloca aqui la guia de aprendizaje proporcionada por el facilitador.*\n\n"
            "## Contenido\n\n"
            "- [Ingresar objetivos, referencias y autores del syllabus]\n"
        ),
        "libro_principal.md": (
            "# Libro Principal\n\n"
            "*Si el facilitador proporciona un libro en PDF, conviertelo a Markdown y colocalo aqui.*\n\n"
            "## Instrucciones\n\n"
            "1. Convierte el PDF a Markdown usando pandoc:\n"
            "   ```bash\n"
            "   pandoc libro.pdf -o libro_principal.md\n"
            "   ```\n"
            "2. Reemplaza este archivo con el resultado.\n"
            "3. La IA priorizara este libro para responder preguntas."
        ),
        "memory.md": (
            "# Memoria de la Materia\n\n"
            "*Aqui se guarda el historial de conversaciones y hallazgos de esta materia.*\n\n"
            "## Sesiones\n\n"
        ),
        "fuentes_usadas.md": (
            "# Fuentes Usadas\n\n"
            "*Lista de fuentes verificadas citadas en esta materia.*\n\n"
            "## Fuentes\n\n"
        ),
    }

    for file_name, content in files_to_create.items():
        file_path = materia_dir / file_name
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")

    print(f"[OK] Entorno de materia creado exitosamente:")
    print(f"   [Carpeta] {materia_dir}")
    print(f"\n   Archivos generados:")
    for file_name in files_to_create:
        print(f"     - {file_name}")
    print(f"     - salidas/ (directorio)")
    print(f"\n   Proximos pasos:")
    print(f"     1. Edita guia_aprendizaje.md con la guia del facilitador")
    print(f"     2. Convierte el PDF a Markdown y guardalo como libro_principal.md")
    print(f"     3. Empieza a estudiar!")

if __name__ == "__main__":
    main()