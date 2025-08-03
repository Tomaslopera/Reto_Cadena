# Importaciones necesarias
import boto3
import re
import datetime
import io
from io import BytesIO
import os
import streamlit as st
from PIL import Image
from Validaciones import Validaciones
from TextractOCR import TextractOCR

ocr = TextractOCR()

st.set_page_config(page_title="Reto FT - Cadena SA", layout="centered")
st.markdown("<h1 style='color: white; background-color:#1e3a5f; padding:10px;'>Reto FT - Cadena SA</h1>", unsafe_allow_html=True)

st.write("## Sube una imagen del billete")
uploaded_file = st.file_uploader("Selecciona una imagen", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imagen subida", use_column_width=True)

st.write("## Parámetros de validación")
with st.form("parametros_form"):
    sorteo = st.text_input("Sorteo")
    fecha_sorteo = st.text_input("Fecha del sorteo")
    dia_de_juego = st.text_input("Día de juego")
    hora_de_juego = st.text_input("Hora de juego")
    premio_mayor = st.text_input("Premio mayor")
    valor_billete = st.text_input("Valor del billete")
    valor_fraccion = st.text_input("Valor de la fracción")
    serie = st.text_input("Serie")
    numero = st.text_input("Número")
    numero_escrito = st.text_area("Número escrito (separado por comas)", help="Ejemplo: veinte, veintitres")

    submitted = st.form_submit_button("Ejecutar validación")

if submitted and uploaded_file:
    with st.spinner("Procesando imagen con Textract y validando..."):
        # Guardar imagen temporal
        temp_path = f"temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Extraer texto con TextractOCR
        raw_text = ocr.extract_text_from_file(temp_path)
        st.text_area("Texto extraído:", raw_text, height=150)

        # Eliminar archivo temporal
        os.remove(temp_path)

        # Crear instancia del validador
        validador = Validaciones(
            raw_text=raw_text,
            sorteo=sorteo,
            fecha_sorteo=fecha_sorteo,
            dia_de_juego=dia_de_juego,
            hora_de_juego=hora_de_juego,
            premio_mayor=premio_mayor,
            valor_billete=valor_billete,
            valor_fraccion=valor_fraccion,
            serie=serie,
            numero=numero,
            numero_escrito=[x.strip() for x in numero_escrito.split(",") if x.strip()]
        )

        # Ejecutar validaciones
        resultados = validador.run_all_checks()
        counts = validador.run_all_counts()

        # Mostrar resultados
        st.success("### Resultados de las validaciones:")
        for clave, valor in resultados.items():
            color = "🟢" if valor else "🔴"
            st.markdown(f"- **{clave}**: {color} {valor}")

        st.info("### Conteo de coincidencias:")
        for clave, valor in counts.items():
            st.markdown(f"- **{clave} count**: {valor}")

elif submitted and not uploaded_file:
    st.error("❗ Debes subir una imagen para realizar la validación.")