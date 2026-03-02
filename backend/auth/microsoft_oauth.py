from flask import Flask, redirect, url_for, session, request, render_template
import requests
import os
from config import Config

def iniciar_login():
    # Redirige al usuario a Microsoft para que se loguee
    # URL que apunta a Microsoft
    
    microsoft_auth_url = f"https://login.microsoftonline.com/{Config.TENANT_ID}/oauth2/v2.0/authorize"
    params = {
        'client_id': Config.CLIENT_ID,
        'redirect_uri': Config.REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid profile email User.Read',
        'prompt': 'select_account'
    }
    
    auth_url = f"{microsoft_auth_url}?client_id={params['client_id']}&redirect_uri={params['redirect_uri']}&response_type={params['response_type']}&scope={params['scope']}&prompt={params['prompt']}"
    return redirect(auth_url)


def manejar_callback():
    # 1. Obtener el código que Microsoft nos envió
    code = request.args.get('code')
    
    if not code:
        return "Error: codigo no recibido"
    
    # 2. Intercambiar el código por un token
    token_url = f"https://login.microsoftonline.com/{Config.TENANT_ID}/oauth2/v2.0/token"
    
    data = {
        'client_id': Config.CLIENT_ID,
        'client_secret': Config.CLIENT_SECRET,
        'code': code,
        'redirect_uri': Config.REDIRECT_URI,
        'grant_type': 'authorization_code',
        'scope': 'openid profile email User.Read'
    }
    
    response = requests.post(token_url, data=data)
    token_data = response.json()
    
    print("TOKEN RESPONSE:", token_data)
    
    if 'access_token' not in token_data:
        return 'Error: could not get token', 400
    
    access_token = token_data['access_token']
    
    # 3. Obtener datos del usuario
    user_info_url = "https://graph.microsoft.com/v1.0/me"
    headers = {'Authorization': f'Bearer {access_token}'}
    
    user_response = requests.get(user_info_url, headers=headers)
    user_data = user_response.json()
    
    email = user_data.get('mail') or user_data.get('userPrincipalName')
    nombre = user_data.get('displayName')
    
    return {
        'email': email,
        'nombre': nombre,
        'microsoft_data': user_data
    }
