from jose import jwt, JWTError
from datetime import datetime, timedelta
from config import Config
from functools import wraps
from flask import jsonify, request
from utils.error_handler import respuesta_error

def generar_jwt(user_data):
    """
    Genera un JWT con los datos del usuario
    """
    expiration = datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    
    payload = {
        'user_id': user_data['id'],
        'email': user_data['email'],
        'nombre': user_data['nombre'],
        'rol': user_data['rol'],
        'exp': expiration
    }
    
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
    return token


def verificar_jwt(token):
    """Verifica si un JWT es válido y devuelve los datos"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
    
def requiere_admin(funcion):
    @wraps(funcion)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        try:
            auth_token = token.split(' ')[1]
        except:
            return respuesta_error("Formato de token no válido", 401)
        
        if not auth_token:
            return respuesta_error("Token no proporcionado", 401)
        
        payload = verificar_jwt(auth_token)
        
        if not payload:
            return respuesta_error("Token inválido", 401)
        
        if payload['rol'] == 'admin':
            return funcion(*args, **kwargs)
        else:
            return respuesta_error("No tienes permisos", 403)
    
    return wrapper
        
def requiere_autenticacion(funcion):
    @wraps(funcion)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        try:
            auth_token = token.split(' ')[1]
        except:
            return respuesta_error("Formato de token no válido", 401)
        
        if not auth_token:
            return respuesta_error("Token no proporcionado", 401)
        
        payload = verificar_jwt(auth_token)
        
        if not payload:
            return respuesta_error("Token inválido", 401)
        
        return funcion(*args, **kwargs)
        
    return wrapper

def requiere_rol(roles_permitidos):
    if isinstance(roles_permitidos, str):
        roles_permitidos=[roles_permitidos]
        
    def decorator(funcion):
        @wraps(funcion)
        def wrapper(*args, **kwargs):
            token = request.headers.get('Authorization')
            
            try:
                auth_token = token.split(' ')[1]
            except:
                return respuesta_error("Formato de token no válido", 401)
            
            if not auth_token:
                return respuesta_error("Token no proporcionado", 401)
            
            payload = verificar_jwt(auth_token)
            
            if not payload:
                return respuesta_error("Token inválido", 401)
            
            if payload.get('rol') in roles_permitidos:
                return funcion(*args, **kwargs)
            else:
                return respuesta_error("No tienes permisos para acceder a esta URL", 403)
            
        return wrapper
    return decorator
        
        