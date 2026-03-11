# Imports

#Blueprint --> Utilizado para organizar rutas en Flask mediante módulos. Permite crear rutas específicas para funcionalidades particulares, como productos en este caso.
#Flask --> Framework web ligero para Python, utilizado para crear aplicaciones web y APIs RESTful.
#request --> Objeto de Flask que contiene datos de la solicitud HTTP, como JSON, parámetros de consulta, etc.
#jsonify --> Función de Flask que convierte datos de Python a formato JSON para enviar respuestas HTTP.
#supabase --> Biblioteca de Python para interactuar con Supabase, una plataforma de backend como servicio que ofrece una base de datos PostgreSQL, autenticación, almacenamiento y funciones en la nube.    
#os --> Módulo de Python para interactuar con el sistema operativo, utilizado aquí para acceder a variables de entorno.
#dotenv --> Biblioteca para cargar variables de entorno desde un archivo .env, lo que permite mantener las credenciales y configuraciones sensibles fuera del código fuente.

import os
from flask import request, jsonify, Blueprint
from supabase import create_client, Client
from database.supabase_client import supabase
from database.supabase_client_admin import supabase_admin
from dotenv import load_dotenv
from auth.jwt_handler import requiere_autenticacion, requiere_rol
from utils.error_handler import respuesta_error
from utils.validators import validar_cantidad

load_dotenv()


#Creamos el blueprint
productos_bp = Blueprint('productos', __name__)

# 2. Conectar con Supabase usando tus credenciales reales. Se leen de las variables de entorno para mantener la seguridad. No se hardcodean en el código fuente.
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

#Funcion auxiliar. Crea un cliente de Supabase utilizando el token de usuario. Clave para que funcionen las politicas de seguridad Row Level Security (RLS) en tu base de datos. Sin este paso, las consultas podrían no retornar datos o fallar debido a restricciones de acceso.
def get_supabase_client(token):
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options={
            "headers": {
                #Pasamos el token de usuario autenticado. Supabase sabrá quien es y qué rol tiene.
                "Authorization": f"Bearer {token}"
            }
        }
    )

# --- RUTAS DE LA API ---

# 1. Listar productos de un pedido (GET). Depende del rol y el estado del pedido (RLS) el mostrar o no los productos. Si el usuario no tiene permiso, la respuesta será una lista vacía o un error de autorización, dependiendo de cómo estén configuradas las políticas en Supabase.
@productos_bp.route("/api/pedidos/<pedido_id>/productos", methods=['GET'])
@requiere_autenticacion
def listar_productos(pedido_id):
    try:

        # Ejecutamos la consulta
        response = supabase_admin.table("pedido_productos").select("*").eq("pedido_id", pedido_id).execute()

        return jsonify(response.data), 200

    except Exception as e:
        print(f"ERROR CRÍTICO EN GET: {str(e)}")
        return respuesta_error(str(e), 500)

# 2. Añadir un producto a un pedido (POST). Solo el rol de oficina (controlado por Supabase RLS).
@productos_bp.route('/api/pedido-productos', methods=['POST'])
@requiere_rol(["oficina", "almacen", "logistica", "admin"])
def añadir_producto():
    try:

        #Obtenemos el token de Authorization
        # token = request.headers.get("Authorization").replace("Bearer ", "")

        # #Creamos el cliente Supabase con ese token
        # sb = get_supabase_client(token)

        #Datos enviados en el cuerpo de la solicitud (JSON)
        datos = request.json

        if not validar_cantidad(datos['cantidad']):
            return respuesta_error("Cantidad inválida. Debe ser mayor que 0", 400)
            
        # Insertamos los datos en la tabla 'pedido_productos'
        nueva_fila = {
            "pedido_id": datos['pedido_id'],
            "nombre_producto": datos['nombre_producto'],
            "cantidad": datos['cantidad']
        }
        response = supabase.table("pedido_productos").insert(nueva_fila).execute()

        #Devolvemos la nueva fila insertada en formato JSON
        return jsonify(response.data), 201
    except Exception as e:
        return respuesta_error(str(e), 400)




# 3. Actualizar un producto de un pedido (PUT). Solo el rol de almacén y logística (estados 0 y 1, todo controlado por Supabase RLS).
@productos_bp.route('/api/pedido-productos/<producto_id>', methods=['PUT'])
@requiere_rol(["oficina","almacen", "logistica", "admin"])
def actualizar_producto(producto_id):
    try:
        datos = request.json
        
        # 1. Construir el payload dinámicamente (solo lo que viene en el JSON)
        payload = {}
        if "nombre_producto" in datos:
            payload["nombre_producto"] = str(datos["nombre_producto"])
        if "cantidad" in datos:
            payload["cantidad"] = float(str(datos["cantidad"]).replace(",", "."))
        if "precio" in datos:
            payload["precio"] = float(str(datos["precio"]).replace(",", "."))

        # 2. Ejecutar con el cliente global para asegurar la escritura
        response = supabase.table("pedido_productos").update(payload).eq("id", producto_id).execute()
        
        # 3. Verificación de seguridad
        if not response.data:
            # Si no hay data, puede que el ID sea incorrecto o el RLS bloquee el retorno
            return jsonify({"error": "No se pudo encontrar el producto actualizado"}), 404

        return jsonify(response.data), 200
    except Exception as e:
        return respuesta_error(str(e), 400)


# Eliminar un producto de un pedido (DELETE). Solo el rol de oficina (controlado por Supabase RLS).
@productos_bp.route('/api/pedido-productos/<producto_id>', methods=['DELETE'])
@requiere_rol(["oficina", "almacen", "logistica", "admin"])
def eliminar_producto(producto_id):
    try:

        #Obtenemos el token de Authorization
        # token = request.headers.get("Authorization").replace("Bearer ", "")

        # #Creamos el cliente Supabase con ese token
        # sb = get_supabase_client(token)

        # Eliminamos la fila de la tabla 'pedido_productos'
        response = supabase.table("pedido_productos").delete().eq("id", producto_id).execute()

        # Si no se eliminó ningún registro, significa que el producto no existe o ya fue eliminado. Devolvemos un mensaje de error.
        if not response.data:
            return respuesta_error("Producto no encontrado o ya eliminado", 404)
        
        #En el caso de éxito, devolvemos un mensaje de confirmación
        return jsonify({"message": "Producto eliminado correctamente"}), 200
    except Exception as e:
        return respuesta_error(str(e), 400)
