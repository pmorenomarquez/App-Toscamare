import os
import shutil
import time
import pytesseract
from PIL import Image, ImageOps

# Ruta al ejecutable de Tesseract (compatible Windows y Linux/Docker)
_tesseract = shutil.which('tesseract') or r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = _tesseract

# Usar tessdata local del proyecto (contiene spa, por, eng, osd)
os.environ['TESSDATA_PREFIX'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tessdata')


def _env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


OCR_TEXT_TIMEOUT = int(os.getenv('OCR_TEXT_TIMEOUT', '45'))
OCR_DATA_TIMEOUT = int(os.getenv('OCR_DATA_TIMEOUT', '25'))
OCR_OSD_TIMEOUT = int(os.getenv('OCR_OSD_TIMEOUT', '5'))
OCR_USE_OSD = _env_bool('OCR_USE_OSD', default=False)


def get_ocr_runtime_info(required_langs=None):
    """Return runtime diagnostics to quickly validate OCR setup in production."""
    required_langs = required_langs or ['spa', 'por', 'eng']
    info = {
        'tesseract_cmd': pytesseract.pytesseract.tesseract_cmd,
        'tessdata_prefix': os.environ.get('TESSDATA_PREFIX'),
        'tesseract_found': bool(shutil.which('tesseract') or os.path.exists(pytesseract.pytesseract.tesseract_cmd or '')),
        'version': None,
        'available_langs': [],
        'missing_langs': [],
    }

    try:
        info['version'] = str(pytesseract.get_tesseract_version())
    except Exception as e:
        info['version'] = f'error: {e}'

    try:
        langs = pytesseract.get_languages(config='')
        info['available_langs'] = sorted(langs)
        info['missing_langs'] = [l for l in required_langs if l not in langs]
    except Exception as e:
        info['missing_langs'] = list(required_langs)
        info['available_langs'] = [f'error: {e}']

    return info


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




def process_image_with_ocr(image_path, lang='spa+por', timeout_sec=None, use_osd=None):
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
    timeout_sec = OCR_TEXT_TIMEOUT if timeout_sec is None else timeout_sec
    use_osd = OCR_USE_OSD if use_osd is None else use_osd

    image = Image.open(image_path)
    step_start = time.time()
    print(f"[OCR][process_image_with_ocr] START image={image_path} lang={lang} timeout={timeout_sec} use_osd={use_osd}")

    # Aplicar transpose EXIF primero
    try:
        image = ImageOps.exif_transpose(image)
    except:
        pass

    # Si está en formato landscape, rotamos 90° para ponerlo en portrait
    if image.width > image.height:
        print(f"[OCR][process_image_with_ocr] rotate portrait width={image.width} height={image.height}")
        image = image.rotate(90, expand=True)

    # Intentar detectar rotación 180 usando OSD (rápido)
    if use_osd:
        try:
            osd_start = time.time()
            print(f"[OCR][process_image_with_ocr] OSD start image={image_path} timeout={OCR_OSD_TIMEOUT}")
            osd = pytesseract.image_to_osd(image, lang=lang, timeout=OCR_OSD_TIMEOUT)
            print(f"[OCR][process_image_with_ocr] OSD done image={image_path} elapsed={time.time()-osd_start:.2f}s")
            rot = _parse_osd_rotation(osd)
            if rot == 180:
                image = image.rotate(180, expand=True)
                print(f"[OCR][process_image_with_ocr] OSD rotate=180 image={image_path}")
        except Exception as e:
            print(f"[OCR][process_image_with_ocr] OSD skipped/fail image={image_path} error={e}")
    else:
        print(f"[OCR][process_image_with_ocr] OSD disabled image={image_path}")

    # Convertir a RGB si no lo es
    if image.mode != 'RGB':
        image = image.convert('RGB')

    # OCR directo con configuración rápido
    custom_config = r'--oem 3 --psm 6'
    try:
        tesseract_start = time.time()
        print(f"[OCR][process_image_with_ocr] OCR start image={image_path} config={custom_config}")
        text = pytesseract.image_to_string(image, lang=lang, config=custom_config, timeout=timeout_sec)
        print(
            f"[OCR][process_image_with_ocr] OCR done image={image_path} "
            f"elapsed={time.time()-tesseract_start:.2f}s chars={len(text)} total={time.time()-step_start:.2f}s"
        )
        return text
    except Exception as e:
        print(f"[OCR][process_image_with_ocr][ERROR] image={image_path} elapsed={time.time()-step_start:.2f}s error={e}")
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
    step_start = time.time()
    print(f"[OCR][get_ocr_data] START image={image_path} lang={lang} timeout={OCR_DATA_TIMEOUT}")
    try:
        image = ImageOps.exif_transpose(image)
    except:
        pass

    # Si la imagen viene en landscape, rotar para portrait (igual que en process_image)
    if image.width > image.height:
        print(f"[OCR][get_ocr_data] rotate portrait width={image.width} height={image.height}")
        image = image.rotate(90, expand=True)

    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    try:
        if config is None:
            config = r'--oem 3 --psm 6'
        data_start = time.time()
        print(f"[OCR][get_ocr_data] image_to_data start image={image_path} config={config}")
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            config=config,
            output_type=pytesseract.Output.DICT,
            timeout=OCR_DATA_TIMEOUT
        )
        words = len(data.get('text', [])) if isinstance(data, dict) else -1
        print(
            f"[OCR][get_ocr_data] image_to_data done image={image_path} "
            f"elapsed={time.time()-data_start:.2f}s words={words} total={time.time()-step_start:.2f}s"
        )
        return data
    except Exception as e:
        print(f"[OCR][get_ocr_data][ERROR] image={image_path} elapsed={time.time()-step_start:.2f}s error={e}")
        return None