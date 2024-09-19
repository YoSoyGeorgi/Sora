import os
import fitz  # PyMuPDF for PDF manipulation
import cv2  
import numpy as np  
from PIL import Image  
import pytesseract  
import re  
import unicodedata  
import base64  
from io import BytesIO
from PyPDF2 import PdfReader
from pyzbar.pyzbar import decode  # For decoding QR/barcodes
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import ssl
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from openai import OpenAI

# Disable warnings about unverified HTTPS requests
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Set up Tesseract OCR path
pytesseract.pytesseract.tesseract_cmd = r'./Tesseract/tesseract.exe'



def check_file_type(file_path):
    """Verifica el tipo de archivo basado en su extensión."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext == '.pdf':
        return 'pdf'
    elif ext in ['.jpg', '.jpeg', '.png', '.heic']:
        return 'image'
    else:
        return 'unsupported'

def is_pdf_text_or_image(file_path):
    """Determina si un PDF contiene texto o imágenes."""
    doc = fitz.open(file_path)
    has_text = False
    has_images = False
    for page in doc:
        text = page.get_text()
        if text.strip():
            has_text = True
        images = page.get_images(full=True)
        if images:
            has_images = True
        if has_text and has_images:
            break
    if has_text:
        return 'PDFText'
    elif has_images:
        return 'PDFImage'
    else:
        return 'Neither'

def check_legibility_pdf_image(file_path, threshold=24.0):
    """Verifica la legibilidad de una imagen o PDF."""
    doc = fitz.open(file_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=300)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    blur_param = cv2.Laplacian(image, cv2.CV_64F).var()
    if blur_param < threshold:
        return 'Image is too blurred', image, blur_param
    return None, image, blur_param

def check_legibility_image(file_path, threshold=24.0):
    image = cv2.imread(file_path)
    blur_param = cv2.Laplacian(image, cv2.CV_64F).var()
    if blur_param < threshold:
        return 'Image is too blurred', image, blur_param
    return None, image, blur_param

def extract_text_from_first_page(pdf_path):
    """Extrae texto de la primera página de un archivo PDF."""
    reader = PdfReader(pdf_path)
    first_page = reader.pages[0]  # Access the first page
    extracted_text = first_page.extract_text()  # Extract text from the first page
    return extracted_text

def check_output(extracted_text):
    """Verifica si el texto extraído contiene las palabras clave 'RFC' y 'CIF'."""
    if 'RFC' in extracted_text and 'CIF' in extracted_text:  # Check if both substrings are in the text
        return "valid"
    else:
        return "Texto inválido"

def parse_pdf_text(extracted_text):
    """Extrae información específica del texto del PDF usando expresiones regulares."""
    # Define patrones regex para los campos
    patterns = {
        "CIF": r"idCIF:\s*(\d+)",
        "RFC": r"RFC:\s*([A-Z0-9]+)",
        "Fechainiciodeoperaciones": r"Fechainiciodeoperaciones:\s*(.*?)(?=\n)",
        "Fechadeúltimocambiodeestado": r"Fechadeúltimocambiodeestado:\s*(.*?)(?=\n)",
        "NombreComercial":r"NombreComercial:\s*(.*?)(?=\n)",
        "Estatusenelpadrón":r"Estatusenelpadrón:\s*([A-Z\s]+)(?=\n)",
        "CURP": r"CURP:\s*([A-Z0-9]+)",
        "Nombre": r"Nombre\(s\):\s*(.*?)(?=\nPrimer)",
        "PrimerApellido": r"PrimerApellido:\s*(.*?)(?=\nSegundo)",
        "SegundoApellido": r"Segundo Apellido:\s*(.*?)(?=\nFecha)",
        "CodigoPostal": r"CódigoPostal:\s*(\d+)",
        "TipoVialidad": r"TipodeVialidad:\s*(.*?)(?=\nNombre)",
        "NombreVialidad": r"NombredeVialidad:\s*(.*?)(?=\nNúmero)",
        "NumeroExterior": r"NúmeroExterior:\s*(.*?)(?=\nNúmero)",
        "NumeroInterior": r"NúmeroInterior:*(.*?)(?=Nombre)",
        "NombreColonia": r"NombredelaColonia:\s*(.*?)(?=\nNombre)",
        "NombreLocalidad": r"NombredelaLocalidad:\s*([A-Z\s]+)(?=\n|Nombre)",
        "NombreMunicipio": r"NombredelMunicipio oDemarcación Territorial:\s*(.*?)(?=\nNombre)",
        "NombredelaEntidadFederativa": r"NombredelaEntidadFederativa:\s*(.*?)(?=EntreCalle)"
    }
    # Extract the data using the regex patterns
    extracted_data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, extracted_text, re.DOTALL)
        extracted_data[key] = match.group(1).strip() if match else ""
    # Fix the issue where NumeroInterior is 'N' (assumed missing value)
    if extracted_data["NombreComercial"] == 'Datos del domicilio registrado':
        extracted_data["NombreComercial"] = ""
    if extracted_data["NumeroInterior"] == 'N':
        extracted_data["NumeroInterior"] = ""
    # Remove any residual newline characters and extra spaces
    for key in extracted_data:
        extracted_data[key] = ' '.join(extracted_data[key].split())
    # Add space in NumeroExterior if needed
    if re.match(r'\d+[A-Z]+', extracted_data["NumeroExterior"]):
        extracted_data["NumeroExterior"] = re.sub(r'(\d+)([A-Z]+)', r'\1 \2', extracted_data["NumeroExterior"])
    # Ensure NombreVialidad doesn't contain NúmeroExterior
    extracted_data["NombreVialidad"] = re.sub(r'\s*NúmeroExterior:.*$', '', extracted_data["NombreVialidad"])
    # Fix NombreLocalidad to not include NombreMunicipio information
    # nombre_localidad_match = re.search(r"NombredelaLocalidad:\s*(.*?)\s*(?=\nNombredel)", extracted_text, re.DOTALL)
    # if nombre_localidad_match:
    #     extracted_data["NombreLocalidad"] = nombre_localidad_match.group(1).strip()
    return extracted_data

class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        # Use TLSv1.2 and lower the security level for compatibility with smaller DH keys
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.set_ciphers('DEFAULT:@SECLEVEL=1')  # Lower security level to allow smaller DH keys
        context.check_hostname = False  # Disable hostname check
        context.verify_mode = ssl.CERT_NONE  # Disable certificate verification temporarily
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)

def fetch_sat_data(idCIF, RFC):
    url = f"https://siat.sat.gob.mx/app/qr/faces/pages/mobile/validadorqr.jsf?D1=10&D2=1&D3={idCIF}_{RFC}"
    # print(f"Fetching URL: {url}")
    session = requests.Session()
    session.mount('https://', SSLAdapter())
    try:
        response = session.get(url, verify=False)
        response.raise_for_status() 
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def parse_sat_data(idCIF, RFC, scrapdata):
    result = {
        'CIF': idCIF,
        'RFC': RFC,
        'Fechainiciodeoperaciones': '',
        'Fechadeúltimocambiodeestado': '',
        'NombreComercial': '',
        'Estatusenelpadrón': '',
        'CURP': '',
        'Nombre': '',
        'PrimerApellido': '',
        'SegundoApellido': '',
        'CodigoPostal': '',
        'TipoVialidad': '',
        'NombreVialidad': '',
        'NumeroExterior': '',
        'NumeroInterior': '',
        'NombreColonia': '',
        'NombreLocalidad': '',
        'NombreMunicipio': '',
        'NombredelaEntidadFederativa': ''
    }
    tables = scrapdata.find_all('table', class_='ui-panelgrid')
    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) == 2:
                key = cells[0].text.strip(':').strip()
                value = cells[1].text.strip()
                
                if 'CURP' in key:
                    result['CURP'] = value
                elif 'Nombre' in key and 'Comercial' not in key and 'vialidad' not in key:
                    if result['Nombre'] == '':  # First 'Nombre' is the person’s name
                        result['Nombre'] = value
                elif 'Apellido Paterno' in key:
                    result['PrimerApellido'] = value
                elif 'Apellido Materno' in key:
                    result['SegundoApellido'] = value
                elif 'Fecha de Inicio de operaciones' in key:
                    result['Fechainiciodeoperaciones'] = value.replace('-', '')
                elif 'Fecha del último cambio de situación' in key:
                    result['Fechadeúltimocambiodeestado'] = value.replace('-', '')
                elif 'Situación del contribuyente' in key:
                    result['Estatusenelpadrón'] = value
                elif 'CP' in key:
                    result['CodigoPostal'] = value
                elif 'Tipo de vialidad' in key:
                    result['TipoVialidad'] = value
                elif 'Nombre de la vialidad' in key:
                    result['NombreVialidad'] = value
                elif 'Número exterior' in key:
                    result['NumeroExterior'] = value
                elif 'Número interior' in key:
                    result['NumeroInterior'] = value
                elif 'Colonia' in key:
                    result['NombreColonia'] = value
                elif 'Municipio o delegación' in key:
                    result['NombreMunicipio'] = value
                    result['NombreLocalidad'] = value
                elif 'Entidad Federativa' in key:
                    result['NombredelaEntidadFederativa'] = value
    # Remove extra spaces (but not all spaces)
    for key in result:
        if isinstance(result[key], str):
            result[key] = result[key].strip()  # Just strip leading/trailing spaces
    return result

def compare_normalized_fields(dict1, dict2):
    differences = []
    date_fields = ['Fechainiciodeoperaciones', 'Fechadeúltimocambiodeestado']
    spanish_months = {
        'ENERO': '01', 'FEBRERO': '02', 'MARZO': '03', 'ABRIL': '04',
        'MAYO': '05', 'JUNIO': '06', 'JULIO': '07', 'AGOSTO': '08',
        'SEPTIEMBRE': '09', 'OCTUBRE': '10', 'NOVIEMBRE': '11', 'DICIEMBRE': '12'
    }
    
    def normalize_date(date_str):
        try:
            # Try parsing the numeric date format first (DDMMYYYY)
            return datetime.strptime(date_str, '%d%m%Y').date()
        except ValueError:
            # Clean the string by removing extra "DE" and spaces
            cleaned_date_str = date_str.replace("DE", "").strip().upper()
            
            # Replace Spanish month names with their numeric equivalents
            for month_name, month_number in spanish_months.items():
                if month_name in cleaned_date_str:
                    cleaned_date_str = cleaned_date_str.replace(month_name, month_number)
                    break
            # Remove remaining spaces and try parsing again
            cleaned_date_str = cleaned_date_str.replace(" ", "")
            try:
                return datetime.strptime(cleaned_date_str, '%d%m%Y').date()
            except ValueError:
                return None
    
    # Get the union of all keys from both dictionaries
    all_fields = set(dict1.keys()).union(set(dict2.keys()))
    
    for field in all_fields:
        val1 = dict1.get(field, '')
        val2 = dict2.get(field, '')
        
        # Check if the field is a date and normalize it
        if field in date_fields:
            norm_val1 = normalize_date(val1)
            norm_val2 = normalize_date(val2)
        else:
            # For non-date fields, use the raw values for comparison
            norm_val1 = val1
            norm_val2 = val2
        
        # Compare the normalized values
        if norm_val1 != norm_val2:
            differences.append({
                'Field': field,
                'Value in dict1': norm_val1,
                'Value in dict2': norm_val2
            })
    
    return differences

def rotate_image_pillow(image, angle):
    """Rotate the given PIL image by the specified angle."""
    return image.rotate(angle, expand=True)

def process_image_for_qr(image):
    height, width = image.shape[:2]
    cropped_img = cv2.cvtColor(image[:height//2, :width//2], cv2.COLOR_BGR2GRAY)
    
    # Try decoding the cropped image
    decoded_objects = decode(cropped_img)
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8'), decoded_objects[0].rect
    
    # Apply image processing techniques
    processed_img = cv2.erode(cv2.dilate(
        cv2.filter2D(cropped_img, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])),
        np.ones((2, 2), np.uint8), iterations=1), np.ones((2, 2), np.uint8), iterations=1)
    
    # Try decoding the processed image
    decoded_objects = decode(processed_img)
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8'), decoded_objects[0].rect
    
    # Apply thresholding and try decoding
    _, thresh_img = cv2.threshold(processed_img, 127, 255, cv2.THRESH_BINARY)
    decoded_objects = decode(thresh_img)
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8'), decoded_objects[0].rect
    
    # Try another threshold value
    _, thresh_img = cv2.threshold(processed_img, 210, 255, cv2.THRESH_BINARY)
    decoded_objects = decode(thresh_img)
    if decoded_objects:
        return decoded_objects[0].data.decode('utf-8'), decoded_objects[0].rect
    
    # If no QR code is found, return empty string and None
    return '', None

def extract_and_check_text_from_image(img_cv):
    for angle in [0, 180, 90, 270]:
        if angle != 0:
            img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
            img_pil = rotate_image_pillow(img_pil, angle)
            img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        data, bbox = process_image_for_qr(img_cv)
        if bbox is not None:
            break
    if bbox is None or data == '':
        return 'QR code not detected', None, None, None, img_cv, None, None, None
    qr_x, qr_y, qr_width, qr_height = bbox
    original_qr_coords = (196, 632, 347, 347)
    original_text_coords = (1310, 500, 1100, 230)
    delta_x, delta_y = original_text_coords[0] - original_qr_coords[0], original_text_coords[1] - original_qr_coords[1]
    scale_x, scale_y = qr_width / original_qr_coords[2], qr_height / original_qr_coords[3]
    text_x, text_y = qr_x + int(delta_x * scale_x), qr_y + int(delta_y * scale_y)
    bbox_text = (text_x, text_y, int(original_text_coords[2] * scale_x), int(original_text_coords[3] * scale_y))
    text_x = max(0, text_x)
    text_y = max(0, text_y)
    width = int(original_text_coords[2] * scale_x)
    height = int(original_text_coords[3] * scale_y)
    max_width = min(width, img_cv.shape[1] - text_x)
    max_height = min(height, img_cv.shape[0] - text_y)
    cropped_image = img_cv[text_y:text_y + max_height, text_x:text_x + max_width]
    img_height, img_width = img_cv.shape[:2]
    cropped = False
    x, y, w, h = bbox_text
    if x < 0 or y < 0 or x + w > img_width or y + h > img_height:
        cropped = True
    text_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
    _, text_image2 = cv2.threshold(text_image, 120, 100, cv2.THRESH_BINARY)
    image = cv2.bitwise_not(text_image2)
    kernel = np.ones((3, 3), np.uint8)
    image = cv2.erode(image, kernel, iterations=1)
    image = cv2.dilate(image, kernel, iterations=1)
    image = cv2.bitwise_not(image)
    text = pytesseract.image_to_string(image).strip()
    check = 'constancia de situacion fiscal' in re.sub(r'[^A-Za-z0-9\s]', '', unicodedata.normalize('NFD', text)).lower()
    return None, text, data, check, img_cv, bbox, bbox_text, cropped

def text_for_ai(bbox, img_cv):
    qr_x, qr_y, qr_width, qr_height = bbox
    original_qr_coords = (196, 632, 347, 347)
    original_text_coords = (0, 1100, 2400, 1700)
    delta_x, delta_y = original_text_coords[0] - original_qr_coords[0], original_text_coords[1] - original_qr_coords[1]
    scale_x, scale_y = qr_width / original_qr_coords[2], qr_height / original_qr_coords[3]
    text_x, text_y = qr_x + int(delta_x * scale_x), qr_y + int(delta_y * scale_y)
    bbox_text = (text_x, text_y, int(original_text_coords[2] * scale_x), int(original_text_coords[3] * scale_y))
    text_x = max(0, text_x)
    text_y = max(0, text_y)
    width = int(original_text_coords[2] * scale_x)
    height = int(original_text_coords[3] * scale_y)
    max_width = min(width, img_cv.shape[1] - text_x)
    max_height = min(height, img_cv.shape[0] - text_y)
    cropped_image = img_cv[text_y:text_y + max_height, text_x:text_x + max_width]
    img_height, img_width = img_cv.shape[:2]
    cropped = False
    x, y, w, h = bbox_text
    if x < 0 or y < 0 or x + w > img_width or y + h > img_height:
        cropped = True
    img_cv = cropped_image
    return img_cv

def encode_image(image_array):
    image_pil = Image.fromarray(cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB))
    buffered = BytesIO()
    image_pil.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def open_ai(img_cv, API_SORA):
    base64_image = encode_image(img_cv)
    MODEL="gpt-4o-mini"
    client = OpenAI(api_key=API_SORA)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts information from Constancia de Situación Fiscal, and you only respond in JSON"},
            {"role": "user", "content": [
                {"type": "text", "text": "Return JSON document with the data of the document of constancia de situación fiscal"},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"}
                }
            ]}
        ],
        temperature=0.0,
       response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "constancia_del_SAT",  # Updated name to be valid
                "schema": {
                    "type": "object",
                    "properties": {
                        "Fechainiciodeoperaciones": {"type": "string"},
                        "Fechadeúltimocambiodeestado": {"type": "string"},
                        "NombreComercial": {"type": "string"},
                        "Estatusenelpadrón": {"type": "string"},
                        "CURP": {"type": "string"},
                        "Nombre": {"type": "string"},
                        "PrimerApellido": {"type": "string"},
                        "SegundoApellido": {"type": "string"},
                        "CodigoPostal": {"type": "string"},
                        "TipoVialidad": {"type": "string"},
                        "NombreVialidad": {"type": "string"},
                        "NumeroExterior": {"type": "string"},
                        "NumeroInterior": {"type": "string"},
                        "NombreColonia": {"type": "string"},
                        "NombreLocalidad": {"type": "string"},
                        "NombreMunicipio": {"type": "string"},
                        "NombredelaEntidadFederativa": {"type": "string"}
                    },
                    "required": [
                        "Fechainiciodeoperaciones", "Fechadeúltimocambiodeestado",
                        "NombreComercial", "Estatusenelpadrón", "CURP", "Nombre", "PrimerApellido",
                        "SegundoApellido", "CodigoPostal", "TipoVialidad", "NombreVialidad", "NumeroExterior",
                        "NumeroInterior", "NombreColonia", "NombreLocalidad", "NombreMunicipio",
                        "NombredelaEntidadFederativa"
                    ],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
    )

    return (response.choices[0].message.content)

def sora(file_path, api_key):
    # print(file_path)
    file_type = check_file_type(file_path)
    # print (file_type)
    if file_path == 'unsupported':
        return 'file unsoported', None, None
    elif file_type == 'pdf':
        content_type = is_pdf_text_or_image(file_path)
        # print (content_type)
        if content_type == 'PDFText':
            extracted_text = extract_text_from_first_page(file_path)
            if check_output(extracted_text)=='valid':
                pdf_data = parse_pdf_text(extracted_text)
                # print (pdf_data)
                satscrapp =  (fetch_sat_data(pdf_data["CIF"],pdf_data["RFC"]))
                if satscrapp is None:
                    return "SAT no accesible", None, pdf_data
                else:
                    parse_sat = parse_sat_data(pdf_data["CIF"],pdf_data["RFC"],satscrapp)
                    if (len(compare_normalized_fields(parse_sat, pdf_data)))==0:
                        return "SAT=DOC", parse_sat, pdf_data
                    else:
                        return "SAT<>DOC", parse_sat, pdf_data
            else:
                # print ('imagepath')
                error, image, blur = check_legibility_pdf_image(file_path)
        elif content_type == 'PDFImage':
            error, image, blur = check_legibility_pdf_image(file_path)
        else:
            print('erroooor')
    elif file_type == 'image':
        error, image, blur = check_legibility_image(file_path)
    #contniue
    if error is None:
        error, text, qr, check, img_cv, bbox, bbox_text, cropped = extract_and_check_text_from_image(image)
        if error is None:
            # print (qr)
            # plt.imshow(text_for_ai(bbox,img_cv), cmap='gray')
            # plt.title(f"Detected Text: {text}")
            # plt.axis('on')
            # plt.show()

            ai_text = open_ai(text_for_ai(bbox,img_cv), api_key)
            match = re.search(r"D3=(\d+)_", qr)
            extracted_id = match.group(1)
            ai_text_dict_final = {'CIF':extracted_id }
            match_alphanumeric = re.search(r"D3=\d+_([A-Z0-9]+)", qr)
            extracted_alphanumeric = match_alphanumeric.group(1)
            rfc = {'RFC':extracted_alphanumeric }
            ai_text_dict_final.update(rfc)
            ai_text_dict_json = json.loads(ai_text)
            ai_text_dict_final.update(ai_text_dict_json)
            satscrapp =  (fetch_sat_data(ai_text_dict_final["CIF"],ai_text_dict_final["RFC"]))
            if satscrapp is None:
                return "SAT no accesible", None, ai_text_dict_final
            else:
                parse_sat = parse_sat_data(ai_text_dict_final["CIF"],ai_text_dict_final["RFC"],satscrapp)
                if (len(compare_normalized_fields(parse_sat, ai_text_dict_final)))==0:
                    return "SAT=DOC", parse_sat, ai_text_dict_final
                else:
                    return "SAT<>DOC", parse_sat, ai_text_dict_final        
        else:
            return error, None, None
    else:
        return error, None, None