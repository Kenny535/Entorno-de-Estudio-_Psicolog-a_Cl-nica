#!/usr/bin/env python3
"""Check full asistente function"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find asistente function
start = content.find('def asistente_escritura_agente(tema, tipo_trabajo, materia_nombre):')
if start != -1:
    # Find next function
    next_func = content.find('\ndef ', start + 1)
    if next_func == -1:
        next_func = len(content)
    
    func = content[start:next_func]
    print(func[:3000])
    print('=== END OF PRINT ===')