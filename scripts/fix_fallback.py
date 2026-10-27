#!/usr/bin/env python3
"""Fix the fallback function indentation"""
import pathlib

path = pathlib.Path(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py')
content = path.read_text(encoding='utf-8')

# The problem is after the fallback_escritura function - it has extra try block
# Let's find the fallback_escritura function and fix its return statement
# The fallback function should end with the return statement, not have a try block after

# Find the fallback function start
fallback_start = content.find('def fallback_escritura(tema, tipo_trabajo, materia_nombre):')
if fallback_start == -1:
    print('❌ fallback_escritura not found')
    exit(1)

# Find the next function after fallback
next_func = content.find('\ndef generar_powerpoint_imagenes_agente', fallback_start)
if next_func == -1:
    print('❌ next function not found')
    exit(1)

print(f'fallback at {fallback_start}, next at {next_func}')

# Get the content between them
fallback_content = content[fallback_start:next_func]
print('Current fallback content (last 500 chars):')
print(repr(fallback_content[-500:]))

# The fallback should just return the string - let's see what the correct version should be
# The issue is the old content has a try block after the return string
# We need to remove that try block

# Find the return statement in fallback
return_idx = fallback_content.rfind('return f"""')
if return_idx == -1:
    return_idx = fallback_content.rfind('return """')
if return_idx == -1:
    print('❌ return not found')
    exit(1)

# Find the end of the return string (the closing triple quotes)
end_return = fallback_content.find('"""', return_idx + 10)
if end_return == -1:
    print('❌ end return not found')
    exit(1)

end_return += 3  # include the quotes
print(f'Return from {return_idx} to {end_return}')

# Everything after the return string until the next function should be removed
# Let's just reconstruct the fallback function properly
new_fallback = '''def fallback_escritura(tema, tipo_trabajo, materia_nombre):
    """Genera una estructura básica de trabajo si el agente falla"""
    return f"""## ✅ Estructura Básica Generada

**Tema:** {tema}
**Tipo:** {tipo_trabajo}
**Materia:** {materia_nombre}

### 📄 Portada
- Título: Tu título aquí
- Nombre: Tu nombre
- Curso: {materia_nombre}
- Universidad: Universidad Autónoma
- Profesor: Tu profesor
- Fecha: {__import__('datetime').datetime.now().strftime("%B %d, %Y")}

### 📚 Índice
1. Introducción
2. Desarrollo
3. Conclusión
4. Referencias

### ✍️ Introducción (estructura)
"El tema {tema} es fundamental en el campo de la psicologia clinica porque..."

### 📝 Desarrollo (puntos clave)
- **Punto 1:** Concepto principal del material de estudio
- **Punto 2:** Aplicación práctica
- **Punto 3:** Hallazgos relevantes

### 🎯 Conclusión (estructura)
"En resumen, el trabajo aborda los aspectos más importantes de {tema} y sus implicaciones en la práctica clinica."

### 📖 Referencias (formato APA básico)
- Autor. (Año). *Título de la obra*. Editorial.

---

*Generado con asistencia de IA. Revisa y adapta el contenido según tus necesidades y el material específico que hayas trabajado en la materia.*
"""

'''

content = content[:fallback_start] + new_fallback + content[next_func:]
path.write_text(content, encoding='utf-8')
print('✅ Fixed fallback function')