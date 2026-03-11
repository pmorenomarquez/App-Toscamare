from flask import Blueprint, jsonify, request
from usuarios.usuarios_service import UsuariosService
from auth.jwt_handler import requiere_admin
from utils.error_handler import respuesta_error
from utils.validators import validar_email, validar_rol

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/api/usuarios')
service = UsuariosService()

@usuarios_bp.route('', methods=['GET'])
@requiere_admin
def listar_usuarios():
    result = service.get_all_usuarios()
    if result['error']:
        return respuesta_error(result['error'], 500)
    return jsonify({"usuarios": result['data']}), 200

@usuarios_bp.route('/<usuario_id>', methods=['GET'])
@requiere_admin
def obtener_usuario(usuario_id):
    result = service.get_usuario_by_id(usuario_id)
    if result['error']:
        return respuesta_error(result['error'], 500)
    return jsonify({"usuario": result['data']}), 200

@usuarios_bp.route('', methods=['POST'])
@requiere_admin
def crear_usuario():
    data = request.json
    if not data or not data.get('email') or not data.get('nombre') or not data.get('rol'):
        return respuesta_error("Faltan campos: email, nombre, rol", 400)
    
    if not validar_email(data.get('email')):
        return respuesta_error("Email inválido", 400)
    
    if not validar_rol(data.get('rol')):
        return respuesta_error("Rol inválido", 400)
    
    result = service.create_usuario(
        data.get('email'),
        data.get('nombre'),
        data.get('rol')
    )
    if result['error']:
        return respuesta_error(result['error'], 400)
    
    return jsonify({"usuario": result['data']}), 201

@usuarios_bp.route('/<usuario_id>', methods=['PUT'])
@requiere_admin
def update_usuario(usuario_id):
    data = request.json
    if not data :
        return respuesta_error("No hay datos para actualizar", 400)
    
    if data.get('email') and not validar_email(data.get('email')):
        return respuesta_error("Email inválido", 400)
    
    if data.get('rol') and not validar_rol(data.get('rol')):
        return respuesta_error("Rol inválido", 400)
    
    result = service.update_usuario(
        usuario_id,
        data.get('email'),
        data.get('nombre'),
        data.get('rol')
    )
    
    if result['error']:
        return respuesta_error(result['error'], 400)
    
    return jsonify({"usuario": result['data']}), 200

@usuarios_bp.route('/<usuario_id>', methods=['DELETE'])
@requiere_admin
def delete_usuario(usuario_id):
    result = service.delete_usuario(usuario_id)
    if result['error']:
        return respuesta_error(result['error'], 400)
    return jsonify({"mensaje": "Usuario eliminado"}), 200