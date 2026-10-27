#!/usr/bin/env python3
"""Search for prompt in asistente function"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find asistente function
start = content.find('def asistente_escritura_agente(tema, tipo_trabajo, materia_nombre):')
if start != -1:
    # Search for "prompt" in the function
    func_end = content.find('\ndef ', start + 1)
    if func_end == -1:
        func_end = len(content)
    
    func_content = content[start:func_end]
    # Find prompt assignment
    import re
    for m in re.finditer(r'prompt\s*=', func_content):
        idx = start + m.start()
        print(f'Found prompt at {idx}')
        print(content[idx:idx+100])
        print('---')