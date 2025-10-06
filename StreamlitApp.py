import os
from io import BytesIO
import streamlit as st
from PIL import Image
from Validaciones import Validaciones
from TextractOCR import TextractOCR
from RekognitionService import RekognitionService           
from OpenCVMatcher import OpenCVMatcher
from ValidacionTrasera import ValidacionTrasera

st.set_page_config(page_title="Reto FT - Cadena SA", layout="centered")
st.markdown(
    "<h1 style='color: white; background-color:#1e3a5f; padding:1px; text-align:center;'>"
    "Reto FT - Cadena SA</h1>",
    unsafe_allow_html=True
)

## --- Barra lateral ---
# --- Modo de validación (frontal / trasera) ---
st.sidebar.markdown("---")
st.sidebar.subheader("Cara a validar")
cara = st.sidebar.radio("Selecciona la cara del billete", ["Frontal", "Trasera"], index=0)

st.sidebar.header("Análisis visual")
modo_analisis = st.sidebar.radio(
    "¿Qué análisis quieres ejecutar?",
    options=["Etiquetas (Rekognition)", "Reconocimiento Imágenes (OpenCV)"],
    index=0
)

# --- Parámetros Rekognition (Etiquetas) ---
st.sidebar.markdown("---")
st.sidebar.subheader("Rekognition – Etiquetas")
aws_region = st.sidebar.text_input("AWS Region", value="us-east-1")
max_labels = st.sidebar.slider("Máximo de etiquetas", 5, 100, 30)
min_conf_labels = st.sidebar.slider("Confianza mínima (%)", 50, 99, 70)

