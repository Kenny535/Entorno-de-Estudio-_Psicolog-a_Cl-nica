#!/usr/bin/env python3
"""Fix the escaped quotes in subprocess"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the escaped quotes issue
# Find the problematic line
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'prompt=\\"\\"\\"{prompt}\\"\\"\\"' in line:
        print(f'Found at line {i+1}: {line}')
        # Fix it - use a different approach
        lines[i] = line.replace('prompt=\\"\\"\\"{prompt}\\"\\"\\"', 'prompt=prompt')
        print(f'Fixed to: {lines[i]}')
        break

content = '\n'.join(lines)

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