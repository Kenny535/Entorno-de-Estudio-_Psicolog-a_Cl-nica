#!/usr/bin/env python3
"""Verify all is working"""
import ast
import re

with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check syntax
try:
    ast.parse(content)
    print('✅ Sintaxis correcta')
except SyntaxError as e:
    print(f'❌ Error en línea {e.lineno}: {e.msg}')
    lines = content.split('\n')
    if e.lineno and e.lineno <= len(lines):
        print(f'   Código: {lines[e.lineno-1]}')

# Verify all menu options
menu_matches = re.findall(r'elif opcion == "([^"]+)":', content)
print('\nAll menu options in routing:')
for m in menu_matches:
    print(f'  - {m}')

# Check specific new options
new_options = [
    '🤖 Analizar EPUB con IA',
    '✍️ Asistente de Escritura',
    '📊 Generar PowerPoint con Imagenes Reales'
]

for opt in new_options:
    if opt in content:
        print(f'✅ Found: {opt}')
    else:
        print(f'❌ Missing: {opt}')