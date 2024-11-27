import os
from app.dao.pdf_dao import PDFDAO
from app.dao.APP_SORA import sora
from app.dto.pdf_response_dto import PDFResponseDTO, ErrorResponse, MismatchResponse, OCROnlyResponse, SuccessResponse
from cryptography.fernet import Fernet

class PDFService:
    @staticmethod
    def process_pdf(url: str, api_key:str) -> PDFResponseDTO:
        try:
            # Descargar el PDF y obtener el nombre del archivo
            pdf_bytes_io, filename = PDFDAO.download_pdf(url)
            print('Nombre del archivo procesado: ', filename)

                       
            # Crear una carpeta temporal personalizada en el directorio de trabajo
            custom_temp_dir = 'temp'
            if not os.path.exists(custom_temp_dir):
                os.makedirs(custom_temp_dir)
            
            # Definir la ruta del archivo en la carpeta temporal personalizada
            temp_file_path = os.path.join(custom_temp_dir, filename)

            # Guardar el archivo en la carpeta temporal personalizada
            with open(temp_file_path, 'wb') as f:
                f.write(pdf_bytes_io.getvalue())

            # Clave de cifrado compartida
            key = b'oFf4bo0WC33swZ5OF2AycMzUglVkeTmps7stCJyrmKg='

            # API key encriptada recibida en el JSON
            encrypted_api_key = api_key.encode()
            print("clave encriptada", encrypted_api_key)
            # Crea el objeto Fernet con la clave
            cipher_suite = Fernet(key)

            # Desencripta la API key
            decrypted_api_key = cipher_suite.decrypt(encrypted_api_key).decode()
            print("clave desencriptada",decrypted_api_key)


            # Llamar a la función sora con la ruta del archivo temporal
            check, sat, document = sora(temp_file_path, decrypted_api_key)
            
            print(check)
            print(sat)
            print(document)


            # Validar si el documento es legible y no se pudo obtener información del documento
            if check == "Image is too blurred" and sat == None and document == None:
                return PDFResponseDTO(
                    errorResponse=ErrorResponse(
                        status=422,
                        mensaje='El documento no es legible, por favor sube un documento con mejor calidad e intenta nuevamente'
                    )
                )

            # Validar el mismatch (cuando la información del documento no coincide con la del SAT)
            if check == "SAT<>DOC":
                return PDFResponseDTO(
                    mismatchResponse=MismatchResponse(
                        status=202,
                        mensaje='Mismatch',
                        data={
                            'documentStatus': 'El documento no coincide con el SAT',
                            'details': 'La información extraída del documento y del SAT no coinciden en uno o más campos',
                            'webScrapingData': sat,
                            'documentData': document
                        }
                    )
                )
            
            if check == 'QR code not detected' and sat == None and document == None:
                return PDFResponseDTO(
                    errorResponse=ErrorResponse(
                        status=409,
                        error='Conflict',
                        mensaje='El documento no coincide con los valores de referencia, sube un documento que cumpla con los valores y por favor intenta nuevamente'
                    )
                )

            # Si el scraping del SAT no es exitoso, pero el OCR es válido
            if check == 'SAT no accesible' and sat == None:
                return PDFResponseDTO(
                    ocrOnlyResponse=OCROnlyResponse(
                        status=201,
                        mensaje='OCR Only',
                        data={
                            'documentStatus': 'Validado sin el servicio del SAT',
                            'details': 'El servicio de scraping ha fallado o se encuentra no disponible. Validación realizada con OCR',
                            'documentData': document
                        }
                    )
                )

            # Si todo es exitoso, devolver los resultados correctos
            return PDFResponseDTO(
                successResponse=SuccessResponse(
                    status=200,
                    mensaje='Success',
                    data={
                        'documentStatus': 'Documento validado',
                        'details': 'Validación exitosa, el CIF y el RFC concuerdan en el documento y en la página del SAT.',
                        'webScrapingData': sat,
                        'documentData': document
                    }
                )
            )

        except ValueError as ve:
        # Capturar errores de valor específico
            return PDFResponseDTO(
                errorResponse=ErrorResponse(
                    status=400,
                    error='Bad request',
                    mensaje=str(ve)
                )
            )
        
        except UnboundLocalError as ule:
            # Capturar específicamente el UnboundLocalError
            return PDFResponseDTO(
                errorResponse=ErrorResponse(
                    status=400,
                    error='Bad request',
                    mensaje='Extensión del archivo inválida. Verifica tu archivo e intenta nuevamente'
                )
            )
        except Exception as e:
            # Capturar cualquier otra excepción
            return PDFResponseDTO(
                errorResponse=ErrorResponse(
                    status=500,
                    error='Internal Server Error',
                    mensaje=f'Error inesperado: {str(e)}'
                )
            )

        finally:
            # Eliminar el archivo temporal
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)