from database.supabase_client_admin import supabase_admin
from datetime import datetime
import os
import uuid
import tempfile
import shutil
import base64
import time
import threading
from pathlib import Path

# OCR imports (usa el paquete local `ocr/src`)
from ocr.src.pdf_to_img import convert_pdf_to_images
from ocr.src.ocr import process_image_with_ocr, get_ocr_data
from ocr.src.extract import extract_albaran_data
from openpyxl import Workbook
from pypdf import PdfReader, PdfWriter
from io import BytesIO
import fitz
class PedidosService:
    
    ESTADOS = {
        "almacen": 0,
        "logistica": 1,
        "transportista": 2,
        "oficina": 3
    }
    
    # Guardar PDFs en este bucket de Supabase Storage
    BUCKET = "pedidos-pdfs"
    
    # ===============================================
    # OBTENER
    # ===============================================
    
    
    # Métodos para obtener pedidos (usa supabase_admin para bypass RLS)
    def obtener_todos(self):
        response = supabase_admin.table("pedidos").select("*").execute()
        return response.data

    # Obtener pedidos por estado (almacen, logistica, transportista, oficina)
    def obtener_por_estado(self, estado):
        response = (
            supabase_admin
            .table("pedidos")
            .select("*")
            .eq("estado", estado)
            .execute()
        )
        return response.data

    # Obtener pedidos por rol (almacen, logistica, transportista, oficina)
    def obtener_por_rol(self, rol):
        if not rol:
            return []

        rol_norm = rol.strip().lower()

        if rol_norm in ("admin", "oficina"):
            return self.obtener_todos()

        if rol_norm not in self.ESTADOS:
            return []

        estado_num = self.ESTADOS[rol_norm]
        return self.obtener_por_estado(estado_num)

    def obtener_por_id(self, pedido_id):
        """
        Obtiene un pedido por su ID y adjunta los productos relacionados.
        Usa el cliente admin para asegurar que se recuperan los productos
        independientemente de las políticas RLS (la ruta que llama a este
        método ya está protegida por autenticación).
        """
        pedido = (
            supabase_admin
            .table("pedidos")
            .select("*")
            .eq("id", pedido_id)
            .maybe_single()
            .execute()
        )

        if not pedido.data:
            return None

        # Obtener productos asociados usando el cliente admin para evitar RLS
        try:
            productos_resp = (
                supabase_admin
                .table("pedido_productos")
                .select("*")
                .eq("pedido_id", pedido_id)
                .execute()
            )
            productos = productos_resp.data or []
        except Exception:
            productos = []

        resultado = pedido.data
        resultado["productos"] = productos
        return resultado
    
    # ===============================================
    # CREAR Y SUBIR PDF
    # ===============================================
    
    # def crear(self, datos):
    #     """
    #     Crea un nuevo pedido.
    #     Siempre inicia en estado 'almacen' (0).
    #     """

    #     if not datos:
    #         return {"error": "Datos requeridos"}


    #     nuevo_pedido = {
    #         "cliente_nombre": datos["cliente_nombre"],
    #         "estado": datos.get("estado", 0),
    #         "usuario_responsable_id": datos["usuario_responsable_id"],
    #         "estado": self.ESTADOS["almacen"]  # Siempre empieza en almacen
    #     }

    #     response = (
    #         supabase
    #         .table("pedidos")
    #         .insert(nuevo_pedido)
    #         .execute()
    #     )

    #     return response.data
    
    
    # Crear un nuevo pedido con PDF. Extrae datos automáticamente del PDF con OCR.
    def crear_con_pdf(self, cliente_nombre, usuario_responsable_id, archivo_pdf):

        pedido_id = str(uuid.uuid4())
        nombre_archivo = f"{pedido_id}.pdf"

        print(f"[CREATE_PEDIDO] Iniciando creación de pedido")
        print(f"[CREATE_PEDIDO] cliente_nombre: {cliente_nombre}")
        print(f"[CREATE_PEDIDO] usuario_responsable_id: {usuario_responsable_id}")
        print(f"[CREATE_PEDIDO] archivo_pdf: {archivo_pdf.filename if archivo_pdf else None}")

        # Guardar PDF en archivo temporal para procesamiento
        tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        try:
            archivo_pdf.save(tmp_pdf.name)
            tmp_pdf_path = tmp_pdf.name
            print(f"[CREATE_PEDIDO] PDF guardado en temporales: {tmp_pdf_path}")
            
            # RECTIFICAR ORIENTACIÓN: Si el documento viene horizontal, rotarlo a vertical.
            try:
                reader = PdfReader(tmp_pdf_path)
                writer = PdfWriter()
                modificado = False
                
                for page in reader.pages:
                    w = float(page.mediabox.width)
                    h = float(page.mediabox.height)
                    
                    if w > h:
                        page.rotate(270)
                        modificado = True
                    
                    writer.add_page(page)
                
                if modificado:
                    with open(tmp_pdf_path, 'wb') as f_out:
                        writer.write(f_out)
                    print("[CREATE_PEDIDO] PDF corregido: Rotado a formato vertical exitosamente.")
            except Exception as e:
                print(f"[CREATE_PEDIDO][ERROR] Error ignorado al intentar rotar el PDF: {e}")

            # Subir a Supabase Storage
            with open(tmp_pdf_path, 'rb') as f:
                supabase_admin.storage.from_(self.BUCKET).upload(
                    nombre_archivo,
                    f.read(),
                    {"content-type": "application/pdf"}
                )
            print(f"[CREATE_PEDIDO] PDF subido a Supabase Storage: {nombre_archivo}")
        except Exception as e:
            print(f"[CREATE_PEDIDO][ERROR] Error al guardar PDF: {e}")
            return {"error": f"Error al guardar PDF: {e}"}

        # Crear pedido en BD con el PDF
        nuevo_pedido = {
            "id": pedido_id,
            "cliente_nombre": cliente_nombre,
            "estado": self.ESTADOS["almacen"],
            "usuario_responsable_id": usuario_responsable_id,
            "pdf_url": nombre_archivo
        }

        try:
            response = (
                supabase_admin
                .table("pedidos")
                .insert(nuevo_pedido)
                .execute()
            )
            print(f"[CREATE_PEDIDO] Pedido creado en BD: {pedido_id}")
        except Exception as e:
            print(f"[CREATE_PEDIDO][ERROR] Error al crear pedido en BD: {e}")
            return {"error": f"Error al crear pedido: {e}"}

        # ── Intento 1: extracción directa de texto (PDF con capa de texto) ─────────
        # Funciona de forma síncrona y es instantánea.
        # Si hay texto suficiente, insertamos productos aquí y NO lanzamos OCR.
        _direct_text_ok = False
        try:
            _t0 = time.time()
            _doc = fitz.open(tmp_pdf_path)
            _direct_text = "\n".join(page.get_text() for page in _doc)
            _doc.close()
            _direct_chars = len(_direct_text.strip())
            print(f"[CREATE_PEDIDO] Texto directo extraído: {_direct_chars} chars en {time.time()-_t0:.2f}s")

            _min_chars = int(os.getenv('PDF_DIRECT_TEXT_MIN_CHARS', '80'))
            if _direct_chars >= _min_chars:
                print(f"[CREATE_PEDIDO] Usando extracción directa de texto (sin OCR)")
                try:
                    _albaran = extract_albaran_data(_direct_text)
                    _productos = _albaran.get('productos', [])
                    print(f"[CREATE_PEDIDO] Productos extraídos (directo): {len(_productos)}")
                    for _prod in _productos:
                        try:
                            _kilos = _prod.get('peso_kg') or 0
                            _fila = {
                                'pedido_id': pedido_id,
                                'nombre_producto': _prod.get('especie') or _prod.get('linea_original'),
                                'cantidad': _kilos,
                                'precio': _prod.get('precio') or 0,
                            }
                            supabase_admin.table('pedido_productos').insert(_fila).execute()
                            print(f"[CREATE_PEDIDO] Producto insertado: {_fila['nombre_producto']}")
                        except Exception as _e:
                            print(f"[CREATE_PEDIDO][ERROR] Error insertando producto directo: {_e}")
                    _direct_text_ok = True
                except Exception as _e:
                    print(f"[CREATE_PEDIDO][WARN] Error en extract_albaran_data (directo): {_e}")
            else:
                print(f"[CREATE_PEDIDO] Texto insuficiente ({_direct_chars} chars) — usando OCR")
        except Exception as _e:
            print(f"[CREATE_PEDIDO][WARN] Error en extracción directa: {_e}")

        if _direct_text_ok:
            # PDF con texto — limpiar temporal y responder ya
            try:
                Path(tmp_pdf_path).unlink()
            except Exception:
                pass
            return response.data

        # ── Intento 2: OCR con Tesseract en hilo de fondo (PDF escaneado) ────────
        def _run_ocr_background(pedido_id, tmp_pdf_path):
            tmp_images_dir = None
            try:
                ocr_total_start = time.time()
                print(f"[OCR] Iniciando procesamiento OCR (background) para pedido {pedido_id}")

                tmp_images_dir = Path(tempfile.mkdtemp())

                # Convertir PDF a imágenes
                try:
                    ocr_dpi = int(os.getenv('OCR_DPI', '220'))
                    convert_start = time.time()
                    print(f"[OCR] convert_pdf_to_images START pedido={pedido_id} dpi={ocr_dpi}")
                    image_files = convert_pdf_to_images(tmp_pdf_path, tmp_images_dir, dpi=ocr_dpi)
                    print(f"[OCR] convert_pdf_to_images DONE pedido={pedido_id} elapsed={time.time()-convert_start:.2f}s")
                except Exception as e:
                    print(f"[OCR][ERROR] error al convertir PDF a imágenes: {e}")
                    image_files = []

                print(f"[OCR] imágenes generadas: {len(image_files)}")

                # Ejecutar OCR sobre cada imagen y recolectar texto y datos
                all_text = ""
                ocr_data_list = []
                for idx, img in enumerate(image_files, start=1):
                    page_start = time.time()
                    print(f"[OCR] Página {idx}/{len(image_files)} START img={img}")
                    try:
                        txt_start = time.time()
                        print(f"[OCR] process_image_with_ocr START img={img}")
                        t = process_image_with_ocr(img)
                        print(f"[OCR] process_image_with_ocr DONE img={img} elapsed={time.time()-txt_start:.2f}s chars={len(t)}")
                    except Exception as e:
                        print(f"[OCR][ERROR] error en process_image_with_ocr para {img}: {e}")
                        t = ""

                    all_text += t + "\n"

                    try:
                        data_start = time.time()
                        print(f"[OCR] get_ocr_data START img={img}")
                        data = get_ocr_data(img, lang='spa+por')
                        if data:
                            print(
                                f"[OCR] get_ocr_data DONE img={img} elapsed={time.time()-data_start:.2f}s "
                                f"words={len(data.get('text', [])) if isinstance(data, dict) else 'n/a'}"
                            )
                            ocr_data_list.append(data)
                        else:
                            print(f"[OCR] get_ocr_data DONE img={img} elapsed={time.time()-data_start:.2f}s result=None")
                    except Exception as e:
                        print(f"[OCR][ERROR] error en get_ocr_data para {img}: {e}")

                    print(f"[OCR] Página {idx}/{len(image_files)} DONE elapsed={time.time()-page_start:.2f}s")

                # Extraer productos del albarán
                try:
                    albaran_data = extract_albaran_data(all_text, ocr_data_list=ocr_data_list)
                except Exception as e:
                    print(f"[OCR][ERROR] error extrayendo productos: {e}")
                    albaran_data = {'productos': []}

                productos = albaran_data.get('productos', [])
                print(f"[OCR] productos extraidos: {len(productos)}")

                # Insertar productos en la tabla 'pedido_productos'
                if productos:
                    for producto in productos:
                        try:
                            kilos = producto.get('peso_kg') or 0
                            fila = {
                                'pedido_id': pedido_id,
                                'nombre_producto': producto.get('especie') or producto.get('linea_original'),
                                'cantidad': kilos,
                                'precio': producto.get('precio') or 0,
                            }
                            supabase_admin.table('pedido_productos').insert(fila).execute()
                            print(f"[OCR] Producto insertado: {fila['nombre_producto']} - {fila['cantidad']} kg - {fila['precio']} €")
                        except Exception as e:
                            print(f"[OCR][ERROR] Error al insertar producto: {e}")
                else:
                    print(f"[OCR] WARNING: No se extrajeron productos del PDF")

                print(f"[OCR] Pipeline completo pedido={pedido_id} elapsed={time.time()-ocr_total_start:.2f}s")

            except Exception as e:
                print(f"[OCR][WARNING] Error procesando OCR del PDF para pedido {pedido_id}: {e}")
            finally:
                try:
                    if tmp_pdf_path and Path(tmp_pdf_path).exists():
                        Path(tmp_pdf_path).unlink()
                        print(f"[OCR] Archivo temporal PDF limpiado")
                except Exception:
                    pass
                try:
                    if tmp_images_dir and tmp_images_dir.exists():
                        shutil.rmtree(tmp_images_dir)
                        print(f"[OCR] Directorio temporal de imágenes limpiado")
                except Exception:
                    pass

        ocr_thread = threading.Thread(
            target=_run_ocr_background,
            args=(pedido_id, tmp_pdf_path),
            daemon=True,
            name=f"ocr-{pedido_id[:8]}"
        )
        ocr_thread.start()
        print(f"[CREATE_PEDIDO] OCR lanzado en background (hilo={ocr_thread.name}), respondiendo al cliente ahora")

        return response.data
    
    # =========================
    # OBTENER URL FIRMADA
    # =========================

    def obtener_pdf_firmado(self, pedido_id):

        pedido = (
            supabase_admin
            .table("pedidos")
            .select("pdf_url, pdf_firmado")
            .eq("id", pedido_id)
            .maybe_single()
            .execute()
        )

        if not pedido.data:
            return {"error": "Pedido no encontrado"}

        nombre_archivo = pedido.data.get("pdf_firmado") or pedido.data.get("pdf_url")

        if not nombre_archivo:
            return {"error": "Este pedido no tiene PDF"}

        # Generar URL firmada (60 segundos)
        signed_url = supabase_admin.storage.from_(self.BUCKET).create_signed_url(
            nombre_archivo,
            60
        )

        return signed_url
    
    def obtener_pdf_preview(self, pedido_id):
        pedido = (
            supabase_admin
            .table("pedidos")
            .select("pdf_url")
            .eq("id", pedido_id)
            .maybe_single()
            .execute()
        )

        if not pedido.data or not pedido.data.get("pdf_url"):
            return {"error": "Este pedido no tiene PDF"}

        try:
            pdf_bytes = supabase_admin.storage.from_(self.BUCKET).download(pedido.data["pdf_url"])
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            if len(doc) == 0:
                return {"error": "PDF vacío"}
                
            page = doc[0]
            # Si es apaisado, lo mostramos derecho para que coincida con lo que procesa la firma
            if page.rect.width > page.rect.height:
                page.set_rotation(page.rotation + 270)
                
            # Render a imagen (DPI ~150 para que no sea inmensa ni se vea mal)
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            return pix.tobytes("png")
        except Exception as e:
            print(f"[PREVIEW][ERROR] Error generando preview: {e}")
            return {"error": "Error procesando el PDF para preview"}
    

    
    # Función que actualiza el estado del pedido, solo si el rol del usuario coincide con el estado actual del pedido
    def actualizar_estado(self, pedido_id, rol_usuario):
        # Obtener pedido actual
        pedido = (
            supabase_admin
            .table("pedidos")
            .select("*")
            .eq("id", pedido_id)
            .maybe_single()
            .execute()
        )

        rol_usuario = rol_usuario.strip().lower()

        if not pedido.data:
            return {"error": "Pedido no encontrado"}

        estado_actual = int(pedido.data["estado"])

        # Admin y oficina pueden avanzar cualquier estado
        if rol_usuario not in ("admin", "oficina"):
            if rol_usuario not in self.ESTADOS:
                return {"error": "Rol no válido"}
            if self.ESTADOS[rol_usuario] != estado_actual:
                return {"error": "No puedes modificar este pedido en su estado actual"}

        # Calcular siguiente estado
        siguiente_estado = estado_actual + 1

        if siguiente_estado > 4:
            return {"error": "El pedido ya está finalizado"}

        # Actualizar estado
        response = (
            supabase_admin
            .table("pedidos")
            .update({"estado": siguiente_estado})
            .eq("id", pedido_id)
            .execute()
        )

        return response.data

    # Retroceder estado: devolver pedido al rol anterior para correcciones
    def retroceder_estado(self, pedido_id, rol_usuario):
        pedido = (
            supabase_admin
            .table("pedidos")
            .select("*")
            .eq("id", pedido_id)
            .maybe_single()
            .execute()
        )

        rol_usuario = rol_usuario.strip().lower()

        if not pedido.data:
            return {"error": "Pedido no encontrado"}

        estado_actual = int(pedido.data["estado"])

        if estado_actual <= 0:
            return {"error": "El pedido ya está en el primer estado"}

        # Admin y oficina pueden retroceder cualquier estado
        # Los demás roles solo pueden retroceder su propio estado
        if rol_usuario not in ("admin", "oficina"):
            if rol_usuario not in self.ESTADOS:
                return {"error": "Rol no válido"}
            if self.ESTADOS[rol_usuario] != estado_actual:
                return {"error": "No puedes retroceder este pedido en su estado actual"}

        estado_anterior = estado_actual - 1

        response = (
            supabase_admin
            .table("pedidos")
            .update({"estado": estado_anterior})
            .eq("id", pedido_id)
            .execute()
        )

        return response.data

    # Eliminar pedido (solo admin/oficina)
    def eliminar_pedido(self, pedido_id):
        # Primero eliminar productos asociados
        supabase_admin.table("pedido_productos").delete().eq("pedido_id", pedido_id).execute()

        # Luego eliminar el pedido
        response = (
            supabase_admin
            .table("pedidos")
            .delete()
            .eq("id", pedido_id)
            .execute()
        )

        return response.data
    
    # =========================
    # FIRMAR PEDIDO (incrustar firma en PDF)
    # =========================

    def firmar_pedido(self, pedido_id, firma_base64):
        """
        Recibe la firma del cliente como imagen base64,
        la incrusta al pie del PDF original del albaran
        y sube el PDF firmado reemplazando al original.
        Tambien avanza el estado del pedido a 3 (Oficina).
        """

        # 1. Obtener pedido y verificar que tiene PDF
        pedido = (
            supabase_admin
            .table("pedidos")
            .select("*")
            .eq("id", pedido_id)
            .maybe_single()
            .execute()
        )

        if not pedido.data:
            return {"error": "Pedido no encontrado"}

        if int(pedido.data["estado"]) != 2:
            return {"error": "El pedido no esta en estado Transportista"}

        nombre_archivo = pedido.data.get("pdf_url")
        if not nombre_archivo:
            return {"error": "Este pedido no tiene PDF"}

        # 2. Descargar PDF original de Supabase Storage
        try:
            pdf_bytes = supabase_admin.storage.from_(self.BUCKET).download(nombre_archivo)
        except Exception as e:
            print(f"[FIRMA][ERROR] Error descargando PDF: {e}")
            return {"error": "Error descargando PDF original"}

        # 3. Decodificar la imagen de firma (base64 data URL → bytes)
        try:
            # Remove data URL prefix if present: "data:image/png;base64,..."
            if "," in firma_base64:
                firma_base64 = firma_base64.split(",", 1)[1]
            firma_bytes = base64.b64decode(firma_base64)
        except Exception as e:
            print(f"[FIRMA][ERROR] Error decodificando firma: {e}")
            return {"error": "Firma invalida"}

        # 4. Leer PDF original
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            print(f"[FIRMA][ERROR] Error leyendo PDF: {e}")
            return {"error": "Error procesando PDF"}

        fecha_firma = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        font = fitz.Font("helv")
        def center_text(page, text, text_y, firma_x, firma_width, font_size, color):
            w = font.text_length(text, fontsize=font_size)
            x_pos = firma_x + (firma_width - w) / 2
            page.insert_text((x_pos, text_y), text, fontsize=font_size, color=color, fontname="helv")

        # 5. Procesar SOLO la primera pagina para la firma
        if len(doc) > 0:
            page = doc[0]
            rect = page.rect
            
            # Igualar la rotacion que aplicamos en el preview (para que la firma cuadre)
            if rect.width > rect.height:
                page.set_rotation(page.rotation + 270)
                rect = page.rect 
            
            # La imagen de la firma enviada desde el frontend tiene el mismo aspect ratio 
            # y coordenadas relativas al documento completo
            firma_rect = fitz.Rect(0, 0, rect.width, rect.height)
            page.insert_image(firma_rect, stream=firma_bytes)

        # 7. Generar PDF firmado
        signed_bytes = doc.write()
        print(f"[FIRMA] PDF original: {len(pdf_bytes)} bytes, PDF firmado: {len(signed_bytes)} bytes")

        # 8. Subir PDF firmado a Supabase con nombre distinto (mantener original)
        nombre_firmado = nombre_archivo.replace(".pdf", f"_firmado_{uuid.uuid4().hex[:6]}.pdf")
        try:
            supabase_admin.storage.from_(self.BUCKET).upload(
                nombre_firmado,
                signed_bytes,
                {"content-type": "application/pdf"}
            )
            print(f"[FIRMA] PDF firmado subido: {nombre_firmado}")
        except Exception as e:
            print(f"[FIRMA][ERROR] Error subiendo PDF firmado: {e}")
            return {"error": f"Error subiendo PDF firmado: {e}"}

        # 9. Guardar ruta del PDF firmado sin avanzar estado
        try:
            supabase_admin.table("pedidos").update({
                "pdf_firmado": nombre_firmado
            }).eq("id", pedido_id).execute()
            print(f"[FIRMA] Pedido {pedido_id} pdf_firmado actualizado: {nombre_firmado}")
        except Exception as e:
            print(f"[FIRMA][ERROR] Error actualizando BD: {e}")
            return {"error": "PDF firmado pero error al actualizar estado en BD"}

        return {"message": "Firma incrustada en el PDF. Revisa el documento.", "pedido_id": pedido_id}

    def exportar_a_excel(self, pedido_id):
        response = supabase_admin.table("pedido_productos").select("*").eq("pedido_id", pedido_id).execute()
        
        productos = response.data
        
        print("Productos obtenidos:", productos)
        
        wb = Workbook()
        ws = wb.active
        
        ws.append(["Código", "Nombre", "Cantidad", "Precio"])

        for producto in productos:
            ws.append([
                producto['id'],
                producto['nombre_producto'],
                producto['cantidad'],
                producto.get('precio', 0)
            ])
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return output
        