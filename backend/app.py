from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
from config import Config
from auth.microsoft_oauth import iniciar_login, manejar_callback
from auth.jwt_handler import generar_jwt, verificar_jwt
from database.supabase_client import supabase
from usuarios.usuarios import usuarios_bp
from pedidos.pedidos import pedidos_bp
from productos.productos import productos_bp
from utils.error_handler import register_error_handlers, respuesta_error


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max (firmas + PDFs)
register_error_handlers(app)
CORS(app, origins=[Config.FRONTEND_URL])

app.register_blueprint(usuarios_bp)
app.register_blueprint(pedidos_bp)
app.register_blueprint(productos_bp)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}),200

@app.route('/api/login', methods=['GET'])
def login():
    return iniciar_login()

@app.route('/api/callback', methods=['GET'])
def callback():
    result = manejar_callback()
    
    if 'error' in result:
        return respuesta_error(result['error'], 400)
    
    response = supabase.table('usuarios').select('*').eq('email', result['email']).execute()
    
    if not response.data or len(response.data) == 0:
        return respuesta_error("Usuario no registrado", 403)
    
    usuario=response.data[0]
    
    token = generar_jwt(usuario)
    
    return redirect(f"{Config.FRONTEND_URL}?token={token}")

@app.route('/api/verify-token', methods=['POST'])
def verify_token():
    data = request.json
    token = data.get('token')
    
    if not token:
        return respuesta_error("Token no proporcionado", 400)
    
    payload = verificar_jwt(token)
    
    if not payload:
        return jsonify({"valid": False}), 401
    
    return jsonify({"valid": True, "user": payload}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)