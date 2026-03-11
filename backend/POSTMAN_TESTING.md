# Pruebas de Pedidos con Postman

## Crear Pedido con PDF (OCR Automático)

### Request Details
- **Method**: POST
- **URL**: `http://localhost:5000/api/pedidos/`
- **Header**: Authorization: Bearer [JWT_TOKEN]

### Body (Form-data)
Enviar SOLO estos campos como `multipart/form-data`:

| Key | Value | Type |
|-----|-------|------|
| cliente_nombre | Nombre del cliente | text |
| pdf | [seleccionar archivo PDF] | file |

### Paso a Paso en Postman:

1. **New Request** → POST
2. **URL**: `http://localhost:5000/api/pedidos/`
3. **Headers**:
   - Key: `Authorization`
   - Value: `Bearer [tu_jwt_token]`

4. **Body** → Selecciona `form-data`:
   - `cliente_nombre` (text) → "Mi Cliente"
   - `pdf` (file) → [SELECCIONA TU ARCHIVO PDF] ⬅️ **IMPORTANTE: tipo FILE**

5. **Send**

### Expected Response (201):
```json
{
  "id": "uuid-del-pedido",
  "cliente_nombre": "Mi Cliente",
  "estado": 0,
  "usuario_responsable_id": "user-id",
  "pdf_url": "uuid-del-pedido.pdf"
}
```

### Que Sucede Automáticamente:
1. ✅ Se crea el pedido en la BD
2. ✅ Se sube el PDF a Supabase Storage
3. ✅ Se convierte PDF a imágenes
4. ✅ Se ejecuta OCR en las imágenes
5. ✅ Se extraen productos del albarán
6. ✅ Se insertan los productos en `pedido_productos`

### Debugging
Mira los logs en la consola del servidor:

```
[CREATE_PEDIDO] Iniciando creación de pedido
[CREATE_PEDIDO] cliente_nombre: Mi Cliente
[CREATE_PEDIDO] PDF subido a Supabase Storage
[CREATE_PEDIDO] Pedido creado en BD: [id]
[OCR] Iniciando procesamiento OCR para pedido [id]
[OCR] imágenes generadas: 1
[OCR] productos extraidos: 5
[OCR] Producto insertado: MANZANA - 10 cajas
[OCR] Producto insertado: PERA - 5 cajas
...
```

### Notas Importantes:
- ⚠️ Body DEBE ser `form-data`, NO JSON
- ⚠️ El PDF DEBE ser tipo `file`, no texto
- ⚠️ Authorization header es OBLIGATORIO
- ⚠️ El rol del token DEBE ser "oficina"
- ✅ Los datos (dirección, productos) se extraen automáticamente del PDF


