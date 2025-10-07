# Reto Validación Automatizada de Fichas Técnicas (FT) – Cadena S.A.

> **Demo end-to-end** para validar Fichas Técnicas de billetes (frontal y trasera) combinando **OCR (Amazon Textract)**, **visión por computador (OpenCV)** y **etiquetado visual (Amazon Rekognition)**, con un **frontend en Streamlit**.  
> Arquitectura **ligera y de bajo costo**: Textract, Rekognition, OpenCV, Streamlit.

## Objetivo

Automatizar la **validación textual y visual** de Fichas Técnicas (FT) de billetes para reducir errores humanos, acelerar revisiones y mejorar la trazabilidad.  
La demo muestra:

- **Validación de texto (OCR + reglas)**: sorteo, fecha, valores, serie, número, etc.  
- **Validación visual (OpenCV)**: presencia/posición de logos u objetos mediante *template matching*.  
- **Etiquetas visuales (Rekognition)**: identificación de objetos genéricos y dibujo de bounding boxes.

## Arquitectura

- **TextractOCR**: extrae líneas de texto (`detect_document_text`).  
- **Validaciones / ValidacionTrasera**: reglas robustas (tolerantes a mayúsculas, tildes, separadores numéricos, saltos de línea).  
- **OpenCVMatcher**: detección multi-escala de plantillas + NMS; overlay visual.  
- **RekognitionService** (opcional): etiquetas + cajas; overlay visual.

## Funciones principales

- **Streamlit UI**:
  - Selector de **cara**: *Frontal* o *Trasera* (formularios distintos).
  - Panel **Rekognition** (etiquetas) y panel **OpenCV** (reconocimiento de imágenes con plantillas).
  - Selección de **campos a validar** (checkbox/multiselect).

- **Clases**:
  - `TextractOCR`: wrapper simple para Textract.
  - `RekognitionService`: `detect_labels`, parseo amigable y dibujo de cajas.
  - `OpenCVMatcher`: template matching robusto (CLAHE/edges, multi-escala, NMS, diagnóstico).
  - `Validaciones` (frontal): reglas flexibles sobre texto OCR (fechas, premios, valores, serie, número…).
  - `ValidacionTrasera`: reglas para la cara posterior (total plan premios, series, etc.).

## Estructura del repositorio

```bash
├── StreamlitApp.py             # Página principal Streamlit (UI)
├── Validaciones.py             # Reglas (cara frontal)
├── ValidacionTrasera.py        # Reglas (cara trasera)
├── OpenCVMatcher.py            # Template matching + NMS + visualización
├── TextractOCR.py              # OCR (Amazon Textract)
├── RekognitionService.py       # Etiquetas + cajas (Amazon Rekognition)
├── README.md                   
├── Diagramas/              # Arquitecturas de Implementación
└── FT Prueba Concepto/                # Imágenes de ejemplo para la demo
```

## Requisitos

- **Python 3.10+**
- Cuenta AWS con permisos para **Textract** y **Rekognition**
- Credenciales configuradas localmente (`aws configure`) o variables de entorno
- Librerías:
  - `streamlit`, `boto3`, `Pillow`, `opencv-python`, `numpy`

## Instalación

```bash
# 1) clonar
git clone https://github.com/<tu-org>/<tu-repo>.git
cd https://github.com/Tomaslopera/Reto_Cadena

# 2) entorno
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3) dependencias
pip install streamlit boto3 pillow numpy opencv-python
```

## Variables de entorno
```bash
AWS_ACCESS_KEY_ID=xxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxx
AWS_DEFAULT_REGION=us-east-1
```

## Ejecuciñon de la demo
```bash
Streamlit run StreamlitApp.py
```

## Uso: flujo frontal y trasera

1. **Sube la imagen** de la Ficha Técnica (frontal o trasera) en formato **JPG** o **PNG**.

2. En la **barra lateral**:

   - Selecciona la **cara**: *Frontal* o *Trasera*.
   - Elige el **modo de análisis visual**:
     - **Etiquetas (Rekognition)** → detecta objetos generales.
     - **Reconocimiento de Imágenes (OpenCV)** → compara plantillas visuales.

3. Completa los **campos de validación** según el tipo de FT.

4. Presiona **Ejecutar validación**.

5. Visualiza:
   - El **texto OCR detectado** (Amazon Textract).
   - Los **resultados de validación** (OK/FALLO).
   - Los **análisis visuales** de OpenCV o Rekognition.

## 🔬 Detalles técnicos

### TextractOCR
- Usa el método `detect_document_text` de **Amazon Textract**.  
- Extrae el texto línea por línea (`BlockType="LINE"`).  
- Devuelve un texto plano (`raw_text`) listo para validación.  
- Tolerante a mayúsculas, acentos, saltos de línea y variaciones de formato.

### Validaciones (frontal)
- Implementa reglas **flexibles** e **insensibles** a acentos y mayúsculas.  
- Soporta formatos como `$12.000`, `12,000`, o `12 000`.  
- Valida los siguientes campos:
  - `sorteo`
  - `fecha`
  - `premio_mayor`
  - `valor_billete`
  - `valor_fraccion`
  - `serie`
  - `numero`

### ValidacionTrasera
- Reglas específicas para la cara **trasera** de la FT.  
- Evalúa campos como:
  - `fecha`
  - `sorteo`
  - `valor_billete`
  - `valor_fraccion`
  - `premio_mayor`
  - `total_plan_premios`
  - `series`  
- Utiliza el mismo sistema robusto de comparación de la clase frontal.

### OpenCVMatcher
- Realiza **Template Matching** multi-escala con `cv2.matchTemplate` y `TM_CCOEFF_NORMED`.  
- Incluye preprocesamiento opcional:
  - **CLAHE** → mejora el contraste local.  
  - **Canny Edges** → detecta bordes resistentes a iluminación.  
- Parámetros configurables:
  - `threshold` → nivel mínimo de similitud.  
  - `scales` → lista de escalas a probar.  
  - `nms_iou` → supresión de solapamientos (Non-Maximum Suppression).  
- También ofrece un modo de diagnóstico (`find_best_of_templates`) para identificar la mejor coincidencia global.

### RekognitionService
- Utiliza `detect_labels` de **AWS Rekognition** para identificar objetos y zonas clave.  
- Convierte **bounding boxes** normalizados a píxeles.  
- Dibuja cajas y etiquetas con nombre y porcentaje de confianza.  
- Devuelve:
  - `labels`: etiquetas detectadas.  
  - `labeled_boxes`: coordenadas en píxeles.  
  - `raw`: respuesta completa de Rekognition.


