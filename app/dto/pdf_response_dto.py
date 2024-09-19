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
    error_response: Optional[ErrorResponse] = None
    mismatch_response: Optional[MismatchResponse] = None
    ocr_only_response: Optional[OCROnlyResponse] = None
    success_response: Optional[SuccessResponse] = None

class Config:
    # Excluir campos con valor None en la respuesta JSON
    exclude_none = True