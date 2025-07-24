# from S3Manager import S3Manager
# from boletin_validator import BoletinValidator

# # Descargar archivo procesado
# s3 = S3Manager(bucket_name="loteria-procesados-txt")
# s3.download_txt("semana-27/boletin_001.txt", "./temp/boletin_001.txt")

# # Leer texto y validar
# with open("./temp/boletin_001.txt", "r", encoding="utf-8") as f:
#     raw_text = f.read()

# validador = BoletinValidator(
#     raw_text=raw_text,
#     sorteo=3097,
#     fecha_sorteo="15 de abril",
#     dia_de_juego="martes",
#     hora_de_juego="10:55 p.m.",
#     premio_mayor="7.000 millones",
#     valor_billete="$15.000",
#     valor_fraccion="$7.500",
#     num_fracciones=2,
#     serie="244",
#     numero="2023",
#     pie_imprenta="4 cadena"
# )

# resultados = validador.run_all_checks()
# print(resultados)
