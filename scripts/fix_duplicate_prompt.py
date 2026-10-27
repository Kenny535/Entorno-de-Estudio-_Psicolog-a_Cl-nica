#!/usr/bin/env python3
"""Fix the duplicate prompt issue"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The problem: there are now TWO prompts in asistente_escritura_agente
# My new prompt (lines ~381-424) and the old one (lines 425-450)
# Need to remove the old prompt and keep the structure correct

# Find the old prompt that starts at line 425 (now around there)
old_prompt_start = content.find('"""Eres un asistente académico experto en normas APA 7ma edición y psicologia clinica. Ayuda a un estudiante a redactar un trabajo académico.')
if old_prompt_start == -1:
    print('❌ Old prompt not found')
    exit(1)

# Find the end of that old prompt (the closing triple quotes before "try:")
old_prompt_end = content.find('"""\n    \n    try:', old_prompt_start)
if old_prompt_end == -1:
    old_prompt_end = content.find('"""\n\n    try:', old_prompt_start)
if old_prompt_end == -1:
    # Try to find just the closing quotes
    old_prompt_end = content.find('"""', old_prompt_start + 100)
    if old_prompt_end != -1:
        old_prompt_end += 3

print(f'Old prompt at {old_prompt_start} to {old_prompt_end}')

# Also need to find the "prompt = " assignment for the old one
# It should be right before the old prompt
assignment_start = content.rfind('prompt = ', 0, old_prompt_start)
if assignment_start != -1:
    print(f'Prompt assignment at {assignment_start}')
    # Remove from assignment_start to old_prompt_end
    content = content[:assignment_start] + content[old_prompt_end:]
    print('✅ Removed old prompt')
else:
    print('❌ Assignment not found')

# Save
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