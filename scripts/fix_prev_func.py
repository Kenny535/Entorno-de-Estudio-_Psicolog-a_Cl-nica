#!/usr/bin/env python3
"""Fix the previous function syntax errors"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# Fix the orphaned closing parentheses and double triple quotes
content = content.replace(
'''*
*Generado con asistencia de IA. Revisa y adapta el contenido seg\xfan tus necesidades y el material espec\xedfico que hayas trabajado en la materia.*
"""
"""
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return f"\xe2\x9c\x85 **Asistente de escritura activado**\\\\n\\\\n{result.stdout}"
        else:
            return fallback_escritura(tema, tipo_trabajo, materia_nombre)''',
'''*
*Generado con asistencia de IA. Revisa y adapta el contenido seg\xfan tus necesidades y el material espec\xedfico que hayas trabajado en la materia.*
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
                return f"\xe2\x9c\x85 **Asistente de escritura activado**\\n\\n{result.stdout}"
            else:
                return fallback_escritura(tema, tipo_trabajo, materia_nombre)
                
        except Exception as e:
            return fallback_escritura(tema, tipo_trabajo, materia_nombre)'''
)

path.write_text(content, encoding='utf-8')
print('✅ Fixed previous function')