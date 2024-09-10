from pydantic import BaseModel

class PDFResponse(BaseModel):
    text: str
    filename: str  
