#!/usr/bin/env python3
"""Fix the triple quotes in subprocess"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the problematic subprocess call in asistente function
# The issue is: prompt=\"\"\"{prompt}\"\"\"  - triple quotes collide
# We need to use a different approach - pass the prompt differently

# Let me find and replace the subprocess call
old_subprocess = '''prompt=\"\"\"{prompt}\"\"\"
)
print(result)
"""],'''

new_subprocess = '''prompt=prompt
)
print(result)
"""],'''

content = content.replace(old_subprocess, new_subprocess)

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