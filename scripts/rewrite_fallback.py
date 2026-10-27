#!/usr/bin/env python3
"""Rewrite fallback function cleanly"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the fallback function
fallback_start = content.find('def fallback_escritura(tema, tipo_trabajo, materia_nombre):')
if fallback_start == -1:
    print('❌ Function not found')
    exit(1)

# Find the next function
next_func = content.find('\ndef ', fallback_start + 1)
if next_func == -1:
    next_func = len(content)

# Get the current fallback
current = content[fallback_start:next_func]
print('Current fallback:')
print(current[:200])
print('...')
print(current[-200:])

# Write new fallback function
new_fallback = '''def fallback_escritura(tema, tipo_trabajo, materia_nombre):
    """Genera una estructura basica de trabajo si el agente falla"""
    from datetime import datetime
    fecha = datetime.now().strftime("%B %Y")
    
    return f"""# {tema.upper()}

**Nombre del Autor**  
**Universidad**  
**{materia_nombre}**  
**Profesor: [Nombre del Profesor]**  
**{fecha}**

---

## Resumen

[Resumen de 150-250 palabras en bloque, sin sangria. Describe el objetivo, metodo, resultados principales y conclusiones del trabajo sobre {tema}.]

**Palabras clave:** {tema.lower()}, psicologia clinica, {tipo_trabajo.lower()}

---

## Introduccion

[Introduccion al tema {tema}. Presenta la importancia del tema en psicologia clinica, define terminos clave y establece el proposito del trabajo.]

### Desarrollo del Tema

[Desarrolla los puntos principales segun el tipo de trabajo ({tipo_trabajo}). Usa headings APA Nivel 2 y 3 segun sea necesario. Incluye citas en formato (Apellido, Ano) o Apellido (Ano).]

#### Concepto Clave 1

[Explicacion con referencias al material de estudio.]

#### Concepto Clave 2

[Explicacion con referencias al material de estudio.]

---

## Conclusion

[Sintesis de los puntos principales. Implicaciones para la practica clinica. Limitaciones y futuras lineas de investigacion.]

---

## Referencias

[Lista en orden alfabetico con sangria francesa (1.27 cm). Formatos APA 7ma:]

Apellido, A. A. (Ano). *Titulo del libro en cursiva*. Editorial. https://doi.org/xxxxx
Apellido, B. B., & Apellido, C. C. (Ano). Titulo del articulo. *Revista en Cursiva*, Volumen(Numero), pp-pp. https://doi.org/xxxxx
Organizacion. (Ano). *Titulo del informe en cursiva*. URL

---

*Generado siguiendo Guia Normas APA 7ma Edicion (normas-apa.org). Revisa y adapta citas y referencias a tu material especifico.*
"""

'''

content = content[:fallback_start] + new_fallback + content[next_func:]

with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Verify syntax
import ast
try:
    ast.parse(content)
    print('✅ Sintaxis correcta')
except SyntaxError as e:
    print(f'❌ Error en linea {e.lineno}: {e.msg}')
    lines = content.split('\n')
    if e.lineno and e.lineno <= len(lines):
        for i in range(max(0, e.lineno-5), min(len(lines), e.lineno+5)):
            print(f'{i+1}: {lines[i]}')