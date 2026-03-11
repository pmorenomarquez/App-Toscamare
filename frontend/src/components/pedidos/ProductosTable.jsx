import { useState, useEffect, useContext } from "react";
import { AppContext } from "@/context/AppContext";
import { Btn } from "@/components/ui";
import * as api from "@/utils/api";

export default function ProductosTable({ pedidoId, editable, canManage }) {
  const { showToast } = useContext(AppContext);
  const [productos, setProductos] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editVal, setEditVal] = useState("");
  const [adding, setAdding] = useState(false);
  const [newNombre, setNewNombre] = useState("");
  const [newCantidad, setNewCantidad] = useState("");

  useEffect(() => {
    if (pedidoId)
      api
        .fetchProductos(pedidoId)
        .then(setProductos)
        .catch(() => {});
  }, [pedidoId]);

  const startEdit = (prod) => {
    setEditingId(prod.id);
    setEditVal(prod.cantidad ?? "");
  };

  const saveEdit = async (prod) => {
    try {
      // 1. Enviamos la actualización
      await api.updateProducto(prod.id, {
        nombre_producto: prod.nombre_producto,
        cantidad: Number(editVal),
        // precio: prod.precio // Asegúrate de mantener el precio si es necesario
      });

      // 2. En lugar de actualizar el estado a mano con .map,
      // volvemos a llamar a la API para tener los datos reales de la DB
      const productosActualizados = await api.fetchProductos(pedidoId);
      setProductos(productosActualizados);

      setEditingId(null);
      showToast("Cantidad actualizada");
    } catch (e) {
      console.error("Error guardando:", e);
      showToast(e.message, "error");
    }
  };

  const handleAdd = async () => {
    if (!newNombre.trim() || !newCantidad) {
      showToast("Completa nombre y cantidad", "error");
      return;
    }
    try {
      const result = await api.addProducto(
        pedidoId,
        newNombre.trim(),
        Number(newCantidad),
      );
      // Backend returns array with inserted row
      const newProd = Array.isArray(result) ? result[0] : result;
      setProductos((prev) => [...prev, newProd]);
      setNewNombre("");
      setNewCantidad("");
      setAdding(false);
      showToast("Producto añadido");
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  const handleDelete = async (prod) => {
    try {
      await api.deleteProducto(prod.id);
      setProductos((prev) => prev.filter((p) => p.id !== prod.id));
      showToast("Producto eliminado");
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  const inputStyle = {
    width: "100%",
    padding: "6px 8px",
    background: "var(--bg-2)",
    border: "1px solid var(--border-2)",
    borderRadius: 4,
    color: "var(--text-1)",
    fontSize: 13,
  };

  if (productos.length === 0 && !adding) {
    return (
      <div>
        <p style={{ fontSize: 12, color: "var(--text-4)", marginBottom: 8 }}>
          Sin productos
        </p>
        {canManage && (
          <Btn
            variant="secondary"
            size="sm"
            icon="plus"
            onClick={() => setAdding(true)}
          >
            Añadir producto
          </Btn>
        )}
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          background: "var(--bg-1)",
          border: "1px solid var(--border-1)",
          borderRadius: "var(--r2)",
          overflow: "hidden",
        }}
      >
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {[
                "Producto",
                "Cantidad (kg)",
                ...(editable || canManage ? [""] : []),
              ].map((h) => (
                <th
                  key={h}
                  style={{
                    padding: "8px 12px",
                    textAlign: "left",
                    fontSize: 10,
                    fontWeight: 600,
                    color: "var(--text-4)",
                    textTransform: "uppercase",
                    letterSpacing: ".04em",
                    borderBottom: "1px solid var(--border-1)",
                    background: "var(--bg-0)",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {productos.map((p, i) => (
              <tr
                key={p.id}
                style={{
                  borderBottom:
                    i < productos.length - 1
                      ? "1px solid var(--border-1)"
                      : "none",
                }}
              >
                <td
                  style={{ padding: "8px 12px", fontSize: 13, fontWeight: 500 }}
                >
                  {p.nombre_producto}
                </td>
                <td style={{ padding: "8px 12px", fontSize: 13 }}>
                  {editingId === p.id ? (
                    <input
                      type="number"
                      value={editVal}
                      onChange={(e) => setEditVal(e.target.value)}
                      min="0"
                      step="0.01"
                      autoFocus
                      style={{
                        ...inputStyle,
                        width: 80,
                        borderColor: "var(--accent)",
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") saveEdit(p);
                        if (e.key === "Escape") setEditingId(null);
                      }}
                    />
                  ) : (
                    <span>{p.cantidad ?? "—"}</span>
                  )}
                </td>
                {(editable || canManage) && (
                  <td style={{ padding: "8px 12px", width: 100 }}>
                    <div style={{ display: "flex", gap: 4 }}>
                      {editable &&
                        (editingId === p.id ? (
                          <>
                            <Btn
                              variant="primary"
                              size="sm"
                              icon="check"
                              onClick={() => saveEdit(p)}
                            />
                            <Btn
                              variant="ghost"
                              size="sm"
                              icon="x"
                              onClick={() => setEditingId(null)}
                            />
                          </>
                        ) : (
                          <Btn
                            variant="ghost"
                            size="sm"
                            icon="edit"
                            onClick={() => startEdit(p)}
                          />
                        ))}
                      {canManage && (
                        <Btn
                          variant="ghost"
                          size="sm"
                          icon="trash"
                          danger
                          onClick={() => handleDelete(p)}
                        />
                      )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {/* Inline add row */}
            {adding && (
              <tr style={{ borderTop: "1px solid var(--border-1)" }}>
                <td style={{ padding: "6px 8px" }}>
                  <input
                    value={newNombre}
                    onChange={(e) => setNewNombre(e.target.value)}
                    placeholder="Nombre del producto"
                    style={inputStyle}
                    autoFocus
                  />
                </td>
                <td style={{ padding: "6px 8px" }}>
                  <input
                    type="number"
                    value={newCantidad}
                    onChange={(e) => setNewCantidad(e.target.value)}
                    placeholder="0"
                    min="0"
                    step="0.01"
                    style={{ ...inputStyle, width: 80 }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleAdd();
                    }}
                  />
                </td>
                <td style={{ padding: "6px 8px" }}>
                  <div style={{ display: "flex", gap: 4 }}>
                    <Btn
                      variant="primary"
                      size="sm"
                      icon="check"
                      onClick={handleAdd}
                    />
                    <Btn
                      variant="ghost"
                      size="sm"
                      icon="x"
                      onClick={() => {
                        setAdding(false);
                        setNewNombre("");
                        setNewCantidad("");
                      }}
                    />
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {canManage && !adding && (
        <Btn
          variant="secondary"
          size="sm"
          icon="plus"
          onClick={() => setAdding(true)}
          style={{ marginTop: 8 }}
        >
          Añadir producto
        </Btn>
      )}
    </div>
  );
}
