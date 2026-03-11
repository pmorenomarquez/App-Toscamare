import os
import sys
from pathlib import Path
from src.pdf_to_img import convert_pdf_to_images
from src.ocr import process_image_with_ocr, get_ocr_data, detect_language_from_image
from src.extract import extract_albaran_data


def main():
    # Configurar rutas
    base_dir = Path(__file__).parent
    pdf_dir = base_dir / "pdfs"
    images_dir = base_dir / "images"
    output_dir = base_dir / "output"
    
    # Crear directorios si no existen
    images_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # Buscar PDFs
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No se encontraron archivos PDF en la carpeta 'pdfs/'")
        return
    
    print(f"📄 Encontrados {len(pdf_files)} archivo(s) PDF\n")
    
    for pdf_file in pdf_files:
        print(f"{'='*60}")
        print(f"Procesando: {pdf_file.name}")
        print(f"{'='*60}\n")
        
        try:
            # Paso 1: Convertir PDF a imágenes
            print("1️⃣  Convirtiendo PDF a imágenes...")
            image_files = convert_pdf_to_images(pdf_file, images_dir)
            print(f"   ✓ Generadas {len(image_files)} imagen(es)\n")

            # Paso 1.5: Detectar idioma del documento para OCR y extracción
            print("2️⃣  Detectando idioma del documento...")
            detected_lang = detect_language_from_image(image_files[0])
            if detected_lang == 'eng':
                ocr_lang = 'eng'
            else:
                # Para español y portugués usamos ambos en OCR, pero el doc_type se detectará en extract_albaran_data
                ocr_lang = 'spa+por'
            
            # No forzar doc_type aquí; dejar que _detect_doc_type lo haga automáticamente
            doc_type = None
            print(f"   ✓ Idioma OCR: {ocr_lang}\n")
            
            # Paso 2: Procesar cada imagen con OCR
            print("3️⃣  Realizando OCR...")
            all_text = ""
            ocr_data_list = []
            for img_file in image_files:
                text = process_image_with_ocr(img_file, lang=ocr_lang)
                all_text += text + "\n"
                data = get_ocr_data(img_file, lang=ocr_lang)
                if data:
                    ocr_data_list.append(data)
            print(f"   ✓ OCR completado ({len(all_text)} caracteres)\n")
            
            # Paso 3: Extraer datos del albarán
            print("4️⃣  Extrayendo información del albarán...")
            albaran_data = extract_albaran_data(all_text, ocr_data_list=ocr_data_list, doc_type=doc_type)
            doc_type = albaran_data.get('doc_type', 'portugues')
            print(f"   ✓ Tipo de documento detectado: {doc_type}\n")
            
            # Paso 4: Guardar resultados
            output_csv = output_dir / f"{pdf_file.stem}_productos.csv"

            # Guardar en CSV
            with open(output_csv, 'w', encoding='utf-8') as f:
                if doc_type == 'ingles':
                    f.write("Nombre,Packing_Cantidad,Peso_With_Glaze_KG,Total\n")
                    total_weight = albaran_data.get('total_weight', '')
                    for producto in albaran_data['productos']:
                        nombre = (producto.get('scientific_name') or producto.get('especie') or '').replace(',', ' ')
                        packing_qty = (producto.get('packing_qty') or '').replace(',', ' ')
                        peso = producto['peso_kg'] if producto['peso_kg'] else ''
                        f.write(f"{nombre},{packing_qty},{peso},{total_weight}\n")
                elif doc_type == 'español_comercial':
                    f.write("Nombre,Cantidad,Precio\n")
                    for producto in albaran_data['productos']:
                        nombre = (producto.get('nombre') or producto.get('especie') or '').replace(',', ' ')
                        cantidad = producto.get('cantidad', '')
                        precio = producto.get('precio', '')
                        f.write(f"{nombre},{cantidad},{precio}\n")
                else:
                    f.write("Lote,Especie,Cajas,Peso_KG\n")
                    for producto in albaran_data['productos']:
                        peso = producto['peso_kg'] if producto['peso_kg'] else ''
                        especie = (producto['especie'] or '').replace(',', ' ')
                        f.write(f"{producto['lote']},{especie},{producto['cajas']},{peso}\n")
            
            print(f"   ✓ Extraídos {albaran_data['total_productos']} productos:")
            for producto in albaran_data['productos'][:5]:  # Mostrar primeros 5
                peso_str = f" - {producto['peso_kg']} kg" if producto['peso_kg'] else ""
                print(f"     • {producto['especie']} (Cajas: {producto['cajas']}){peso_str}")
            
            if albaran_data['total_productos'] > 5:
                print(f"     ... y {albaran_data['total_productos'] - 5} más")
            
            print(f"\n💾 Resultados guardados:")
            print(f"   📊 CSV: {output_csv}\n")
            
        except Exception as e:
            print(f"❌ Error procesando {pdf_file.name}: {str(e)}\n")
            continue


if __name__ == "__main__":
    main()