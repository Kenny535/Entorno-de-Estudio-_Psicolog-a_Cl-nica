#!/usr/bin/env python3
"""Check Asistente routing"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Check for Asistente de Escritura routing
if 'elif opcion == "✍️ Asistente de Escritura":' in content:
    print('✅ Asistente de Escritura routing found')
else:
    print('❌ Asistente de Escritura routing NOT found')
    
# Also check the menu sidebar
if '✍️ Asistente de Escritura' in content:
    print('✅ Asistente de Escritura in menu')
else:
    print('❌ Asistente de Escritura NOT in menu')