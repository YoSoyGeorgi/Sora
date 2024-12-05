import requests
from io import BytesIO
from urllib.parse import urlparse, unquote
from requests.exceptions import HTTPError

class PDFDAO:
    @staticmethod
    def download_pdf(url: str):
        try:
            # Descarga el archivo desde la URL
            response = requests.get(url)
            response.raise_for_status()  # Lanza HTTPError para códigos 4xx y 5xx

            # Extraer nombre del archivo desde el encabezado o URL
            filename = PDFDAO.extract_filename(response)
            if not filename:
                filename = PDFDAO.extract_filename_from_url(url)

            return BytesIO(response.content), filename

        except HTTPError as e:
            if e.response.status_code == 403:
                raise Exception("El archivo no es accesible. Código de estado: 403 (Forbidden)")
            elif e.response.status_code == 404:
                raise Exception("El archivo no se encontró. Código de estado: 404 (Not Found)")
            else:
                raise Exception(f"Error HTTP al descargar el archivo: {e}")

        except Exception as e:
            raise Exception(f"Error al descargar el archivo: {str(e)}")
        
        
    @staticmethod
    def extract_filename(response):
        # Busca el encabezado Content-Disposition
        content_disposition = response.headers.get('content-disposition')
        if content_disposition:
            # Intenta extraer el nombre del archivo
            filename_part = [part for part in content_disposition.split(';') if 'filename=' in part]
            if filename_part:
                filename = filename_part[0].split('=')[1].strip().strip('"')
                return filename
        return None

    @staticmethod
    def extract_filename_from_url(url: str) -> str:
        # Extrae el nombre del archivo desde la URL
        parsed_url = urlparse(url)
        filename = unquote(parsed_url.path.split('/')[-1])
        return filename
