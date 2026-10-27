#!/usr/bin/env python3
"""Add missing menu routing"""
with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the config option routing
idx = content.find('elif opcion == "Configuración y herramientas":')
if idx == -1:
    idx = content.find('elif opcion == "⚙️ Configuración y herramientas":')

print(f'Config option at: {idx}')

if idx > 0:
    # Find the line number
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'Configuración y herramientas' in line and 'elif' in line:
            print(f'Line {i+1}: {line.strip()}')
            # Insert before this line
            new_routing = '''elif opcion == "📊 Generar PowerPoint con Imágenes Reales":
    st.header("📊 Generar PowerPoint con Imágenes Reales")
    
    materias = list_materias()
    
    if not materias:
        st.warning("No hay materias creadas. Primero crea una materia.")
    else:
        # Formulario para configurar la presentación
        with st.form("form_ppt_imagenes"):
            col1, col2 = st.columns(2)
            
            with col1:
                materia_seleccionada = st.selectbox(
                    "Materia:",
                    materias,
                    key="ppt_materia_imagenes"
                )
                
                titulo = st.text_input(
                    "Título de la presentación:",
                    placeholder="Ej: Fundamentos de la Terapia Cognitivo-Conductual",
                    help="Título completo de tu presentación"
                )
            
            with col2:
                trabajo_name = st.text_input(
                    "Nombre del archivo:",
                    value="presentacion",
                    help="Nombre para el archivo de la presentación"
                )
                
                num_diapositivas = st.slider(
                    "Número aproximado de diapositivas:",
                    min_value=8,
                    max_value=20,
                    value=12,
                    step=1
                )
            
            st.info("""
            📊 **Generador de PowerPoint con Imágenes Reales**
            Este agente crea una presentación PowerPoint profesional con las siguientes características:
            
            ✅ **Imágenes basadas en TU material** - Solo usa imágenes relacionadas con el contenido de tu libro, NO imágenes inventadas o de stock genéricas.
            
            ✅ **Diseño académico profesional** - Estructura clara, colores coherentes, tipografía legible.
            
            ✅ **Contenido estructurado** - Introducción, desarrollo, conclusiones y referencias.
            
            ✅ **Notas para el orador** - Texto guía para cada diapositiva.
            """)
            
            submitted = st.form_submit_button("📊 Generar Estructura PowerPoint", type="primary")
            
            if submitted:
                if not titulo:
                    st.error("El título es obligatorio.")
                else:
                    with st.spinner("Generando estructura de PowerPoint con imágenes reales..."):
                        try:
                            resultado = generar_powerpoint_imagenes_agente(materia_seleccionada, trabajo_name, titulo)
                            
                            if resultado.startswith("✅"):
                                st.success("✅ Estructura PowerPoint generada!")
                                st.markdown(resultado)
                                
                                # Mostrar archivo guardado
                                materia_dir = get_materia_dir(materia_seleccionada)
                                output_file = materia_dir / "salidas" / f"{trabajo_name}_estructura_ppt.md"
                                if output_file.exists():
                                    with open(output_file, "rb") as f:
                                        st.download_button(
                                            label="💾 Descargar estructura PowerPoint (Markdown)",
                                            data=f.read(),
                                            file_name=output_file.name,
                                            mime="text/markdown"
                                        )
                            else:
                                st.warning("⚠️ Usando estructura básica")
                                st.markdown(resultado)
                                
                        except Exception as e:
                            st.error(f"❌ Error inesperado: {e}")

'''
            # Insert before the config option
            content = content[:idx] + new_routing + '\n' + content[idx:]
            
            with open(r'C:\Universidad\estudio-psicologia\scripts\streamlit_app.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print('✅ Added routing for PowerPoint with images')
            break
    else:
        print('❌ Config option not found in routing')
else:
    print('❌ Config option not found')