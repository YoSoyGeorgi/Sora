from fastapi import FastAPI, HTTPException
from app.dto.pdf_dto import URLRequest
from app.dto.pdf_response_dto import PDFResponseDTO
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.services.pdf_service import PDFService
from mangum import Mangum

app = FastAPI()
handler = Mangum(app)

@app.post("/get_pdf_text", response_model=PDFResponseDTO)
async def get_pdf_text(request: URLRequest):
    try:
        # Llama al servicio para procesar el archivo
        result = PDFService.process_pdf(request.url, request.api_key)

        # Serializar manualmente el resultado excluyendo None
        json_compatible_result = jsonable_encoder(result.dict(exclude_none=True))

        # Retornar como respuesta JSON
        return JSONResponse(content=json_compatible_result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
