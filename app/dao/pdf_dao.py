import requests
from io import BytesIO
from urllib.parse import urlparse, unquote

class PDFDAO:
    @staticmethod
    def download_pdf(url: str):
        try:
            # Convierte la URL de Google Drive si es necesario
            if "drive.google.com" in url:
                file_id = url.split('/d/')[1].split('/')[0]
                download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                url = download_url

            # Descarga el PDF
            response = requests.get(url)
            response.raise_for_status()  # Asegúrate de que no haya errores en la solicitud

            # Intenta obtener el nombre del archivo desde el encabezado Content-Disposition
            filename = PDFDAO.extract_filename(response)
            
            # Si no hay nombre en el encabezado, intenta obtenerlo desde la URL
            if not filename:
                filename = PDFDAO.extract_filename_from_url(url)

            # Retorna el contenido del PDF como un objeto BytesIO y el nombre del archivo
            return BytesIO(response.content), filename
        except requests.RequestException as e:
            raise Exception(f"Failed to download PDF: {str(e)}")

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
