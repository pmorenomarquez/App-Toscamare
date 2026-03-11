from database.supabase_client_admin import supabase_admin
from datetime import datetime
import uuid
import tempfile
import shutil
import base64
from pathlib import Path

# OCR imports (usa el paquete local `ocr/src`)
from ocr.src.pdf_to_img import convert_pdf_to_images
from ocr.src.ocr import process_image_with_ocr, get_ocr_data
from ocr.src.extract import extract_albaran_data
from openpyxl import Workbook
from io import BytesIO

# PDF manipulation for signature embedding
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader

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
            supabase
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

        # Procesar OCR para extraer productos del PDF
        try:
            print(f"[OCR] Iniciando procesamiento OCR para pedido {pedido_id}")
            print(f"[OCR] archivo temporal: {tmp_pdf_path}")

            # Crear un directorio temporal para imágenes
            tmp_images_dir = Path(tempfile.mkdtemp())
            print(f"[OCR] directorio temporal de imágenes: {tmp_images_dir}")

            # Convertir PDF a imágenes
            try:
                image_files = convert_pdf_to_images(tmp_pdf_path, tmp_images_dir)
            except Exception as e:
                print(f"[OCR][ERROR] error al convertir PDF a imágenes: {e}")
                image_files = []

            print(f"[OCR] imágenes generadas: {len(image_files)}")
            for p in image_files:
                print(f"[OCR] - {p}")

            # Ejecutar OCR sobre cada imagen y recolectar texto y datos
            all_text = ""
            ocr_data_list = []
            for img in image_files:
                try:
                    t = process_image_with_ocr(img)
                    print(f"[OCR] OCR texto longitud ({img}): {len(t)}")
                except Exception as e:
                    print(f"[OCR][ERROR] error en process_image_with_ocr para {img}: {e}")
                    t = ""

                all_text += t + "\n"

                try:
                    data = get_ocr_data(img, lang='spa+por')
                    if data:
                        print(f"[OCR] get_ocr_data returned words: {len(data.get('text', [])) if isinstance(data, dict) else 'n/a'}")
                        ocr_data_list.append(data)
                except Exception as e:
                    print(f"[OCR][ERROR] error en get_ocr_data para {img}: {e}")

            # Extraer productos del albarán
            try:
                albaran_data = extract_albaran_data(all_text, ocr_data_list=ocr_data_list)
            except Exception as e:
                print(f"[OCR][ERROR] error extrayendo productos: {e}")
                albaran_data = {'productos': []}

            productos = albaran_data.get('productos', [])
            print(f"[OCR] productos extraidos: {len(productos)}")
            for producto in productos[:10]:
                print(f"[OCR] producto: {producto}")

            # Insertar productos en la tabla 'pedido_productos' usando supabase_admin (bypass RLS)
            if productos:
                for producto in productos:
                    try:
                        # usar peso en kg como cantidad
                        kilos = producto.get('peso_kg') or 0
                        fila = {
                            'pedido_id': pedido_id,
                            'nombre_producto': producto.get('especie') or producto.get('linea_original'),
                            'cantidad': kilos,
                            'precio': producto.get('precio') or 0
                            
                        }
                        supabase_admin.table('pedido_productos').insert(fila).execute()
                        print(f"[OCR] Producto insertado: {fila['nombre_producto']} - {fila['cantidad']} kg - {fila['precio']} €") ####################################3
                    except Exception as e:
                        print(f"[OCR][ERROR] Error al insertar producto: {e}")
            else:
                print(f"[OCR] WARNING: No se extrajeron productos del PDF")

        except Exception as e:
            # No abortar la creación del pedido si OCR falla; registrar si es necesario
            print(f"[OCR][WARNING] Error procesando OCR del PDF para pedido {pedido_id}: {e}")
        finally:
            # Limpiar archivos temporales
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

        return response.data
    
    # =========================
    # OBTENER URL FIRMADA
    # =========================

    def obtener_pdf_firmado(self, pedido_id):

        pedido = (
            supabase_admin
            .table("pedidos")
            .select("pdf_url")
            .eq("id", pedido_id)
            .maybe_single()
            .execute()
        )

        if not pedido.data:
            return {"error": "Pedido no encontrado"}

        nombre_archivo = pedido.data["pdf_url"]

        if not nombre_archivo:
            return {"error": "Este pedido no tiene PDF"}

        # Generar URL firmada (60 segundos)
        signed_url = supabase_admin.storage.from_(self.BUCKET).create_signed_url(
            nombre_archivo,
            60
        )

        return signed_url
    

    
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
            reader = PdfReader(BytesIO(pdf_bytes))
        except Exception as e:
            print(f"[FIRMA][ERROR] Error leyendo PDF: {e}")
            return {"error": "Error procesando PDF"}

        fecha_firma = datetime.now().strftime("%d/%m/%Y %H:%M")
        writer = PdfWriter()

        # 5. Procesar cada pagina: rotar si horizontal + añadir firma
        for page in reader.pages:
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            # Rotar paginas horizontales a vertical
            if page_width > page_height:
                page.rotate(270)
                page_width, page_height = page_height, page_width

            # Crear overlay de firma para esta pagina
            overlay_buffer = BytesIO()
            cv = rl_canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

            margin = 20
            firma_width = 150
            firma_height = 50
            firma_x = page_width - firma_width - margin
            firma_y = page_height - firma_height - margin - 14

            # Texto "Firma del cliente"
            cv.setFont("Helvetica", 7)
            cv.setFillColorRGB(0.4, 0.4, 0.4)
            cv.drawCentredString(firma_x + firma_width / 2, firma_y + firma_height + 4, "Firma del cliente")

            # Imagen de la firma
            firma_image = ImageReader(BytesIO(firma_bytes))
            cv.drawImage(firma_image, firma_x, firma_y, width=firma_width, height=firma_height, mask='auto')

            # Linea debajo
            cv.setStrokeColorRGB(0.7, 0.7, 0.7)
            cv.setLineWidth(0.5)
            cv.line(firma_x, firma_y - 2, firma_x + firma_width, firma_y - 2)

            # Fecha
            cv.setFont("Helvetica", 5)
            cv.setFillColorRGB(0.5, 0.5, 0.5)
            cv.drawCentredString(firma_x + firma_width / 2, firma_y - 10, f"Firmado: {fecha_firma}")

            cv.save()
            overlay_buffer.seek(0)

            # Fusionar firma con la pagina
            overlay_page = PdfReader(overlay_buffer).pages[0]
            page.merge_page(overlay_page)
            writer.add_page(page)

        # 7. Generar PDF firmado
        signed_buffer = BytesIO()
        writer.write(signed_buffer)
        signed_buffer.seek(0)
        signed_bytes = signed_buffer.read()
        print(f"[FIRMA] PDF original: {len(pdf_bytes)} bytes, PDF firmado: {len(signed_bytes)} bytes")

        # 8. Subir PDF firmado a Supabase con nombre distinto (mantener original)
        nombre_firmado = nombre_archivo.replace(".pdf", "_firmado.pdf")
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

        # 9. Avanzar estado a 3 y guardar ruta del PDF firmado
        try:
            supabase_admin.table("pedidos").update({
                "estado": 3,
                "pdf_firmado": nombre_firmado
            }).eq("id", pedido_id).execute()
            print(f"[FIRMA] Pedido {pedido_id} avanzado a estado 3, pdf_firmado: {nombre_firmado}")
        except Exception as e:
            print(f"[FIRMA][ERROR] Error actualizando pedido: {e}")
            return {"error": "PDF firmado pero error al actualizar estado"}

        return {"message": "Firma registrada correctamente", "pedido_id": pedido_id}

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
        