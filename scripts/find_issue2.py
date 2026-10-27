#!/usr/bin/env python3
"""Find all decimal in braces"""
import re

with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Search for any decimal in braces
for m in re.finditer(r'\{[\d.]+', content):
    print(f'Found at {m.start()}: {m.group()}')
    print(f'Context: {content[max(0,m.start()-50):m.start()+100]}')
    print('---')

# Also check for (1.27) patterns that might be problematic
for m in re.finditer(r'\(1\.27', content):
    print(f'Found (1.27 at {m.start()}:')
    print(f'Context: {content[max(0,m.start()-50):m.start()+100]}')
    print('---')