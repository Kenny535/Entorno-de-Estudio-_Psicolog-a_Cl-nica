#!/usr/bin/env python3
"""Find the actual prompt string"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find asistente function
start = content.find('def asistente_escritura_agente(tema, tipo_trabajo, materia_nombre):')
if start != -1:
    # Search backwards from the prompt=prompt line for the actual f-string
    prompt_line = content.find('prompt=prompt', start)
    if prompt_line != -1:
        # Look backwards for the f""" or """
        search_start = max(0, prompt_line - 5000)
        before = content[search_start:prompt_line]
        
        # Find the last f""" or """
        last_f = before.rfind('f"""')
        last_quote = before.rfind('"""')
        
        print(f'Last f""" at relative pos: {last_f}')
        print(f'Last """ at relative pos: {last_quote}')
        
        if last_f != -1:
            abs_pos = search_start + last_f
            print(f'Absolute pos: {abs_pos}')
            print(content[abs_pos:abs_pos+200])
            print('---')
        
        if last_quote != -1:
            abs_pos = search_start + last_quote
            print(f'Absolute pos: {abs_pos}')
            print(content[abs_pos:abs_pos+200])