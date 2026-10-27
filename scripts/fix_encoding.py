#!/usr/bin/env python3
"""Fix all docstring encoding issues in streamlit_app.py"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# Replace all accented characters in docstrings with ASCII equivalents
replacements = {
    'imágenes': 'imagenes',
    'Imágenes': 'Imagenes',
    'DISEÑO': 'DISENO',
    'DIALECTO': 'DIALECTO',
    'DIALECTIVA': 'DIALECTIVA',
    'CRÍTICOS': 'CRITICOS',
    'ANÁLISIS': 'ANALISIS',
    'PRÁCTICA': 'PRACTICA',
    'ACADÉMICO': 'ACADEMICO',
    'PRESENTACIÓN': 'PRESENTACION',
    'UNIVERSIDAD': 'UNIVERSIDAD',
    'psicología': 'psicologia',
    'clínica': 'clinica',
    'generación': 'generacion',
    'estudiante': 'estudiante',
    'EJEMPLOS': 'EJEMPLOS',
    'EJEMPLO': 'EJEMPLO',
    'CONCEPTO': 'CONCEPTO',
    'ESPECÍFICOS': 'ESPECIFICOS',
    'MÁXIMO': 'MAXIMO',
    'ANASTASIOS': 'ANASTASIOS',
}

for old, new in replacements.items():
    content = content.replace(old, new)

path.write_text(content, encoding='utf-8')
print('✅ Fixed encoding issues')