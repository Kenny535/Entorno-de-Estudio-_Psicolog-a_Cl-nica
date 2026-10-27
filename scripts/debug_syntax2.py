#!/usr/bin/env python3
"""Debug more context"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
for i, line in enumerate(lines):
    if i >= 380 and i <= 460:
        print(f'{i+1}: {line}')