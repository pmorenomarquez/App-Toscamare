from pathlib import Path

import fitz  # PyMuPDF — convierte PDF a imagen sin Poppler
from PIL import Image, ImageEnhance, ImageFilter

from .ocr import normalize_orientation


def convert_pdf_to_images(pdf_path, output_dir, dpi=300, correct_orientation=True, lang='spa+por'):
    """
    Convierte un archivo PDF en imágenes (una por página) usando PyMuPDF.
    No requiere Poppler ni ningún binario externo.

    Args:
        pdf_path: Ruta al archivo PDF
        output_dir: Directorio donde guardar las imágenes
        dpi: Resolución de la imagen

    Returns:
        Lista de rutas a las imágenes generadas
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72  # 72 es la resolución base de PDF
    matrix = fitz.Matrix(zoom, zoom)

    image_files = []
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=matrix)

        # Convertir a PIL Image
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Preprocesar
        image = basic_preprocess(image)

        if correct_orientation:
            image = normalize_orientation(image, lang=lang, prefer_portrait=True)

        image = binarize_image(image)

        # Guardar imagen
        output_file = output_dir / f"{pdf_path.stem}_page_{i}.png"
        image.save(output_file, 'PNG')
        image_files.append(output_file)

    doc.close()
    return image_files


def preprocess_image(image):
    """
    Preprocesa la imagen para mejorar la precision del OCR
    """
    image = basic_preprocess(image)
    image = binarize_image(image)
    return image


def basic_preprocess(image):
    """
    Preprocesa la imagen para mejorar la precisión del OCR
    """
    # Convertir a escala de grises
    image = image.convert('L')

    # Redimensionar si es muy pequeña
    width, height = image.size
    if width < 2000:
        scale_factor = 2000 / width
        new_size = (int(width * scale_factor), int(height * scale_factor))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    # Aumentar contraste
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.5)

    # Aumentar nitidez
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)

    # Reducir ruido
    image = image.filter(ImageFilter.MedianFilter(size=3))

    return image


def binarize_image(image):
    """
    Aplica binarizacion con metodo de Otsu.
    """
    import numpy as np

    img_array = np.array(image)

    threshold = calculate_otsu_threshold(img_array)

    bin_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)

    white_ratio = float((bin_array == 255).sum()) / float(bin_array.size)
    if white_ratio < 0.02 or white_ratio > 0.98:
        bin_array = np.where(img_array > 128, 255, 0).astype(np.uint8)

    return Image.fromarray(bin_array)


def calculate_otsu_threshold(image_array):
    """
    Calcula el umbral óptimo usando el método de Otsu
    """
    import numpy as np

    hist, bin_edges = np.histogram(image_array, bins=256, range=(0, 256))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    hist = hist.astype(float) / hist.sum()

    weight1 = np.cumsum(hist)
    weight2 = 1 - weight1

    mean1 = np.cumsum(hist * bin_centers) / (weight1 + 1e-10)
    mean2 = (np.cumsum((hist * bin_centers)[::-1])[::-1]) / (weight2 + 1e-10)

    variance12 = weight1 * weight2 * (mean1 - mean2) ** 2

    threshold = np.argmax(variance12)

    return threshold
