#!/usr/bin/env python3
"""Fix the syntax error in the prompt string"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# The issue is on line 452 with prompt="""{prompt}"""
# We need to escape this properly or use a different approach

# Find the problematic line
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'prompt="""{prompt}"""' in line and i > 400:
        print(f'Found at line {i+1}: {repr(line)}')
        # Fix it - use escaped quotes
        lines[i] = line.replace('prompt="""{prompt}"""', 'prompt=\\"\\"\\"{prompt}\\"\\"\\"')
        print(f'Fixed to: {repr(lines[i])}')
        break

content = '\n'.join(lines)
path.write_text(content, encoding='utf-8')
print('✅ Fixed prompt string')

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