#!/usr/bin/env python3
"""Check asistente function prompt"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find asistente function
start = content.find('def asistente_escritura_agente(tema, tipo_trabajo, materia_nombre):')
if start != -1:
    # Find the prompt
    prompt_start = content.find('prompt = f"""', start)
    if prompt_start == -1:
        prompt_start = content.find('prompt = """', start)
    if prompt_start != -1:
        print(f'Prompt starts at {prompt_start}')
        # Find end of prompt
        prompt_end = content.find('"""', prompt_start + 10)
        if prompt_end != -1:
            print(f'Prompt ends at {prompt_end}')
            prompt = content[prompt_start:prompt_end+3]
            print(f'Prompt length: {len(prompt)}')
            # Check for unmatched braces in prompt
            open_braces = prompt.count('{')
            close_braces = prompt.count('}')
            print(f'Open braces: {open_braces}, Close braces: {close_braces}')
            # Check for {1.27 or similar
            import re
            for m in re.finditer(r'\{[\d.]', prompt):
                print(f'Found digit brace at {m.start()}: {prompt[max(0,m.start()-20):m.start()+30]}')
        else:
            print('Prompt end not found!')
    else:
        print('Prompt not found')
else:
    print('Function not found')