# --- Parámetros OpenCV ---
st.sidebar.markdown("---")
st.sidebar.subheader("OpenCV")
cv_basic_scale = st.sidebar.number_input(
    "Escala de plantilla (p. ej. 0.48)",
    min_value=0.10, max_value=3.00, value=1.00, step=0.02
)
cv_templates = st.sidebar.file_uploader(
    "Sube 1..N plantillas (recortes a detectar)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)
cv_threshold = st.sidebar.slider("Umbral de coincidencia (0-100)", 50, 100, 75, 1)
cv_scales_str = "1.4,1.3,1.2,1.1,1.0,0.95,0.9,0.85,0.8,0.75"
cv_use_edges = True
cv_use_clahe = True
cv_nms_iou = 0.4
cv_max_per_tpl = 50

def _parse_scales(s: str):
    try:
        vals = [float(x.strip()) for x in s.split(",") if x.strip()]
        return [v for v in vals if v > 0]
    except Exception:
        return [1.0]

## --- Carga imagen ---
st.write("## Sube una imagen del billete")
uploaded_file = st.file_uploader("Selecciona una imagen", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Imagen subida", use_column_width=True)
else:
    image = None

# -- Parámetros validaciones ---
st.write("## Parámetros de validación")
if cara == "Frontal":
    with st.form("parametros_frontales"):
        st.markdown("**¿Qué campos (frontal) quieres validar?**")
        campos_front_disponibles = [
            "sorteo","fecha","dia","hora",
            "premio_mayor","valor_billete","valor_fraccion",
            "serie","numero"
        ]
        campos_a_validar = st.multiselect(
            "",
            options=campos_front_disponibles,
            default=campos_front_disponibles
        )

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
else:
    with st.form("parametros_traseros"):
        st.markdown("**¿Qué campos (trasera) quieres validar?**")
        campos_back_disponibles = [
            "fecha","sorteo","valor_billete","valor_fraccion",
            "premio_mayor","total_plan_premios","series"
        ]
        campos_a_validar = st.multiselect(
            "",
            options=campos_back_disponibles,
            default=campos_back_disponibles
        )

        # Campos típicos de la cara trasera (según tu imagen/RAW):
        fecha_sorteo = st.text_input("Fecha del sorteo")
        sorteo = st.text_input("Número de sorteo")
        valor_billete = st.text_input("Valor del billete")
        valor_fraccion = st.text_input("Valor de la fracción")
        premio_mayor = st.text_input("Premio mayor")
        total_plan_premios = st.text_input("Total plan premios")
        series = st.text_input("Series")

        # variables no usadas en trasera pero esperadas por tu código existente
        dia_de_juego = ""
        hora_de_juego = ""
        serie = ""
        numero = ""

        submitted = st.form_submit_button("Ejecutar validación")

## --- Procesamiento ---
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
        if cara == "Frontal":
            from Validaciones import Validaciones  # tu clase frontal
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
                checks_enabled=set(campos_a_validar),
            )
        else:
            validador = ValidacionTrasera(
                raw_text=raw_text,
                fecha_sorteo=fecha_sorteo,
                sorteo=sorteo,
                valor_billete=valor_billete,
                valor_fraccion=valor_fraccion,
                premio_mayor=premio_mayor,
                total_plan_premios=total_plan_premios,
                series=series,
                checks_enabled=set(campos_a_validar),
            )

        resultados = validador.run_all_checks()
        counts = validador.run_all_counts()

        st.subheader("Resultados de las validaciones")
        for clave, valor in resultados.items():
            estado = "OK" if valor else "FALLO"
            st.markdown(f"- **{clave}**: {estado}")

        st.info("Conteo de coincidencias")
        for clave, valor in counts.items():
            st.markdown(f"- **{clave}**: {valor}")

        # BONUS DEMO: resumen compacto para mostrar en la presentación
        with st.expander("Resumen para DEMO"):
            st.json({
                "cara": cara,
                "campos_validados": list(resultados.keys()),
                "validados_ok": [k for k, v in resultados.items() if v],
                "total_ok": sum(1 for v in resultados.values() if v),
                "total_fallos": sum(1 for v in resultados.values() if not v),
            })

        # ----------- ANÁLISIS VISUAL -----------
        st.subheader("Análisis visual")

        # ----- AWS REKOGNITION - ETIQUETAS -----
        buff = BytesIO(); image.save(buff, format="PNG"); img_bytes = buff.getvalue()

        if modo_analisis == "Etiquetas (Rekognition)":
            try:
                rk = RekognitionService(region_name=aws_region)
                labels_res = rk.detect_labels_pretty(
                    img_bytes, max_labels=int(max_labels), min_conf=float(min_conf_labels)
                )

                st.markdown("#### Etiquetas detectadas")
                if labels_res["labels"]:
                    st.dataframe({
                        "Etiqueta": [x["name"] for x in labels_res["labels"]],
                        "Confianza (%)": [x["confidence"] for x in labels_res["labels"]],
                        "Padres": [", ".join(x["parents"]) if x["parents"] else "-" for x in labels_res["labels"]],
                        "#Instancias": [x["instances"] for x in labels_res["labels"]],
                    }, use_container_width=True)
                else:
                    st.info("Sin etiquetas a ese umbral.")

                if labels_res["labeled_boxes"]:
                    vis_img = rk.draw_labeled_boxes(image, labels_res["labeled_boxes"])
                    st.image(vis_img, caption="Cajas detectadas (DetectLabels)")
                with st.expander("Respuesta cruda"):
                    st.json(labels_res["raw"])
            except Exception as e:
                st.error(f"Rekognition DetectLabels: {e}")
        # ----- OpenCV - RECONOCIMIENTO IMÁGENES -----
        else:
            if not cv_templates:
                st.info("Sube al menos una plantilla (recorte) en la barra lateral.")
            else:
                try:
                    cv_m = OpenCVMatcher(use_edges=cv_use_edges, use_clahe=cv_use_clahe)
                    
                    # --- Carga plantillas ---
                    templates = {}
                    max_tpl_w, max_tpl_h = 0, 0
                    for f in cv_templates:
                        name = os.path.splitext(os.path.basename(f.name))[0]
                        tpl_img = Image.open(f).convert("RGB")
                        templates[name] = tpl_img
                        w, h = tpl_img.size
                        max_tpl_w = max(max_tpl_w, w)
                        max_tpl_h = max(max_tpl_h, h)

                    # --- Matching múltiple ---
                    detections = []
                    W, H = image.size
                    raw_scales = _parse_scales(cv_scales_str)
                    safe_scales = [
                        s for s in raw_scales
                        if int(max_tpl_w * s) <= W and int(max_tpl_h * s) <= H
                    ]
                    if not safe_scales:
                        st.warning("Todas las escalas propuestas exceden el tamaño del billete. Prueba valores menores.")
                        safe_scales = [1.0]

                    detections = cv_m.match_multiple(
                        image, templates,
                        threshold=float(cv_threshold),
                        scales=safe_scales,
                        nms_iou=float(cv_nms_iou),
                        max_per_template=int(cv_max_per_tpl),
                    )

                    # --- Resultados ---
                    if detections:
                        vis = cv_m.draw_detections(image, detections)
                        st.image(vis, caption="Detecciones OpenCV")
                        st.markdown("#### Resultados")
                        for d in detections[:100]:
                            st.markdown(f"- **{d.name}** · score {d.score:.3f} · box {d.box} · scale {d.scale}")
                    else:
                        best = cv_m.find_best_of_templates(image, templates, scales=safe_scales)
                        if best is not None:
                            st.markdown(
                                f"**Mejor score global:** {best.score:.3f} · **plantilla:** {best.name} · **escala:** {best.scale}"
                            )
                            st.image(cv_m.draw_detections(image, [best]),
                                    caption="Mejor coincidencia")                       
                        else:
                            st.info("OpenCV: no hubo ninguna coincidencia razonable (revisa el recorte y las escalas).")

                except Exception as e:
                    st.error(f"OpenCV (local): {e}")

elif submitted and image is None:
    st.error("Debes subir una imagen para realizar la validación.")