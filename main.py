from fastapi import FastAPI, HTTPException
from app.dto.pdf_dto import URLRequest
from app.dto.pdf_response_dto import PDFResponse
from app.services.pdf_service import PDFService
from mangum import Mangum

app = FastAPI()
handler = Mangum(app)

@app.post("/get_pdf_text", response_model=PDFResponse)
async def get_pdf_text(request: URLRequest):
    try:
        # Ahora la función retorna dos valores: el texto y el nombre del archivo
        text, filename = PDFService.process_pdf(request.url)
        return PDFResponse(text=text, filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

