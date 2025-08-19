# --- Streamlit + Textract + Rekognition (detección de etiquetas) ---

import os
from io import BytesIO
import streamlit as st
from PIL import Image

from Validaciones import Validaciones
from TextractOCR import TextractOCR
from RekognitionService import RekognitionService

# =========================
# Configuración de página
# =========================
st.set_page_config(page_title="Reto FT - Cadena SA", layout="centered")
st.markdown(
    "<h1 style='color: white; background-color:#1e3a5f; padding:1px; text-align:center;'>"
    "Reto FT - Cadena SA</h1>",
    unsafe_allow_html=True
)

# =========================
# Barra lateral: Rekognition
# =========================
st.sidebar.header("Rekognition – Parámetros")
aws_region = st.sidebar.text_input("AWS Region", value="us-east-1")

modo_rekognition = st.sidebar.radio(
    "¿Qué análisis visual quieres hacer?",
    options=["Etiquetas (Rekognition)", "Frase (texto)", "Imagen de referencia"],
    index=0
)

# Parámetros DETECCIÓN DE ETIQUETAS
if modo_rekognition == "Etiquetas (Rekognition)":
    max_labels = st.sidebar.slider("Máximo de etiquetas", 5, 50, 25)
    min_conf_labels = st.sidebar.slider("Confianza mínima (%)", 50, 99, 80)

# Parámetros para búsqueda por frase
if modo_rekognition == "Frase (texto)":
    frase_objetivo = st.sidebar.text_input(
        "Frase objetivo",
        value="Cruz Roja Colombiana",
        help="Se buscará como secuencia de palabras cercanas en la misma línea visual"
    )
    conf_min_palabra = st.sidebar.slider("Confianza mínima por palabra", 50, 99, 70)
    gap_px = st.sidebar.slider("Distancia máx. entre palabras (px)", 40, 300, 160)
    y_tol_pct = st.sidebar.slider("Tolerancia vertical (%)", 2, 20, 12) / 100.0

# Parámetros para búsqueda por imagen
if modo_rekognition == "Imagen de referencia":
    ref_logo_file = st.sidebar.file_uploader(
        "Sube la imagen de referencia (logo recortado)",
        type=["png", "jpg", "jpeg"],
        help="Mejor PNG con fondo transparente; si no tienes OpenCV instalado devolverá 0 coincidencias."
    )
    umbral_tm = st.sidebar.slider("Umbral template matching", 60, 95, 78) / 100.0

# =========================
# Carga de imagen FT
# =========================
st.write("## Sube una imagen del billete")
uploaded_file = st.file_uploader("Selecciona una imagen", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Imagen subida", use_column_width=True)
else:
    image = None

# =========================
# Formulario de parámetros (OCR/Validaciones)
# =========================
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

    submitted = st.form_submit_button("Ejecutar validación")

# =========================
# Pipeline (Textract + Validaciones + Rekognition)
# =========================
if submitted and image is not None:
    with st.spinner("Procesando imagen con Textract y validando..."):

        # ----------- TEXTRACT -----------
        temp_path = f"temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        ocr = TextractOCR()
        raw_text = ocr.extract_text_from_file(temp_path)
        st.subheader("OCR (Textract)")
        st.text_area("Texto extraído:", raw_text, height=300)

        try:
            os.remove(temp_path)
        except OSError:
            pass

        # ----------- VALIDACIONES TEXTO -----------
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
        )
        resultados = validador.run_all_checks()
        counts = validador.run_all_counts()

        st.subheader("Resultados de las validaciones")
        for clave, valor in resultados.items():
            color = "🟢" if valor else "🔴"
            st.markdown(f"- **{clave}**: {color} {valor}")

        st.info("Conteo de coincidencias")
        for clave, valor in counts.items():
            st.markdown(f"- **{clave}**: {valor}")

        # ----------- REKOGNITION -----------
        st.subheader("Análisis visual (Rekognition)")
        rk = RekognitionService(region_name=aws_region)

        # preparar bytes de imagen
        buff = BytesIO()
        image.save(buff, format="PNG")
        img_bytes = buff.getvalue()

        # === MODO: ETIQUETAS (como la demo de AWS) ===
        if modo_rekognition == "Etiquetas (Rekognition)":
            labels_resp = rk.detect_labels(img_bytes, max_labels=int(max_labels), min_conf=float(min_conf_labels))
            # Tabla de etiquetas
            st.markdown("#### Etiquetas detectadas")
            if labels_resp.get("Labels"):
                # Mostrar lista con nombre, confianza, padres, instancias
                rows = []
                for lab in labels_resp["Labels"]:
                    name = lab.get("Name", "")
                    conf = round(lab.get("Confidence", 0.0), 2)
                    parents = ", ".join([p.get("Name", "") for p in lab.get("Parents", [])]) or "-"
                    instances = len(lab.get("Instances", []))
                    rows.append((name, conf, parents, instances))
                st.dataframe(
                    {"Etiqueta": [r[0] for r in rows],
                     "Confianza (%)": [r[1] for r in rows],
                     "Padres": [r[2] for r in rows],
                     "#Instancias": [r[3] for r in rows]}
                )
            else:
                st.info("Sin etiquetas a ese umbral.")

            # Dibujo de cajas (si Rekognition entrega Instances)
            vis_img = rk.draw_label_instances_with_names(image, labels_resp)
            if vis_img is not None:
                st.image(vis_img, caption="Cajas de instancias por etiqueta")

            with st.expander("Respuesta cruda"):
                st.json(labels_resp)

        # === MODO: FRASE (texto con Rekognition Text) ===
        elif modo_rekognition == "Frase (texto)":
            objetivo = [w.strip().lower() for w in frase_objetivo.split() if w.strip()]
            if len(objetivo) < 1:
                st.warning("Ingresa al menos una palabra en la frase objetivo.")
            else:
                res = rk.find_phrase_by_words(
                    image_bytes=img_bytes,
                    target_words=tuple(objetivo),
                    min_conf=float(conf_min_palabra),
                    word_gap_px=int(gap_px),
                    y_tol=float(y_tol_pct),
                )
                if res.get("found"):
                    st.success(f"Se detectó la frase objetivo: '{frase_objetivo}'.")
                    vis = rk.draw_boxes(image, res["boxes_px"], width=5)
                    st.image(vis, caption="Ubicación estimada (frase)")
                else:
                    st.warning("No se detectó la frase objetivo. Ajusta confianza, distancia o tolerancia.")
                    with st.expander("Detalle / debug"):
                        st.write(res.get("debug_matches", []))

        # === MODO: IMAGEN DE REFERENCIA (template matching) ===
        else:
            if ref_logo_file is None:
                st.info("Sube una imagen de referencia (logo recortado) en la barra lateral.")
            else:
                ref_img = Image.open(ref_logo_file).convert("RGB")
                boxes = rk.template_match_logo(image, ref_img, threshold=float(umbral_tm))
                if boxes:
                    st.success(f"Coincidencias de la imagen de referencia: {len(boxes)}")
                    vis = rk.draw_boxes(image, boxes, width=5)
                    st.image(vis, caption="Ubicación estimada (imagen de referencia)")
                else:
                    st.info("Sin coincidencias (o OpenCV no está instalado). Prueba otro umbral o un recorte más limpio.")

elif submitted and image is None:
    st.error("Debes subir una imagen para realizar la validación.")
