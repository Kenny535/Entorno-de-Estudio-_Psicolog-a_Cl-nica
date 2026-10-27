#!/usr/bin/env python3
"""Check actual line 344"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
# Check around line 344
for i in range(330, 360):
    if i < len(lines):
        print(f'{i+1}: {lines[i]}')