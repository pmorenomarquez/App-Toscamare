from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter


def convert_pdf_to_images(pdf_path, output_dir, dpi=150, correct_orientation=False, lang='spa+por'):
    """
    Convierte un archivo PDF en imágenes (una por página)
    Versión simplificada para máxima velocidad y compatibilidad
    
    Args:
        pdf_path: Ruta al archivo PDF
        output_dir: Directorio donde guardar las imágenes
        dpi: Resolución (150 es óptimo: rápido + buena calidad OCR)
        correct_orientation: NO se usa (demasiado lento)
    
    Returns:
        Lista de rutas a las imágenes generadas
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    
    # Convertir PDF a imágenes
    images = convert_from_path(pdf_path, dpi=dpi)
    
    image_files = []
    for i, image in enumerate(images, start=1):
        # Conversión simple a RGB (Tesseract lo prefiere)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Guardar imagen
        output_file = output_dir / f"{pdf_path.stem}_page_{i}.png"
        image.save(output_file, 'PNG')
        image_files.append(output_file)
    
    return image_files