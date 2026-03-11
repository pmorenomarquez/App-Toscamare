import os
import pytesseract
from PIL import Image, ImageOps

# Ruta al ejecutable de Tesseract en Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Usar tessdata local del proyecto (contiene spa, por, eng, osd)
os.environ['TESSDATA_PREFIX'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tessdata')


# ============================================================
#  DETECCIÓN DE IDIOMA
# ============================================================


def detect_language_from_image(image_path):
    """
    Detecta el idioma principal de una imagen usando Tesseract y análisis de palabras clave
    
    Args:
        image_path: Ruta a la imagen
    
    Returns:
        String con el código de idioma detectado (ej: 'spa', 'eng', 'fra', 'deu', 'por', etc.)
    """
    image = Image.open(image_path)
    image = ImageOps.exif_transpose(image)
    
    # Primero, hacer OCR con inglés para obtener el texto
    try:
        config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, lang='eng+spa+por', config=config).lower()
    except:
        return 'eng'  # Default a inglés si falla
    
    # Palabras clave por idioma (una selección pequeña pero confiable)
    keywords = {
        'eng': ['invoice', 'packing', 'weight', 'quantity', 'total', 'date', 'goods', 'description', 'price', 'receipt'],
        'spa': ['factura', 'albarán', 'cantidad', 'peso', 'precio', 'total', 'fecha', 'producto', 'concepto', 'descripción'],
        'por': ['nota', 'quantidade', 'peso', 'preço', 'data', 'total', 'descrição', 'fatura', 'recibo'],
        'fra': ['facture', 'quantité', 'poids', 'prix', 'date', 'total', 'description', 'montant', 'article'],
        'deu': ['rechnung', 'gewicht', 'menge', 'preis', 'datum', 'summe', 'artikel', 'beschreibung', 'gesamtbetrag'],
        'ita': ['fattura', 'quantità', 'peso', 'prezzo', 'data', 'totale', 'articolo', 'descrizione', 'importo'],
    }
    
    # Contar coincidencias de palabras clave
    scores = {lang: 0 for lang in keywords}
    
    for lang, words_list in keywords.items():
        for keyword in words_list:
            if keyword in text:
                scores[lang] += 1
    
    # Si encuentra palabras clave, usar el idioma con más coincidencias
    max_score = max(scores.values())
    if max_score > 0:
        detected_lang = max(scores, key=scores.get)
        return detected_lang
    
    # Fallback: usar la puntuación de Tesseract OSD si no hay palabras clave
    try:
        osd = pytesseract.image_to_osd(image)
        for line in osd.split('\n'):
            if line.startswith('Script:'):
                return 'eng'  # Default a inglés
    except:
        pass
    
    return 'eng'  # Default a inglés




def process_image_with_ocr(image_path, lang='spa+por'):
    """
    Procesa una imagen con Tesseract OCR
    Aplica una orientación básica para documentos verticales:
    - rota si la imagen está en horizontal (probablemente PDF escaneado girado)
    - usa OSD para detectar si está al revés (180°)

    Args:
        image_path: Ruta a la imagen
        lang: Idiomas para OCR (español + portugués)

    Returns:
        Texto extraído de la imagen
    """
    image = Image.open(image_path)

    # Aplicar transpose EXIF primero
    try:
        image = ImageOps.exif_transpose(image)
    except:
        pass

    # Si está en formato landscape, rotamos 90° para ponerlo en portrait
    if image.width > image.height:
        image = image.rotate(90, expand=True)

    # Intentar detectar rotación 180 usando OSD (rápido)
    try:
        osd = pytesseract.image_to_osd(image, lang=lang)
        rot = _parse_osd_rotation(osd)
        if rot == 180:
            image = image.rotate(180, expand=True)
    except:
        pass

    # Convertir a RGB si no lo es
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # OCR directo con configuración rápido
    custom_config = r'--oem 3 --psm 6'
    try:
        text = pytesseract.image_to_string(image, lang=lang, config=custom_config)
        return text
    except Exception as e:
        print(f"Error en OCR: {e}")
        return ""

def _parse_osd_rotation(osd_text):
    for line in osd_text.split('\n'):
        if 'Rotate' in line:
            try:
                return int(line.split(':')[1].strip())
            except:
                return None
    return None


# normalize_orientation left in case other modules call it, but now simply transpose

def normalize_orientation(image, lang='spa+por', prefer_portrait=True):
    """
    Corrige únicamente usando EXIF transpose sin lógica adicional.
    """
    return ImageOps.exif_transpose(image)


def get_ocr_data(image_path, lang='eng', config=None):
    """
    Obtiene datos detallados del OCR incluyendo coordenadas
    
    Args:
        image_path: Ruta a la imagen
        lang: Idiomas para OCR
    
    Returns:
        Dict con información detallada del OCR
    """
    image = Image.open(image_path)
    try:
        image = ImageOps.exif_transpose(image)
    except:
        pass

    # Si la imagen viene en landscape, rotar para portrait (igual que en process_image)
    if image.width > image.height:
        image = image.rotate(90, expand=True)

    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    try:
        if config is None:
            config = r'--oem 3 --psm 6'
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config=config,
            output_type=pytesseract.Output.DICT
        )
        return data
    except:
        return None