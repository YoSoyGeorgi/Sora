import fitz  # PyMuPDF
import logging
from app.dao.pdf_dao import PDFDAO

class PDFService:
    @staticmethod
    def process_pdf(url: str) -> tuple[str, str]:  # Retorna una tupla con el texto y el nombre del archivo
        try:
            # Descarga el PDF y obtiene el nombre del archivo
            pdf_data, filename = PDFDAO.download_pdf(url)

            # Procesar el PDF con PyMuPDF
            with fitz.open(stream=pdf_data, filetype="pdf") as doc:
                text = ""
                for page_num in range(len(doc)):
                    text += doc.load_page(page_num).get_text()

            logging.debug(f"Extracted text from PDF: {text[:200]}...")  # Muestra un preview del texto
            logging.info(f"Processed PDF file: {filename}")  # Imprime el nombre del archivo procesado

            return text, filename  # Retorna el texto y el nombre del archivo
        except Exception as e:
            logging.error(f"Failed to process PDF: {e}")
            raise Exception(f"Error processing PDF: {e}")
