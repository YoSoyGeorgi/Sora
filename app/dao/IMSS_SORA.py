import os
import fitz
import cv2  
import numpy as np  
from PIL import Image  
import re  
import unicodedata  
import base64  
from io import BytesIO
from openai import OpenAI
import json



def check_file_content(file_path):
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext == '.pdf':
        doc = fitz.open(file_path)
        has_text, has_images = False, False
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text().strip()
            if text:
                has_text = True
            if page.get_images(full=True):
                has_images = True
            if has_text and has_images:
                break
        return 'PDFText' if has_text else 'PDFImage' if has_images else 'Neither', text
    elif ext in ['.jpeg', '.jpg', '.png']:
        return 'Image', None
    else:
        return 'Unsupported', None

def legibility(file_path, threshold=4.0):
    content_type, text = check_file_content(file_path)
    
    if content_type == 'Unsupported':
        return 'Unsupported file type', None, None, None
    
    if content_type == 'PDFText':
        doc = fitz.open(file_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=300)
        image = cv2.cvtColor(np.array(Image.frombytes("RGB", [pix.width, pix.height], pix.samples)), cv2.COLOR_RGB2BGR)
        return False,content_type, image, text
    
    elif content_type in ['PDFImage', 'Image']:
        if content_type == 'PDFImage':
            doc = fitz.open(file_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=300)
            image = cv2.cvtColor(np.array(Image.frombytes("RGB", [pix.width, pix.height], pix.samples)), cv2.COLOR_RGB2BGR)
        else:
            image = cv2.imread(file_path)     
        
        laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
        if laplacian_var < threshold:
            return 'Image is too blurred',content_type, None, None
        
        return False,content_type, image, None
    
    return None, None, None, None

def encode_image(image_array):
    image_pil = Image.fromarray(cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB))
    buffered = BytesIO()
    image_pil.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def process_nss_image(base64_image, api_key, model="gpt-4o"):
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system", 
                "content": "Eres un asistente especializado en extraer información de documentos del NSS (Número de Seguridad Social) mexicano. Analiza la imagen con precisión y extrae solo el número NSS de 11 dígitos. Verifica que el documento sea auténtico buscando elementos oficiales del IMSS."
            },
            {
                "role": "user", 
                "content": [
                    {
                        "type": "text", 
                        "text": "Devuelve un documento JSON con los dos campos, Número de Seguridad Social (NSS) a 11 dígitos y NSS_check (Booleano para indicar si es un documento del Seguro Social o no) del documento de NSS."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "auto"
                    }
                    }
                ]
            }
        ],
        temperature=0.0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "NSS",
                "schema": {
                    "type": "object",
                    "properties": {
                        "NSS": {"type": "string"},
                        "NSS_check": {"type": "boolean"}
                    },
                    "required": ["NSS", "NSS_check"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
    )

    # Parse the response
    total_tokens = 0
    total_tokens = response.usage.total_tokens
    response_json = json.loads(response.choices[0].message.content)
    nss = response_json['NSS']
    nss_check = response_json['NSS_check']

    if nss_check:
        nss = re.sub(r'[^0-9]', '', nss)
        
        # Check length and apply corrections if needed
        if len(nss) == 12:
            # First find any digit that repeats 3 or more times
            pattern = r'(\d)\1{2,}'
            match = re.search(pattern, nss)
            if match:
                repeated_digit = match.group(1)
                correction_pattern = f'({repeated_digit}){repeated_digit}+'
                nss = re.sub(correction_pattern, 
                            lambda m: repeated_digit * (len(m.group()) - 1), 
                            nss)
        # Final validation
        if len(nss) != 11:
            nss_check = False

    return nss, nss_check, total_tokens

def validar_nss_completo(nss_completo):
    if len(nss_completo) != 11 or not nss_completo.isdigit():
        return False
    
    # Separar los 10 dígitos base y el dígito verificador
    nss_base = nss_completo[:10]
    digito_verificador_proporcionado = int(nss_completo[-1])

    # Pesos para cada posición
    pesos = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
    suma = 0

    # Multiplicación y suma de dígitos
    for i, digito in enumerate(nss_base):
        producto = int(digito) * pesos[i]
        # Si el producto es mayor a 9, sumar los dígitos del producto
        if producto > 9:
            producto = (producto // 10) + (producto % 10)
        suma += producto

    # Calcular el residuo y dígito verificador esperado
    residuo = suma % 10
    digito_verificador_esperado = 10 - residuo if residuo != 0 else 0

    # Validar si el dígito verificador proporcionado es correcto
    return digito_verificador_proporcionado == digito_verificador_esperado

def extract_nss(file_path, api_key):
    api_key = api_key
    check, content_type, image, text = legibility(file_path)
    if check == False:
        if content_type == 'PDFText':
            nss_pattern = r'\b\d{11}\b'
            matches = re.findall(nss_pattern, text)
            matches = list(set(matches))
            if len(matches) == 1:
                nss_check = validar_nss_completo(matches[0])
                if nss_check == True:
                    return check, matches[0], True, 0
                else:
                    return "No se pudo validar el NSS", None, False, 0
            else:
                base64_image = encode_image(image)
                nss_number, is_valid, total_tokens = process_nss_image(base64_image, api_key)
                nss_check = validar_nss_completo(nss_number)
                if nss_check == True:
                    return check, nss_number, True, total_tokens
                else:
                    return "No se pudo validar el NSS", None, False, total_tokens
        else:
            base64_image = encode_image(image)
            nss_number, is_valid, total_tokens = process_nss_image(base64_image, api_key)
            nss_check = validar_nss_completo(nss_number)
            if nss_check == True:
                return check, nss_number, True, total_tokens
            else:
                return "No se pudo validar el NSS", None, False, total_tokens
    else:
        return check, None, False, 0