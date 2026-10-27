#!/usr/bin/env python3
"""Find the exact issue"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the fallback function return
fallback_start = content.find('def fallback_escritura(tema, tipo_trabajo, materia_nombre):')
if fallback_start != -1:
    return_idx = content.find('return f"""', fallback_start)
    if return_idx != -1:
        end_return = content.find('"""', return_idx + 10)
        if end_return != -1:
            # Print the return statement
            return_stmt = content[return_idx:end_return+3]
            print('=== RETURN STATEMENT ===')
            print(return_stmt[:500])
            print('...')
            print(return_stmt[-500:])

# The issue might be that there's a {1.27} somewhere that's being interpreted
# Let me search for {1.27
idx = content.find('{1.27')
if idx != -1:
    print(f'\nFound {{1.27 at {idx}:')
    print(content[max(0,idx-50):idx+50])

# Search for any decimal in braces
import re
for m in re.finditer(r'\{[\d.]+', content):
    print(f'\nFound decimal in braces at {m.start()}: {m.group()}')
    print(f'Context: {content[max(0,m.start()-30):m.start()+50]}')