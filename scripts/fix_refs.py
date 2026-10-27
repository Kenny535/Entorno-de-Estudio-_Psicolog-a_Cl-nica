#!/usr/bin/env python3
"""Fix the PowerPoint references syntax error"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# Fix the problematic reference lines
old = '''        ref_slide.Shapes.Title.TextFrame.TextRange.Text = "Referencias"
        ref_slide.Shapes.Placeholders(2).TextFrame.TextRange.Text = """American Psychological Association. (2020). *Publication manual of the American Psychological Association* (7th ed.). https://doi.org/10.1037/0000165-000
Smith, J. A., & Jones, L. M. (2019). Efectos de la terapia cognitivo-conductual en trastornos de ansiedad. *Journal of Clinical Psychology*, 75(3), 456-467. https://doi.org/10.1002/jclp.22745"""'''

new = '''        ref_slide.Shapes.Title.TextFrame.TextRange.Text = "Referencias"
        ref_text = "American Psychological Association. (2020). Publication manual of the American Psychological Association (7th ed.). https://doi.org/10.1037/0000165-000\\nSmith, J. A., & Jones, L. M. (2019). Efectos de la terapia cognitivo-conductual en trastornos de ansiedad. Journal of Clinical Psychology, 75(3), 456-467. https://doi.org/10.1002/jclp.22745"
        ref_slide.Shapes.Placeholders(2).TextFrame.TextRange.Text = ref_text'''

content = content.replace(old, new)
path.write_text(content, encoding='utf-8')
print('✅ Fixed references syntax')