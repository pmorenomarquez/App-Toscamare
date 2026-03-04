from flask import Blueprint, jsonify, request, send_file
from auth.jwt_handler import verificar_jwt
from .pedidos_service import PedidosService
from auth.jwt_handler import requiere_autenticacion, requiere_rol
from utils.error_handler import respuesta_error


pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/pedidos')
service = PedidosService()

# =========================
# OBTENER PEDIDOS POR ROL
# =========================

@pedidos_bp.route('', methods=['GET'])
@requiere_autenticacion
def obtener_pedidos():
    """Obtiene pedidos según el rol del usuario"""

    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return respuesta_error("Token requerido", 401)

    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return respuesta_error("Formato de token inválido", 401)

    payload = verificar_jwt(token)

    if not payload:
        return respuesta_error("Token inválido", 401)

    rol_usuario = payload.get("rol")

    if not rol_usuario:
        return respuesta_error("Rol no encontrado en el token", 403)

    pedidos = service.obtener_por_rol(rol_usuario)

    return jsonify(pedidos), 200


# =========================
# OBTENER PEDIDO POR ID
# =========================

@pedidos_bp.route('/<uuid:id>', methods=['GET'])
@requiere_autenticacion
def obtener_pedido(id):

    resultado = service.obtener_por_id(str(id))

    if not resultado:
        return respuesta_error("Pedido no encontrado", 404)

    return jsonify(resultado), 200

# =========================
# CREAR PEDIDO
# =========================
@pedidos_bp.route('', methods=['POST'])
@requiere_rol(["oficina", "admin"])
def crear_pedido():
    """Crea un nuevo pedido con PDF y extrae datos automáticamente"""

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return respuesta_error("Token requerido", 401)

    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return respuesta_error("Formato de token inválido", 401)

    payload = verificar_jwt(token)

    if not payload:
        return respuesta_error("Token inválido", 401)

    if payload.get("rol") not in ("oficina", "admin"):
        return respuesta_error("No autorizado", 403)

    # DEBUG: Ver qué se está recibiendo
    print(f"[DEBUG] request.form keys: {list(request.form.keys())}")
    print(f"[DEBUG] request.files keys: {list(request.files.keys())}")
    
    # Campos requeridos
    cliente_nombre = request.form.get("cliente_nombre", "").strip()
    archivo_pdf = request.files.get("pdf")
    
    print(f"[DEBUG] cliente_nombre: {cliente_nombre}")
    print(f"[DEBUG] archivo_pdf: {archivo_pdf is not None}")

    if not cliente_nombre:
        return respuesta_error("cliente_nombre es requerido", 400)
    
    if not archivo_pdf:
        return respuesta_error("PDF es requerido", 400)

    # Extraer usuario_responsable_id del JWT
    usuario_responsable_id = payload.get("user_id")
    if not usuario_responsable_id:
        return jsonify({"error": "No se pudo obtener el ID del usuario del token"}), 401
    
    # Crear el pedido con solo estos datos; OCR extraerá el resto
    resultado = service.crear_con_pdf(
        cliente_nombre=cliente_nombre,
        usuario_responsable_id=usuario_responsable_id,
        archivo_pdf=archivo_pdf
    )

    if "error" in resultado:
        return jsonify(resultado), 400

    return jsonify(resultado), 201

# @pedidos_bp.route('', methods=['POST'])
# def crear_pedido():
#     """Crea un nuevo pedido"""

#     auth_header = request.headers.get("Authorization")

#     if not auth_header:
#         return jsonify({"error": "Token requerido"}), 401

#     try:
#         token = auth_header.split(" ")[1]
#     except IndexError:
#         return jsonify({"error": "Formato de token inválido"}), 401

#     payload = verificar_jwt(token)

#     if not payload:
#         return jsonify({"error": "Token inválido"}), 401

#     # Opcional: solo oficina puede crear pedidos
#     if payload.get("rol") != "oficina":
#         return jsonify({"error": "No autorizado"}), 403

#     datos = request.get_json()

#     pedido = service.crear(datos)

#     return jsonify(pedido), 201



# =========================
# ACTUALIZAR ESTADO PEDIDO
# =========================

@pedidos_bp.route('/<uuid:id>/estado', methods=['PATCH'])
@requiere_autenticacion
def actualizar_estado_pedido(id):

    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return respuesta_error("Token requerido", 401)

    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return respuesta_error("Formato de token inválido", 401)

    payload = verificar_jwt(token)

    if not payload:
        return respuesta_error("Token inválido", 401)

    rol_usuario = payload.get("rol")

    resultado = service.actualizar_estado(str(id), rol_usuario)

    if "error" in resultado:
        return respuesta_error(resultado["error"], 400)

    return jsonify(resultado), 200


# =========================
# RETROCEDER ESTADO PEDIDO
# =========================

@pedidos_bp.route('/<uuid:id>/estado/retroceder', methods=['PATCH'])
@requiere_autenticacion
def retroceder_estado_pedido(id):

    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return respuesta_error("Token requerido", 401)

    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return respuesta_error("Formato de token inválido", 401)

    payload = verificar_jwt(token)

    if not payload:
        return respuesta_error("Token inválido", 401)

    rol_usuario = payload.get("rol")

    resultado = service.retroceder_estado(str(id), rol_usuario)

    if "error" in resultado:
        return respuesta_error(resultado["error"], 400)

    return jsonify(resultado), 200


# =========================
# OBTENER PDF
# =========================

@pedidos_bp.route('/<uuid:id>/pdf', methods=['GET'])
def obtener_pdf(id):

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return respuesta_error("Token requerido", 401)

    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        return respuesta_error("Formato de token inválido", 401)

    payload = verificar_jwt(token)

    if not payload:
        return respuesta_error("Token inválido", 401)

    resultado = service.obtener_pdf_firmado(str(id))

    if "error" in resultado:
        return respuesta_error(resultado["error"], 404)

    return jsonify(resultado), 200

# =========================
# ELIMINAR PEDIDO
# =========================

@pedidos_bp.route('/<uuid:id>', methods=['DELETE'])
@requiere_rol(["oficina", "admin"])
def eliminar_pedido(id):
    resultado = service.eliminar_pedido(str(id))

    if isinstance(resultado, dict) and "error" in resultado:
        return respuesta_error(resultado["error"], 400)

    return jsonify({"message": "Pedido eliminado correctamente"}), 200


@pedidos_bp.route('/<uuid:id>/export/excel', methods=['GET'])
# oficina y admin pueden exportar
@requiere_rol(["oficina", "admin"])
def exportar_pedido_excel(id):
    archivo_excel = service.exportar_a_excel(str(id))
    
    return send_file(
        archivo_excel,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'pedido_{id}.xlsx'
    )