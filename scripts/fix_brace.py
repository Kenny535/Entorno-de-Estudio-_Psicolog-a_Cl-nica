#!/usr/bin/env python3
"""Fix the extra brace"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the extra brace
content = content.replace(
    '**{__import__(\'datetime\').datetime.now().strftime("%B %Y")}}',
    '**{__import__(\'datetime\').datetime.now().strftime("%B %Y")}'
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