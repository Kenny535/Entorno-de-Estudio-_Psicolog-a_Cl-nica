#!/usr/bin/env python3
"""
Conversor automático de EPUB a Markdown para todas las materias.
Busca archivos .epub en carpetas de materias, los convierte con pandoc
y guarda los resultados en la carpeta "salidas" de cada materia.

Uso: python convertir_epub_automatico.py [--overwrite|-o]
     --overwrite / -o: Forzar sobrescribir archivos MD existentes
"""
import sys
import subprocess
import pathlib
import os
import argparse

sys.path.insert(0, pathlib.Path(__file__).parent)
from config import BASE_DIR, MATERIAS_DIR, SALIDAS_DIR, ensure_dirs, list_materias

def main():
    ensure_dirs()
    
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(
        description="Conversor automático EPUB → Markdown para materias universitarias"
    )
    parser.add_argument(
        "--overwrite", "-o",
        action="store_true",
        help="Forzar sobrescribir archivos Markdown existentes"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("📚 Conversor Automático EPUB → Markdown")
    print("=" * 60)
    
    # Listar todas las materias
    materias = list_materias()
    
    if not materias:
        print("[ERROR] No se encontraron materias. Verifica la carpeta.")
        print("Ruta esperada:", MATERIAS_DIR)
        sys.exit(1)
    
    print(f"\n📁 Se encontraron {len(materias)} materia(s):")
    for m in materias:
        print(f"  - {m}")
    
    total_convertidos = 0
    total_errores = 0
    total_saltados = 0
    
    for materia_name in materias:
        print(f"\n{'─' * 50}")
        print(f"🔍 Procesando materia: {materia_name}")
        print(f"{'─' * 50}")
        
        # Rutas de la materia
        materia_dir = MATERIAS_DIR / materia_name
        salidas_dir = SALIDAS_DIR / materia_name
        
        # Asegurar que existe la carpeta salidas
        salidas_dir.mkdir(parents=True, exist_ok=True)
        
        # Buscar archivos EPUB en la carpeta de la materia
        epub_files = list(materia_dir.glob("*.epub"))
        
        if not epub_files:
            print(f"  ℹ️ No se encontraron archivos .epub en {materia_dir}")
            continue
        
        print(f"  📖 Found {len(epub_files)} archivo(s) .epub")
        
        for epub_path in epub_files:
            print(f"\n  🔄 Convirtiendo: {epub_path.name}")
            
            # Nombre base para el archivo MD (sin extensión)
            md_filename = epub_path.stem + ".md"
            md_path = salidas_dir / md_filename
            
            # Verificar si ya existe
            if md_path.exists() and not args.overwrite:
                print(f"  ⚠️  El archivo {md_filename} ya existe en salidas/")
                print(f"  ⏭️  Saltando (usa --overwrite para forzar sobrescritura)")
                total_saltados += 1
                continue
            
            # Ejecutar pandoc para convertir EPUB a Markdown
            print(f"  ⚙️  Ejecutando: pandoc '{epub_path}' -o '{md_path}'")
            
            try:
                result = subprocess.run(
                    ["pandoc", str(epub_path), "-o", str(md_path)],
                    capture_output=True,
                    text=True,
                    cwd=str(materia_dir)
                )
                
                if result.returncode == 0:
                    file_size = md_path.stat().st_size
                    print(f"  ✅ Convertido exitosamente!")
                    print(f"     📄 Archivo: {md_filename}")
                    print(f"     💾 Tamaño: {file_size:,} bytes")
                    total_convertidos += 1
                else:
                    print(f"  ❌ Error en pandoc:")
                    print(f"     {result.stderr[:200]}")  # Mostrar primeros 200 chars
                    total_errores += 1
                    
            except Exception as e:
                print(f"  ❌ Error inesperado: {e}")
                total_errores += 1
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN FINAL")
    print("=" * 60)
    print(f"📚 Materias procesadas: {len(materias)}")
    print(f"✅ Archivos convertidos: {total_convertidos}")
    print(f"❌ Errores: {total_errores}")
    print(f"⏭️  Archivos saltados (existían): {total_saltados}")
    print(f"📁 Archivos guardados en: {SALIDAS_DIR}")
    
    # Listar qué se generó
    print(f"\n📁 Archivos generados en las carpetas salidas:")
    for materia_name in materias:
        md_files = list((SALIDAS_DIR / materia_name).glob("*.md"))
        if md_files:
            print(f"  • {materia_name}: {len(md_files)} archivo(s) MD")
            for f in md_files:
                print(f"    - {f.name}")
    
    print("\n" + "=" * 60)
    print("¡Proceso completado!")
    print("=" * 60)

if __name__ == "__main__":
    main()