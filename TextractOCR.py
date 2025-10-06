import boto3
from io import BytesIO
from PIL import Image

class TextractOCR:
    def __init__(self, aws_region="us-east-1"):
        self.textract = boto3.client("textract", region_name=aws_region)

    def extract_text_from_file(self, file_path):
        with open(file_path, "rb") as image_file:
            image_bytes = image_file.read()

        response = self.textract.detect_document_text(Document={'Bytes': image_bytes})
        raw_text = ""
        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                raw_text += item["Text"] + "\n"
        return raw_text
