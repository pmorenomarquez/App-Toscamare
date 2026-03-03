from database.supabase_client import supabase
from database.supabase_client_admin import supabase_admin
from datetime import datetime
import uuid
import tempfile
import shutil
from pathlib import Path
 
# OCR imports (usa el paquete local `ocr/src`)
from ocr.src.pdf_to_img import convert_pdf_to_images
from ocr.src.ocr import process_image_with_ocr, get_ocr_data
from ocr.src.extract import extract_albaran_data
from openpyxl import Workbook
from io import BytesIO
 
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
   
   
    # Métodos para obtener pedidos
    def obtener_todos(self):
        response = supabase.table("pedidos").select("*").execute()
        return response.data
 
    # Obtener pedidos por estado (almacen, logistica, transportista, oficina)
    def obtener_por_estado(self, estado):
        response = (
            supabase
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
                            'cantidad': kilos
                        }
                        supabase_admin.table('pedido_productos').insert(fila).execute()
                        print(f"[OCR] Producto insertado: {fila['nombre_producto']} - {fila['cantidad']} kg")
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
            supabase
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
        signed_url = supabase.storage.from_(self.BUCKET).create_signed_url(
            nombre_archivo,
            60
        )
 
        return signed_url
   
 
   
    # Función que actualiza el estado del pedido, solo si el rol del usuario coincide con el estado actual del pedido
    def actualizar_estado(self, pedido_id, rol_usuario):
        # Obtener pedido actual
        pedido = (
            supabase
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
       
 
        # Validar que el rol coincide con el estado actual
        if rol_usuario not in self.ESTADOS:
            return {"error": "Rol no válido"}
 
        # print("ROL DEL TOKEN:", rol_usuario)
        # print("ESTADO ACTUAL BD:", estado_actual)
        # print("ESTADO QUE DEBERÍA TENER ESE ROL:", self.ESTADOS.get(rol_usuario))
        if self.ESTADOS[rol_usuario] != estado_actual:
            return {"error": "No puedes modificar este pedido en su estado actual"}
 
        # Calcular siguiente estado
        siguiente_estado = estado_actual + 1
 
        if siguiente_estado > 3:
            return {"error": "El pedido ya está finalizado"}
 
        # Actualizar estado
        datos_actualizacion = {
            "estado": siguiente_estado
        }
 
        response = (
            supabase
            .table("pedidos")
            .update(datos_actualizacion)
            .eq("id", pedido_id)
            .execute()
        )
 
        return response.data
   
    def exportar_a_excel(self, pedido_id):
        response = supabase.table("pedido_productos").select("*").eq("pedido_id", pedido_id).execute()
       
        productos = response.data
       
        print("Productos obtenidos:", productos)
       
        wb = Workbook()
        ws = wb.active
       
        ws.append(["Código", "Nombre", "Cantidad"])
       
        for producto in productos:
            ws.append([
                producto['id'],
                producto['nombre_producto'],
                producto['cantidad']
            ])
       
        output = BytesIO()
        wb.save(output)
        output.seek(0)
       
        return output
