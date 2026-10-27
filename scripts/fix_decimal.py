#!/usr/bin/env python3
"""Fix the decimal literal issue"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the (1.27 cm) issue - it's in an f-string and Python is trying to parse it
content = content.replace(
    'sangría francesa (1.27 cm)',
    'sangría francesa (1,27 cm)'
)

with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify syntax
import ast
try:
    ast.parse(content)
    print('✅ Sintaxis correcta')
except SyntaxError as e:
    print(f'❌ Error en línea {e.lineno}: {e.msg}')
    lines = content.split('\n')
    if e.lineno and e.lineno <= len(lines):
        for i in range(max(0, e.lineno-5), min(len(lines), e.lineno+5)):
            print(f'{i+1}: {lines[i]}')