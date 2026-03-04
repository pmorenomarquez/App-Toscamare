import { useState, useEffect, useContext } from "react";
import { AppContext } from "@/context/AppContext";
import { ROLES, ESTADOS } from "@/config/constants";
import { formatDateTime } from "@/utils/helpers";
import { Modal, Badge, SVG } from "@/components/ui";
import ProductosTable from "./ProductosTable";
import * as api from "@/utils/api";

export default function PedidoDetailModal({
  open,
  onClose,
  pedido,
  onRefresh,
}) {
  const { session } = useContext(AppContext);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [loadingPdf, setLoadingPdf] = useState(false);

  useEffect(() => {
    if (pedido && pedido.pdf_ruta) {
      setLoadingPdf(true);
      api
        .getPDFSignedUrl(pedido.id)
        .then((url) => setPdfUrl(url))
        .catch(() => setPdfUrl(null))
        .finally(() => setLoadingPdf(false));
    } else {
      setPdfUrl(null);
    }
  }, [pedido]);

  if (!pedido) return null;
  const est = ESTADOS[pedido.estado_actual];

  const rol = session.user.rol;
  const isModerator = rol === ROLES.ADMIN || rol === ROLES.OFICINA;

  // Edit quantities: almacen at estado 0, or admin/oficina at any state up to 2
  const canEditProducts =
    (pedido.estado_actual === 0 && (rol === ROLES.ALMACEN || isModerator)) ||
    (isModerator && pedido.estado_actual <= 2);

  // Add/delete products: oficina, almacen, logistica, admin
  const canManageProducts = [
    ROLES.OFICINA,
    ROLES.ALMACEN,
    ROLES.LOGISTICA,
    ROLES.ADMIN,
  ].includes(rol);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={"Detalle — " + pedido.codigo}
      wide
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div>
          <div style={{ display: "flex", gap: 10, marginBottom: 18 }}>
            <Badge color={est.color} bg={est.bg} border={est.borderColor}>
              {est.label}
            </Badge>
          </div>
          <div style={{ marginBottom: 14 }}>
            <span
              style={{
                fontSize: 11,
                color: "var(--text-4)",
                textTransform: "uppercase",
                letterSpacing: ".04em",
              }}
            >
              Cliente
            </span>
            <p
              style={{
                fontSize: 15,
                fontWeight: 500,
                color: "var(--text-1)",
                marginTop: 2,
              }}
            >
              {pedido.cliente}
            </p>
          </div>

          {/* Productos */}
          <div style={{ marginTop: 16 }}>
            <span
              style={{
                fontSize: 11,
                color: "var(--text-4)",
                textTransform: "uppercase",
                letterSpacing: ".04em",
                display: "block",
                marginBottom: 8,
              }}
            >
              Productos
            </span>
            <ProductosTable
              pedidoId={pedido.id}
              editable={canEditProducts}
              canManage={canManageProducts}
            />
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div
            style={{
              padding: 16,
              background: "var(--bg-1)",
              borderRadius: "var(--r2)",
              border: "1px solid var(--border-1)",
            }}
          >
            <span
              style={{
                fontSize: 11,
                color: "var(--text-4)",
                textTransform: "uppercase",
                letterSpacing: ".04em",
                display: "block",
                marginBottom: 10,
              }}
            >
              Información
            </span>
            {[
              ["Creado", formatDateTime(pedido.fecha_creacion)],
              ["Actualizado", formatDateTime(pedido.fecha_actualizacion)],
              ["PDF", pedido.pdf_ruta ? "Disponible" : "Sin PDF"],
            ].map(([k, v]) => (
              <div
                key={k}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: 13,
                  marginBottom: 6,
                }}
              >
                <span style={{ color: "var(--text-4)" }}>{k}</span>
                {k === "PDF" && pdfUrl ? (
                  <a
                    href={pdfUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: "var(--accent)",
                      fontSize: 12,
                      textDecoration: "none",
                    }}
                  >
                    {loadingPdf ? "Cargando..." : "Ver PDF"}
                  </a>
                ) : (
                  <span
                    style={{
                      color: "var(--text-2)",
                      fontFamily: k === "PDF" ? "var(--mono)" : "inherit",
                      fontSize: k === "PDF" ? 12 : 13,
                    }}
                  >
                    {v}
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Progress stepper */}
          <div
            style={{
              padding: 16,
              background: "var(--bg-1)",
              borderRadius: "var(--r2)",
              border: "1px solid var(--border-1)",
            }}
          >
            <span
              style={{
                fontSize: 11,
                color: "var(--text-4)",
                textTransform: "uppercase",
                letterSpacing: ".04em",
                display: "block",
                marginBottom: 12,
              }}
            >
              Progreso
            </span>
            <div style={{ display: "flex", alignItems: "center" }}>
              {Object.entries(ESTADOS).map(([k, v], i, arr) => {
                const done = pedido.estado_actual > parseInt(k);
                const current = pedido.estado_actual === parseInt(k);
                return (
                  <div
                    key={k}
                    style={{ flex: 1, display: "flex", alignItems: "center" }}
                  >
                    <div
                      style={{
                        width: 22,
                        height: 22,
                        borderRadius: "50%",
                        flexShrink: 0,
                        background: done
                          ? v.color
                          : current
                            ? v.color + "30"
                            : "var(--bg-3)",
                        border: current
                          ? "2px solid " + v.color
                          : done
                            ? "none"
                            : "1px solid var(--border-2)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {done && <SVG name="check" size={12} color="#0A0C10" />}
                      {current && (
                        <span
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: "50%",
                            background: v.color,
                          }}
                        />
                      )}
                    </div>
                    {i < arr.length - 1 && (
                      <div
                        style={{
                          flex: 1,
                          height: 2,
                          background: done ? v.color : "var(--border-2)",
                          margin: "0 2px",
                        }}
                      />
                    )}
                  </div>
                );
              })}
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: 8,
              }}
            >
              {Object.entries(ESTADOS).map(([k, v]) => (
                <span
                  key={k}
                  style={{
                    fontSize: 9,
                    color:
                      pedido.estado_actual >= parseInt(k)
                        ? v.color
                        : "var(--text-4)",
                    textAlign: "center",
                    flex: 1,
                  }}
                >
                  {v.label.split(" ")[1] || v.label.split(" ")[0]}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}
