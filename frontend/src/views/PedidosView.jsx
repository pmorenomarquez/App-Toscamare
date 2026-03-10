import { useState, useMemo, useContext, useEffect } from "react";
import { AppContext } from "@/context/AppContext";
import { ROLES, ROLE_META, ESTADOS } from "@/config/constants";
import { timeAgo } from "@/utils/helpers";
import { SVG, Btn, Badge, Select, EmptyState } from "@/components/ui";
import PedidoFormModal from "@/components/pedidos/PedidoFormModal";
import PedidoDetailModal from "@/components/pedidos/PedidoDetailModal";
import FirmaModal from "@/components/pedidos/FirmaModal";
import SignatureModal from "@/components/pedidos/SignatureModal";
import * as api from "@/utils/api";

export default function PedidosView() {
  const { pedidos, session, showToast, loadPedidos, adminViewAs } =
    useContext(AppContext);
  const [search, setSearch] = useState("");
  const [filterEstado, setFilterEstado] = useState("todos");
  const [showCreate, setShowCreate] = useState(false);
  const [detailPedido, setDetailPedido] = useState(null);
  const [confirmId, setConfirmId] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null); // 'advance' | 'rollback' | 'delete'
  const [actionLoading, setActionLoading] = useState(null);
  const [firmaPedido, setFirmaPedido] = useState(null);

  const userRol = session.user.rol;
  const effectiveRol = adminViewAs || userRol;
  const isAdminOriginal = userRol === ROLES.ADMIN;
  const isAdmin = effectiveRol === ROLES.ADMIN;
  const isOficina = effectiveRol === ROLES.OFICINA;
  const isModerator = isAdmin || isOficina;

  useEffect(() => {
    setFilterEstado("todos");
  }, [adminViewAs]);

  const filtered = useMemo(() => {
    // Only show active pedidos (estado 0-3), not completados (4)
    let list = pedidos.filter((p) => p.estado_actual <= 3);

    // When admin views as a specific role, filter to that role's estado
    if (adminViewAs) {
      const estadoVisible = ROLE_META[adminViewAs]?.estadoVisible;
      if (estadoVisible != null) {
        list = list.filter((p) => p.estado_actual === estadoVisible);
      }
    }

    // Moderators can further filter by estado dropdown
    if (isModerator && filterEstado !== "todos") {
      list = list.filter((p) => p.estado_actual === parseInt(filterEstado));
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (p) =>
          p.codigo.toLowerCase().includes(q) ||
          p.cliente.toLowerCase().includes(q),
      );
    }
    return list;
  }, [pedidos, filterEstado, search, isModerator, isAdmin, adminViewAs]);

  const advanceOrder = async (pedidoId) => {
    const pedido = pedidos.find((p) => p.id === pedidoId);
    if (!pedido) return;

    setActionLoading(pedidoId);
    try {
      await api.advancePedido(pedidoId);
      const nextLabel = ESTADOS[pedido.estado_actual + 1]?.label || "Completado";
      showToast(pedido.codigo + " → " + nextLabel);
      await loadPedidos();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setActionLoading(null);
      setConfirmId(null);
      setConfirmAction(null);
    }
  };

  const rollbackOrder = async (pedidoId) => {
    const pedido = pedidos.find((p) => p.id === pedidoId);
    if (!pedido) return;

    setActionLoading(pedidoId);
    try {
      await api.rollbackPedido(pedidoId);
      const prevLabel = ESTADOS[pedido.estado_actual - 1]?.label || "Anterior";
      showToast(pedido.codigo + " ← " + prevLabel);
      await loadPedidos();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setActionLoading(null);
      setConfirmId(null);
      setConfirmAction(null);
    }
  };

  const handleDelete = async (pedido) => {
    setActionLoading(pedido.id);
    try {
      await api.deletePedido(pedido.id);
      showToast(pedido.codigo + " eliminado");
      await loadPedidos();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setActionLoading(null);
      setConfirmId(null);
      setConfirmAction(null);
    }
  };

  const handleExportExcel = async (pedido) => {
    try {
      await api.exportExcel(pedido.id);
      showToast("Excel descargado");
    } catch (e) {
      showToast(e.message, "error");
    }
  };

  // Advance: admin/oficina can advance any estado, each role only their own
  const canAdvance = (p) => {
    if (isAdmin || isOficina) return true;
    return ESTADOS[p.estado_actual]?.role === effectiveRol;
  };

  // Rollback: send pedido back one estado for corrections
  const canRollback = (p) => {
    if (p.estado_actual <= 0) return false;
    if (isAdmin || isOficina) return true;
    return ESTADOS[p.estado_actual]?.role === effectiveRol;
  };

  const canSign = (p) => {
    return p.estado_actual === 2 && (effectiveRol === ROLES.TRANSPORTISTA || isModerator);
  };

  const canExport = (p) => {
    return p.estado_actual === 3 && isModerator;
  };

  const showAdvanceBtn = (p) => {
    return p.estado_actual <= 3 && canAdvance(p);
  };

  const canCreate = isModerator;

  // Function to determine if transportista is trying to confirm and has valid signature in localstorage
  const handleConfirmCarga = async (pedidoId) => {
    const firmaGuardada = localStorage.getItem('firma_' + pedidoId);
    if (!firmaGuardada) {
      showToast("Es necesario firmar antes de confirmar la carga", "error");
      return;
    }

    setActionLoading(pedidoId);
    try {
      await api.firmarPedido(pedidoId, firmaGuardada);
      localStorage.removeItem('firma_' + pedidoId);
      
      const pedido = pedidos.find(p => p.id === pedidoId);
      const nextLabel = ESTADOS[pedido.estado_actual + 1]?.label || "Completado";
      showToast(pedido.codigo + " → " + nextLabel);
      await loadPedidos();
    } catch (e) {
      showToast(e.message || "Error al completar flujo", "error");
    } finally {
      setActionLoading(null);
    }
  };

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
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div style={{ position: "relative" }}>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar pedidos..."
              style={{
                padding: "8px 12px 8px 34px",
                background: "var(--bg-2)",
                border: "1px solid var(--border-2)",
                borderRadius: "var(--r2)",
                color: "var(--text-1)",
                fontSize: 13,
                width: 240,
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
          {isModerator && !adminViewAs && (
            <Select
              value={filterEstado}
              onChange={(e) => setFilterEstado(e.target.value)}
              options={[
                { value: "todos", label: "Todos los estados" },
                ...Object.entries(ESTADOS)
                  .filter(([k]) => parseInt(k) <= 3)
                  .map(([k, v]) => ({
                    value: k,
                    label: v.label,
                  })),
              ]}
            />
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <p style={{ fontSize: 12, color: "var(--text-4)" }}>
            {filtered.length} pedido{filtered.length !== 1 ? "s" : ""}
            {isAdmin &&
              adminViewAs &&
              " — Vista: " + (ROLE_META[adminViewAs]?.label || "")}
          </p>
          {canCreate && (
            <Btn
              variant="primary"
              icon="plus"
              onClick={() => setShowCreate(true)}
            >
              Nuevo Pedido
            </Btn>
          )}
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon="check"
          title="Sin pedidos pendientes"
          subtitle={search ? "Intenta otro termino" : "Tu bandeja esta vacia"}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {filtered.map((p, i) => {
            const est = ESTADOS[p.estado_actual];
            const isConfirming = confirmId === p.id;
            const isLoading = actionLoading === p.id;
            return (
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
                    <p
                      style={{ fontSize: 14, fontWeight: 500, marginBottom: 3 }}
                    >
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
                      <span style={{
                        fontSize: 10, color: est.color, fontWeight: 500,
                        display: "flex", alignItems: "center", gap: 4,
                      }}>
                        <SVG name={ROLE_META[est.role]?.icon || "user"} size={11} color={est.color} />
                        {ROLE_META[est.role]?.label || est.role}
                      </span>
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
                      variant="outline"
                      size="sm"
                      icon="eye"
                      title="Ver detalle del pedido"
                      onClick={() => setDetailPedido(p)}
                    >
                      Ver
                    </Btn>

                    {/* Export Excel button for oficina/admin at state 3 */}
                    {canExport(p) && (
                      <Btn
                        variant="outline"
                        size="sm"
                        icon="download"
                        onClick={() => handleExportExcel(p)}
                      >
                        Descargar Excel
                      </Btn>
                    )}

                    {/* Confirmation dialog */}
                    {isConfirming ? (
                      <div style={{ display: "flex", gap: 4 }}>
                          <Btn
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setConfirmId(null);
                              setConfirmAction(null);
                                                    }}
                          >
                            Cancelar
                          </Btn>
                          <Btn
                            variant={
                              confirmAction === "delete" ? "outline"
                              : confirmAction === "rollback" ? "outline"
                              : "primary"
                            }
                            size="sm"
                            icon={
                              confirmAction === "rollback" ? "chevronL"
                              : confirmAction === "delete" ? "trash"
                              : "check"
                            }
                            danger={confirmAction === "delete"}
                            disabled={isLoading}
                            onClick={() => {
                              if (confirmAction === "rollback") rollbackOrder(p.id);
                              else if (confirmAction === "delete") handleDelete(p);
                              else advanceOrder(p.id);
                            }}
                          >
                            {isLoading ? "..." : confirmAction === "delete" ? "Eliminar" : "Confirmar"}
                          </Btn>
                      </div>
                    ) : (
                      <>
                        {/* Delete button only strictly for the original admin/oficina users */}
                        {(isAdminOriginal || session.user.rol === ROLES.OFICINA) && !adminViewAs && (
                          <Btn
                            variant="outline"
                            size="sm"
                            icon="trash"
                            title="Eliminar pedido"
                            danger
                            onClick={() => {
                              setConfirmId(p.id);
                              setConfirmAction("delete");
                            }}
                          />
                        )}

                        {/* Rollback button */}
                        {canRollback(p) && (
                          <Btn
                            variant="outline"
                            size="sm"
                            icon="chevronL"
                            onClick={() => {
                              setConfirmId(p.id);
                              setConfirmAction("rollback");
                            }}
                          >
                            Devolver
                          </Btn>
                        )}

                        {/* Transportista flow at estado 2: Sign -> Confirm */}
                        {canSign(p) && (
                          <>
                            <Btn
                              variant={localStorage.getItem('firma_' + p.id) ? "outline" : "primary"}
                              size="sm"
                              icon="edit"
                              style={localStorage.getItem('firma_' + p.id) ? { borderColor: 'var(--success)', color: 'var(--success)' } : {}}
                              onClick={() => setFirmaPedido(p)}
                            >
                              {localStorage.getItem('firma_' + p.id) ? "Ver firma" : "Firmar"}
                            </Btn>
                            <Btn
                              variant="primary"
                              size="sm"
                              icon="check"
                              disabled={!localStorage.getItem('firma_' + p.id) || isLoading}
                              onClick={() => handleConfirmCarga(p.id)}
                            >
                              {isLoading ? "..." : "Confirmar Carga"}
                            </Btn>
                          </>
                        )}

                        {/* Advance state button (hide at estado 2 if canSign) */}
                        {showAdvanceBtn(p) && !canSign(p) && (
                          <Btn
                            variant="primary"
                            size="sm"
                            icon={p.estado_actual === 3 ? "check" : "chevronR"}
                            onClick={() => {
                              setConfirmId(p.id);
                              setConfirmAction("advance");
                            }}
                          >
                            {est.action}
                          </Btn>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <PedidoFormModal open={showCreate} onClose={() => setShowCreate(false)} />
      <PedidoDetailModal
        open={!!detailPedido}
        onClose={() => setDetailPedido(null)}
        pedido={detailPedido}
        onRefresh={loadPedidos}
      />
      <SignatureModal
        open={!!firmaPedido}
        onClose={() => setFirmaPedido(null)}
        pedido={firmaPedido}
      />
    </div>
  );
}
