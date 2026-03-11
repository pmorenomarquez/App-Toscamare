from database.supabase_client import supabase
from datetime import datetime

class UsuariosService:

    def get_all_usuarios(self):
        try:
            response = supabase.table('usuarios').select('*').execute()
            return {"data" : response.data, "error" : None}
        except Exception as e:
            return {"data" : None, "error" : str(e)}

    def get_usuario_by_id(self, usuario_id):
        try:
            response = supabase.table('usuarios').select('*').eq('id', usuario_id).execute()
            if response.data:
                return {"data" : response.data[0], "error" : None}
            
            return {"data": None, "error": "Usuario no encontrado"}
        
        except Exception as e:
            return {"data" : None, "error" : str(e)}

    def create_usuario(self, email, nombre, rol):
        try:
            existe_email = supabase.table('usuarios').select('*').eq('email', email).execute()
        
            if existe_email.data and len(existe_email.data) > 0:
                return{"data": None, "error" : "Ya existe ese usuario"}
        
            response = supabase.table('usuarios').insert({
                "email": email,
                "nombre": nombre,
                "rol": rol
            }).execute()
        
            return {"data" : response.data[0], "error" : None}
        
        except Exception as e:
            return{"data" : None, "error": str(e)}
        
    def update_usuario(self, usuario_id, email=None, nombre=None, rol=None):
        try:
            existe_id = supabase.table('usuarios').select('*').eq('id', usuario_id).execute()
            
            if not existe_id.data:
                return {"data": None, "error": "No existe este usuario"}
            
            update_data = {}
            
            if email is not None:
                update_data['email'] = email
            if nombre is not None:
                update_data['nombre'] = nombre
            if rol is not None:
                update_data['rol'] = rol
                
            if not update_data:
                return{"data": None, "error": "No hay campos para actualizar"}
                
            response = supabase.table('usuarios').update(update_data).eq('id', usuario_id).execute()
            
            return {"data": response.data[0], "error": None}
            
        except Exception as e:
            return {"data" : None, "error": str(e)}
        
    def delete_usuario(self, usuario_id):
        try:
            existe_id = supabase.table('usuarios').select('*').eq('id', usuario_id).execute()
            
            if not existe_id.data:
                return {"data": None, "error": "No existe este usuario"}
            
            response = supabase.table('usuarios').delete().eq('id', usuario_id).execute()
            
            return {"data": response.data[0], "error": None}
            
        except Exception as e:
            return {"data": None, "error": str(e)}
        
        