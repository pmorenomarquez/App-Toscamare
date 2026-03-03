import os
import sys
from pathlib import Path
from src.pdf_to_img import convert_pdf_to_images
from src.ocr import process_image_with_ocr, get_ocr_data
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
            
            # Paso 2: Procesar cada imagen con OCR
            print("2️⃣  Realizando OCR...")
            all_text = ""
            ocr_data_list = []
            for img_file in image_files:
                text = process_image_with_ocr(img_file)
                all_text += text + "\n"
                data = get_ocr_data(img_file, lang='spa+por')
                if data:
                    ocr_data_list.append(data)
            print(f"   ✓ OCR completado ({len(all_text)} caracteres)\n")
            
            # Paso 3: Extraer datos del albarán
            print("3️⃣  Extrayendo información del albarán...")
            albaran_data = extract_albaran_data(all_text, ocr_data_list=ocr_data_list)
            
            # Paso 4: Guardar resultados
            output_txt = output_dir / f"{pdf_file.stem}_productos.txt"
            output_csv = output_dir / f"{pdf_file.stem}_productos.csv"
            
            # Guardar en TXT
            with open(output_txt, 'w', encoding='utf-8') as f:
                f.write("PRODUCTOS EXTRAÍDOS DEL ALBARÁN\n")
                f.write("="*80 + "\n\n")
                f.write(f"Total de productos encontrados: {albaran_data['total_productos']}\n\n")
                
                for idx, producto in enumerate(albaran_data['productos'], 1):
                    f.write(f"{idx}. {producto['especie']}\n")
                    f.write(f"   Lote: {producto['lote']}\n")
                    f.write(f"   Cajas: {producto['cajas']}\n")
                    if producto['peso_kg']:
                        f.write(f"   Peso: {producto['peso_kg']} kg\n")
                    if producto.get('precio'):
                        f.write(f"   Precio: {producto['precio']} €\n") #########################################       
                    f.write(f"   Original: {producto['linea_original']}\n")
                    f.write("-" * 80 + "\n")
                
                f.write("\n\nTEXTO COMPLETO OCR (para verificación):\n")
                f.write("="*80 + "\n")
                f.write(all_text)
            
            # Guardar en CSV
            with open(output_csv, 'w', encoding='utf-8') as f:
                f.write("Lote,Especie,Cajas,Peso_KG,Precio_EUR\n")
                for producto in albaran_data['productos']:
                    peso = producto['peso_kg'] if producto['peso_kg'] else ''
                    precio = producto['precio'] if producto['precio'] else ''  #########################################
                    f.write(f"{producto['lote']},{producto['especie']},{producto['cajas']},{peso},{precio}\n")
            
            print(f"   ✓ Extraídos {albaran_data['total_productos']} productos:")
            for producto in albaran_data['productos'][:5]:  # Mostrar primeros 5
                peso_str = f" - {producto['peso_kg']} kg" if producto['peso_kg'] else ""
                precio_str = f" - {producto['precio']} €" if producto.get('precio') else ""
                print(f"     • {producto['especie']} (Cajas: {producto['cajas']}){peso_str}{precio_str}")
            
            if albaran_data['total_productos'] > 5:
                print(f"     ... y {albaran_data['total_productos'] - 5} más")
            
            print(f"\n💾 Resultados guardados:")
            print(f"   📄 TXT: {output_txt}")
            print(f"   📊 CSV: {output_csv}\n")
            
        except Exception as e:
            print(f"❌ Error procesando {pdf_file.name}: {str(e)}\n")
            continue


if __name__ == "__main__":
    main()