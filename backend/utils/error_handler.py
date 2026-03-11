from flask import jsonify
from werkzeug.exceptions import HTTPException

def respuesta_error(error, codigo=400):
    return jsonify({
        "success": False,
        "error": error,
        "mensaje": error
    }), codigo

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return respuesta_error("Petición inválida", 400)
    
    @app.errorhandler(401)
    def unauthorized(error):
        return respuesta_error("No autenticado", 401)
    
    @app.errorhandler(403)
    def forbidden(error):
        return respuesta_error("No autorizado", 403)
    
    @app.errorhandler(404)
    def not_found(error):
        return respuesta_error("Recurso no encontrado", 404)
    
    @app.errorhandler(500)
    def internal_error(error):
        return respuesta_error("Error interno del servidor", 500)