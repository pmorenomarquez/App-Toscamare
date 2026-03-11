# supabase_admin_client.py
# Este cliente de Supabase utiliza la clave de servicio (service role key) para tener permisos de administrador.
# Se usa para operaciones que requieren permisos elevados, como subir archivos a Storage o modificar datos sensibles.

from supabase import create_client
from config import Config

supabase_admin = create_client(
    Config.SUPABASE_URL,
    Config.SUPABASE_SERVICE_ROLE_KEY
)