#!/usr/bin/env python3
"""Add Asistente de Escritura routing"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find where to insert - after "Analizar EPUB con IA" routing
idx = content.find('elif opcion == "🤖 Analizar EPUB con IA":')
if idx == -1:
    print('❌ Analizar EPUB routing not found')
    exit(1)

# Find the next elif after Analizar EPUB
next_elif = content.find('elif opcion ==', idx + 1)
if next_elif == -1:
    print('❌ Next elif not found')
    exit(1)

print(f'Found Analizar at {idx}, next at {next_elif}')

# The routing for Asistente should go between them
new_routing = '''elif opcion == "✍️ Asistente de Escritura":
    st.header("✍️ Asistente de Escritura")
    
    materias = list_materias()
    
    if not materias:
        st.warning("No hay materias creadas. Primero crea una materia.")
    else:
        # Formulario para configurar el trabajo
        with st.form("form_escritura"):
            col1, col2 = st.columns(2)
            
            with col1:
                materia_seleccionada = st.selectbox(
                    "Materia:",
                    materias,
                    key="escritura_materia"
                )
                
                tema = st.text_input(
                    "Tema del trabajo:",
                    placeholder="Ej: Terapia cognitivo-conductual",
                    help="Escribe el tema principal de tu trabajo académico"
                )
            
            with col2:
                tipo_trabajo = st.selectbox(
                    "Tipo de trabajo:",
                    ["Ensayo", "Trabajo de investigación", "Reflexión", "Análisis de caso", "Revisión teórica"],
                    key="tipo_trabajo"
                )
                
                trabajo_name = st.text_input(
                    "Nombre del archivo:",
                    value="trabajo",
                    help="Nombre para el archivo de trabajo"
                )
            
            st.info("""
            📝 **Asistente de Escritura Académica**
            Este agente te ayudará a estructurar tu trabajo académico siguiendo las normas APA 7ma edición.
            Usará el contenido de tu libro como base para generar referencias y citations.
            """)
            
            submitted = st.form_submit_button("✍️ Generar Estructura del Trabajo", type="primary")
            
            if submitted:
                if not tema:
                    st.error("El tema es obligatorio.")
                else:
                    with st.spinner("Generando estructura del trabajo académico..."):
                        try:
                            resultado = asistente_escritura_agente(tema, tipo_trabajo, materia_seleccionada)
                            
                            if resultado.startswith("✅"):
                                st.success("✅ Estructura generada!")
                                st.markdown(resultado)
                                
                                # Guardar en archivo para uso posterior
                                materia_dir = get_materia_dir(materia_seleccionada)
                                output_file = materia_dir / "salidas" / f"{trabajo_name}_estructura.md"
                                with open(output_file, "w", encoding="utf-8") as f:
                                    f.write(resultado)
                                st.info(f"📁 Estructura guardada en: {output_file.name}")
                            else:
                                st.warning("⚠️ Usando estructura básica")
                                st.markdown(resultado)
                                
                        except Exception as e:
                            st.error(f"❌ Error inesperado: {e}")

'''

# Insert before the next elif
content = content[:next_elif] + new_routing + '\n' + content[next_elif:]

with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Added Asistente de Escritura routing')

# Verify syntax
import ast
try:
    ast.parse(content)
    print('✅ Sintaxis correcta')
except SyntaxError as e:
    print(f'❌ Error en línea {e.lineno}: {e.msg}')