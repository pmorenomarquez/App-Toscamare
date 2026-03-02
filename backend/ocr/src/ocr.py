import pytesseract
from PIL import Image, ImageOps


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