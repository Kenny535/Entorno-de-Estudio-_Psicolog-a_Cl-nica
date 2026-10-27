#!/usr/bin/env python3
"""Fix the orphaned closing parentheses and double triple quotes - targeted"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# Find and fix the problematic section
# The issue is lines 359-366 have double triple quotes and orphaned )
# Let's find and replace the exact pattern

old_block = '''---
*Generado con asistencia de IA. Revisa y adapta el contenido según tus necesidades y el material específico que hayas trabajado en la materia.*
"""
"""
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return f"✅ **Asistente de escritura activado**\\n\\n{result.stdout}"
        else:
            return fallback_escritura(tema, tipo_trabajo, materia_nombre)


def generar_powerpoint_imagenes_agente(materia_nombre, trabajo_name, titulo):'''

new_block = '''---
*Generado con asistencia de IA. Revisa y adapta el contenido según tus necesidades y el material específico que hayas trabajado en la materia.*
"""

        try:
            result = subprocess.run(
                ["python", "-c", f"""
import sys
sys.path.insert(0, r'{SCRIPTS_DIR}')
from subagent import subagent
result = subagent(
    description="Asistente escritura academica",
    prompt=\"""{prompt}\"\"\"
)
print(result)
"""],
                capture_output=True,
                text=True,
                cwd=str(SCRIPTS_DIR)
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return f"✅ **Asistente de escritura activado**\\n\\n{result.stdout}"
            else:
                return fallback_escritura(tema, tipo_trabajo, materia_nombre)
                
        except Exception as e:
            return fallback_escritura(tema, tipo_trabajo, materia_nombre)


def generar_powerpoint_imagenes_agente(materia_nombre, trabajo_name, titulo):'''

if old_block in content:
    content = content.replace(old_block, new_block)
    path.write_text(content, encoding='utf-8')
    print('✅ Fixed successfully')
else:
    print('❌ Pattern not found, trying alternative...')
    # Try with the raw bytes
    print(repr(content[content.find("Generado con asistencia"):content.find("def generar_powerpoint_imagenes_agente")][:500]))