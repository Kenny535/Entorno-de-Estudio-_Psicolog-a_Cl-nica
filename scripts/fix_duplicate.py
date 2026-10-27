#!/usr/bin/env python3
"""Fix duplicate function"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# Find duplicate
first = content.find('def generar_powerpoint_imagenes_agente(materia_nombre, trabajo_name, titulo):')
second = content.find('def generar_powerpoint_imagenes_agente(materia_nombre, trabajo_name, titulo):', first + 1)

if second != -1:
    print(f'Found duplicate at {first} and {second}')
    # Remove the second occurrence
    # Find the next function after the second one
    next_func = content.find('\ndef ', second + 1)
    if next_func == -1:
        # Find end of file marker
        next_func = content.find('\nif __name__', second + 1)
    if next_func == -1:
        next_func = len(content)
    
    content = content[:second] + content[next_func:]
    path.write_text(content, encoding='utf-8')
    print('✅ Removed duplicate')
else:
    print('❌ No duplicate found')

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