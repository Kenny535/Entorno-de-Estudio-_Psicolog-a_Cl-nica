#!/usr/bin/env python3
"""Fix using exact string from file"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# Find the exact text
start_idx = content.find('Generado con asistencia de IA. Revisa y adapta el contenido según tus necesidades y el material específico que hayas trabajado en la materia.')
if start_idx == -1:
    print('❌ Start not found')
    exit(1)

end_idx = content.find('def generar_powerpoint_imagenes_agente', start_idx)
if end_idx == -1:
    print('❌ End not found')
    exit(1)

print(f'Found at {start_idx} to {end_idx}')
print('Content to replace:')
print(repr(content[start_idx:end_idx]))

# Now replace exactly
old = content[start_idx:end_idx]
new = '''Generado con asistencia de IA. Revisa y adapta el contenido según tus necesidades y el material específico que hayas trabajado en la materia.*
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

content = content[:start_idx] + new + content[end_idx:]
path.write_text(content, encoding='utf-8')
print('✅ Replaced successfully')