from pydantic import BaseModel

class URLRequest(BaseModel):
    url: str
    api_key: str
