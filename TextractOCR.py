import boto3
from io import BytesIO
from PIL import Image

class TextractOCR:
    def __init__(self, aws_region="us-east-1"):
        self.textract = boto3.client("textract", region_name=aws_region)

    def extract_text_from_file(self, file_path):
        """Extrae texto plano línea por línea desde una imagen"""
        with open(file_path, "rb") as image_file:
            image_bytes = image_file.read()

        response = self.textract.detect_document_text(Document={'Bytes': image_bytes})
        
        raw_text = ""
        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                raw_text += item["Text"] + "\n"

        return raw_text
    

    def extract_text_from_image(self, i):
        image = Image.open(BytesIO(i))
        buffer = BytesIO()
        image.save(buffer, format="PNG")  # Asegúrate que sea PNG si ese es el formato real
        image_bytes = buffer.getvalue()

        response = self.textract.detect_document_text(Document={'Bytes': image_bytes})

        raw_text = ""
        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                raw_text += item["Text"] + "\n"

        return raw_text


    def extract_and_save(self, file_path, output_txt_path):
        """Extrae texto y lo guarda en un archivo .txt"""
        text = self.extract_text_from_file(file_path)
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        return text
