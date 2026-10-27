#!/usr/bin/env python3
"""Check menu routing"""
import re

with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

menu_matches = re.findall(r'elif opcion == "([^"]+)":', content)
print('Menu options in routing:')
for m in menu_matches:
    print(f'  - {m}')

# Check if new options are there
new_options = [
    '🤖 Analizar EPUB con IA',
    '✍️ Asistente de Escritura',
    '📊 Generar PowerPoint con Imágenes Reales'
]

for opt in new_options:
    if opt in content:
        print(f'✅ Found: {opt}')
    else:
        print(f'❌ Missing: {opt}')