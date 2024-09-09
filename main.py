import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from io import BytesIO
from mangum import Mangum
import fitz  # PyMuPDF

app = FastAPI()
handler = Mangum(app)

class URLRequest(BaseModel):
    url: str

def convert_drive_url(drive_url):
    try:
        # Extrae el ID del archivo de Google Drive
        file_id = drive_url.split('/d/')[1].split('/')[0]
        # Convierte la URL a formato de descarga directa
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        return download_url
    except IndexError:
        raise ValueError("Invalid Google Drive URL format")

@app.post("/get_pdf_text")
async def get_pdf_text(request: URLRequest):
    try:
        # Convertir URL de visualización a URL de descarga
        download_url = convert_drive_url(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Hacer la solicitud GET al enlace de descarga directa
    response = requests.get(download_url)

    # Si la solicitud fue exitosa, procesar el contenido binario del PDF
    if response.status_code == 200:
        # Crear un objeto BytesIO a partir del contenido del PDF
        pdf_bytes = BytesIO(response.content)
        
        # Abrir el PDF con PyMuPDF
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # Extraer texto de cada página
        text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            text += page.get_text()
        
        # Cerrar el documento
        pdf_document.close()
        
        # Devolver el texto extraído como JSON
        return {"text": text}
    else:
        # Si falla la solicitud, manejar el error
        raise HTTPException(status_code=response.status_code, detail="No se pudo descargar el archivo o el archivo no existe")
