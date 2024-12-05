from fastapi import FastAPI, HTTPException
from app.dto.pdf_dto import URLRequest
from app.dto.pdf_response_dto import PDFResponseDTO as ResponseSAT
from app.dto.pdf_response_IMSS_dto import PDFResponseDTO as ResponseIMSS
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.services.pdf_service import PDFService
from app.services.pdf_service_imss import PDFServiceIMSS
from mangum import Mangum



app = FastAPI()
handler = Mangum(app)

@app.get("/")
async def hello():
    return {"message":"Test"}

@app.post("/get-sat", response_model=ResponseSAT)
async def get_pdf_text(request: URLRequest):
    try:
        # Llama al servicio para procesar el archivo
        result = PDFService.process_pdf(request.url, request.api_key)

        # Serializar el resultado completo, sin excluir `None`
        json_compatible_result = jsonable_encoder(result.dict(exclude_none=True))

        # Retornar como respuesta JSON
        return JSONResponse(content=json_compatible_result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/get-imss", response_model=ResponseIMSS)
async def get_pdf_text(request: URLRequest):
    try:
        # Llama al servicio para procesar el archivo
        result = PDFServiceIMSS.process_pdf(request.url, request.api_key)

        # Serializar el resultado completo, sin excluir `None`
        json_compatible_result = jsonable_encoder(result.dict(exclude_none=True))

        # Retornar como respuesta JSON
        return JSONResponse(content=json_compatible_result)

    except Exception as e:
        raise HTTPException(status_code=501, detail=f"Error processing PDF: {str(e)}")
