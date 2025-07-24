import boto3

class S3Manager:
    def __init__(self, bucket_name, aws_region="us-east-1"):
        self.s3 = boto3.client('s3', region_name=aws_region)
        self.bucket_name = bucket_name

    def download_txt(self, s3_key, local_path):
        """
        Descarga un archivo .txt desde S3 a una ruta local.
        :param s3_key: Ruta dentro del bucket, ej: 'semana-27/boletin_001.txt'
        :param local_path: Ruta local, ej: './descargas/boletin_001.txt'
        """
        self.s3.download_file(self.bucket_name, s3_key, local_path)
        print(f"Descargado: {local_path}")