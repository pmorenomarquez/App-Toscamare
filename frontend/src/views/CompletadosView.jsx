import { useState, useMemo, useContext } from "react";
import { AppContext } from "@/context/AppContext";
import { ESTADOS } from "@/config/constants";
import { timeAgo } from "@/utils/helpers";
import { SVG, Btn, Badge, EmptyState } from "@/components/ui";
import PedidoDetailModal from "@/components/pedidos/PedidoDetailModal";
import * as api from "@/utils/api";

export default function CompletadosView() {
  const { pedidos, showToast, loadPedidos } = useContext(AppContext);
  const [search, setSearch] = useState("");
  const [detailPedido, setDetailPedido] = useState(null);

  const completados = useMemo(() => {
    let list = pedidos.filter((p) => p.estado_actual === 4);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (p) =>
          p.codigo.toLowerCase().includes(q) ||
          p.cliente.toLowerCase().includes(q),
      );
    }
    return list;
  }, [pedidos, search]);

  const handleExportExcel = async (pedido) => {
    try {
      await api.exportExcel(pedido.id);
      showToast("Excel descargado");
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  const est = ESTADOS[4];

  return (
    <div style={{ padding: 28 }}>
      {/* Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 16,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div style={{ position: "relative" }}>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar pedidos completados..."
            style={{
              padding: "8px 12px 8px 34px",
              background: "var(--bg-2)",
              border: "1px solid var(--border-2)",
              borderRadius: "var(--r2)",
              color: "var(--text-1)",
              fontSize: 13,
              width: 280,
            }}
          />
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: 11,
              transform: "translateY(-50%)",
              pointerEvents: "none",
            }}
          >
            <SVG name="search" size={14} color="var(--text-4)" />
          </div>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-4)" }}>
          {completados.length} pedido{completados.length !== 1 ? "s" : ""} completado{completados.length !== 1 ? "s" : ""}
        </p>
      </div>

      {completados.length === 0 ? (
        <EmptyState
          icon="archive"
          title="Sin pedidos completados"
          subtitle={search ? "Intenta otro termino" : "Los pedidos completados aparecen aqui"}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {completados.map((p, i) => (
            <div
              key={p.id}
              className={"anim-fade d" + Math.min(i + 1, 8)}
              style={{
                background: "var(--bg-2)",
                border: "1px solid var(--border-1)",
                borderRadius: "var(--r3)",
                padding: "16px 20px",
                transition: ".15s var(--ease)",
                borderLeft: "3px solid " + est.color,
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.borderColor = "var(--border-3)")
              }
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "var(--border-1)";
                e.currentTarget.style.borderLeftColor = est.color;
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: 16,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      marginBottom: 6,
                    }}
                  >
                    <code
                      style={{
                        fontFamily: "var(--mono)",
                        fontSize: 13,
                        fontWeight: 500,
                        color: est.color,
                      }}
                    >
                      {p.codigo}
                    </code>
                    <Badge
                      color={est.color}
                      bg={est.bg}
                      border={est.borderColor}
                    >
                      {est.label}
                    </Badge>
                  </div>
                  <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 3 }}>
                    {p.cliente}
                  </p>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 14,
                      marginTop: 8,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 11,
                        color: "var(--text-4)",
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                    >
                      <SVG name="clock" size={12} color="var(--text-4)" />
                      {timeAgo(p.fecha_actualizacion)}
                    </span>
                    {p.pdf_ruta && (
                      <span
                        style={{
                          fontSize: 11,
                          color: "var(--text-4)",
                          display: "flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        <SVG name="file" size={12} color="var(--text-4)" />
                        PDF
                      </span>
                    )}
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    flexShrink: 0,
                  }}
                >
                  <Btn
                    variant="ghost"
                    size="sm"
                    icon="eye"
                    onClick={() => setDetailPedido(p)}
                  />
                  <Btn
                    variant="outline"
                    size="sm"
                    icon="download"
                    onClick={() => handleExportExcel(p)}
                  >
                    Excel
                  </Btn>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <PedidoDetailModal
        open={!!detailPedido}
        onClose={() => setDetailPedido(null)}
        pedido={detailPedido}
        onRefresh={loadPedidos}
      />
    </div>
  );
}
