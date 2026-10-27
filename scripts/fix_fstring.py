#!/usr/bin/env python3
"""Fix the f-string issue - need to escape parentheses or use different approach"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The issue is in an f-string - parentheses inside can cause issues
# Let me replace the whole problematic line
content = content.replace(
    '[Lista en orden alfabético con sangría francesa (1,27 cm). Formatos APA 7ma:]',
    '[Lista en orden alfabético con sangría francesa (1.27 cm). Formatos APA 7ma:]'
)

# Actually, the issue might be that the f-string is being interpreted
# Let me check if there's an f-string that contains this
# Better: replace the entire fallback function's return to not use f-string for that part

# Let's just verify the full syntax by running Python's compiler directly
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