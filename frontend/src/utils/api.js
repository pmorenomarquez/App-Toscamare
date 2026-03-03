// ═══════════════════════════════════════════════════════════════
// API Layer — Conecta con el backend Flask
//
// Auth flow:
//   1. Frontend redirige a GET /api/login → Microsoft OAuth
//   2. Backend callback genera JWT, redirige a FRONTEND?token=JWT
//   3. Frontend captura token de URL, lo guarda en localStorage
//   4. POST /api/verify-token valida el JWT
// ═══════════════════════════════════════════════════════════════

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";
const API_BASE = BACKEND_URL + "/api";

// ── Token management ─────────────────────────────────────────

export function getStoredToken() {
  return localStorage.getItem("jwt");
}

function setStoredToken(token) {
  localStorage.setItem("jwt", token);
}

export function clearToken() {
  localStorage.removeItem("jwt");
  localStorage.removeItem("user");
}

function headers(extra = {}) {
  const h = { ...extra };
  const token = getStoredToken();
  if (token) h["Authorization"] = "Bearer " + token;
  return h;
}

// ── Base request ─────────────────────────────────────────────

async function request(path, opts = {}) {
  const res = await fetch(API_BASE + path, {
    ...opts,
    headers: headers(opts.headers || {}),
  });

  if (res.status === 401) {
    clearToken();
    window.location.reload();
    throw new Error("Sesión expirada");
  }

  if (!res.ok) {
    const err = await res
      .json()
      .catch(() => ({ detail: "Error del servidor" }));
    throw new Error(err.detail || err.error || "Error");
  }

  // Handle Excel blob responses
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("spreadsheetml") || ct.includes("octet-stream")) {
    return res;
  }

  return res.json();
}

// ── Normalizers ──────────────────────────────────────────────

function normalizePedido(p) {
  return {
    ...p,
    id: p.id,
    codigo: p.id
      ? "PED-" + String(p.id).slice(0, 8).toUpperCase()
      : "PED-SIN-ID",
    cliente: p.cliente_nombre || "",
    estado_actual:
      typeof p.estado === "number" ? p.estado : parseInt(p.estado, 10) || 0,
    pdf_ruta: p.pdf_url || null,
    // DB uses fecha_creacion/fecha_actualizacion (not created_at/updated_at)
    fecha_creacion: p.fecha_creacion || p.created_at || null,
    fecha_actualizacion: p.fecha_actualizacion || p.fecha_creacion || null,
  };
}

// ── Auth (Microsoft OAuth via Flask backend) ─────────────────

export function loginMicrosoft() {
  window.location.href = API_BASE + "/login";
}

export async function verifyToken(token) {
  const res = await fetch(API_BASE + "/verify-token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });

  const data = await res.json();

  if (!data.valid) {
    clearToken();
    throw new Error("Token inválido");
  }

  const user = data.user;
  if (user.user_id && !user.id) {
    user.id = user.user_id;
  }

  return user;
}

export async function handleOAuthCallback(token) {
  setStoredToken(token);
  const user = await verifyToken(token);
  localStorage.setItem("user", JSON.stringify(user));
  return user;
}

export async function restoreSession() {
  const token = getStoredToken();
  if (!token) return null;

  try {
    const user = await verifyToken(token);
    localStorage.setItem("user", JSON.stringify(user));
    return user;
  } catch {
    clearToken();
    return null;
  }
}

export function logout() {
  clearToken();
}

// ── Pedidos ──────────────────────────────────────────────────

export function fetchPedidos() {
  return request("/pedidos").then((data) =>
    Array.isArray(data) ? data.map(normalizePedido) : data,
  );
}

export function createPedido(clienteNombre, pdfFile) {
  const formData = new FormData();
  formData.append("cliente_nombre", clienteNombre);
  formData.append("pdf", pdfFile);
  return request("/pedidos", {
    method: "POST",
    body: formData,
    // No Content-Type header — browser sets multipart boundary automatically
  });
}

export function advancePedido(id) {
  return request("/pedidos/" + id + "/estado", { method: "PATCH" });
}

export function rollbackPedido(id) {
  return request('/pedidos/' + id + '/estado/retroceder', { method: 'PATCH' });
}

export async function exportExcel(id) {
  const res = await fetch(API_BASE + "/pedidos/" + id + "/export/excel", {
    headers: headers(),
  });
  if (!res.ok) throw new Error("Error al exportar");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "pedido_" + id + ".xlsx";
  a.click();
  URL.revokeObjectURL(url);
}

// ── PDF ──────────────────────────────────────────────────────

export async function getPDFSignedUrl(pedidoId) {
  const data = await request("/pedidos/" + pedidoId + "/pdf");
  // Backend returns { path, signedURL } or { signedUrl }
  return data.signedURL || data.signedUrl || data.signed_url || null;
}

// ── Productos ────────────────────────────────────────────────

export function fetchProductos(pedidoId) {
  return request("/pedidos/" + pedidoId + "/productos");
}

export function addProducto(pedidoId, nombreProducto, cantidad) {
  return request("/pedido-productos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pedido_id: pedidoId,
      nombre_producto: nombreProducto,
      cantidad: cantidad,
    }),
  });
}

export function updateProducto(productoId, data) {
  return request("/pedido-productos/" + productoId, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function deleteProducto(productoId) {
  return request("/pedido-productos/" + productoId, { method: "DELETE" });
}

// ── Usuarios ─────────────────────────────────────────────────

export function fetchUsuarios() {
  return request("/usuarios").then((data) => data.usuarios || data);
}

export function createUsuario(data) {
  return request("/usuarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: data.email,
      nombre: data.nombre,
      rol: data.rol,
    }),
  });
}

export function updateUsuario(id, data) {
  return request("/usuarios/" + id, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
