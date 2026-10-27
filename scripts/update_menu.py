#!/usr/bin/env python3
"""Actualiza el menú de Streamlit con las nuevas opciones de agentes"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

old = '        "📈 Ver materias existentes",'
new = '''        "🤖 Analizar EPUB con IA",
        "✍️ Asistente de Escritura",
        "📊 Generar PowerPoint con Imágenes Reales",
        "📈 Ver materias existentes",'''

content = content.replace(old, new, 1)
path.write_text(content, encoding='utf-8')
print('✅ Menú actualizado correctamente')