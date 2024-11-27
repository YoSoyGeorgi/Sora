from pydantic import BaseModel
from typing import Optional, Dict, Any

class ErrorResponse(BaseModel):
    status: int
    error: str
    mensaje: str

class MismatchResponse(BaseModel):
    status: int
    mensaje: str
    data: Dict[str, Any]

class OCROnlyResponse(BaseModel):
    status: int
    mensaje: str
    data: Dict[str, Any]

class SuccessResponse(BaseModel):
    status: int
    mensaje: str
    data: Dict[str, Any]

class PDFResponseDTO(BaseModel):
    errorResponse: Optional[ErrorResponse] = None
    mismatchResponse: Optional[MismatchResponse] = None
    ocrOnlyResponse: Optional[OCROnlyResponse] = None
    successResponse: Optional[SuccessResponse] = None

class Config:
    # Excluir campos con valor None en la respuesta JSON
    exclude_none = True