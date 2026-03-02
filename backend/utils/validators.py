def validar_email(email):
    if not email or '@' not in email:
        return False
    
    partes = email.split('@')
    if len(partes) != 2 or not partes[1]:
        return False
    
    return True

def validar_rol(rol):
    roles_validos = ['admin', 'oficina', 'logistica', 'almacen', 'transportista']
    if rol not in roles_validos:
        return False
    
    return True

def validar_cantidad(cantidad):
    try:
        cantidad_num = float(cantidad)
        return cantidad_num > 0
    except (ValueError, TypeError):
        return False