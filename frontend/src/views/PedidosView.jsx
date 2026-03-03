import { useState, useMemo, useContext } from 'react';
import { AppContext } from '@/context/AppContext';
import { ROLES, ROLE_META, ESTADOS } from '@/config/constants';
import { timeAgo } from '@/utils/helpers';
import { SVG, Btn, Badge, Select, EmptyState } from '@/components/ui';
import PedidoFormModal from '@/components/pedidos/PedidoFormModal';
import PedidoDetailModal from '@/components/pedidos/PedidoDetailModal';
import * as api from '@/utils/api';

export default function PedidosView() {
  const { pedidos, session, showToast, loadPedidos, adminViewAs } = useContext(AppContext);
  const [search, setSearch] = useState('');
  const [filterEstado, setFilterEstado] = useState('todos');
  const [showCreate, setShowCreate] = useState(false);
  const [detailPedido, setDetailPedido] = useState(null);
  const [confirmId, setConfirmId] = useState(null);
  const [confirmAction, setConfirmAction] = useState(null); // 'advance' | 'rollback'
  const [actionLoading, setActionLoading] = useState(null);

  const isAdmin = session.user.rol === ROLES.ADMIN;
  const isOficina = session.user.rol === ROLES.OFICINA;
  const isModerator = isAdmin || isOficina;

  const filtered = useMemo(() => {
    let list = pedidos;

    // When admin views as a specific role, filter to that role's estado
    if (isAdmin && adminViewAs) {
      const estadoVisible = ROLE_META[adminViewAs]?.estadoVisible;
      if (estadoVisible != null) {
        list = list.filter(p => p.estado_actual === estadoVisible);
      }
    }

    // Moderators can further filter by estado dropdown
    if (isModerator && filterEstado !== 'todos') {
      list = list.filter(p => p.estado_actual === parseInt(filterEstado));
    }
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(p => p.codigo.toLowerCase().includes(q) || p.cliente.toLowerCase().includes(q));
    }
    return list;
  }, [pedidos, filterEstado, search, isModerator, isAdmin, adminViewAs]);

  const advanceOrder = async (pedidoId) => {
    const pedido = pedidos.find(p => p.id === pedidoId);
    if (!pedido) return;

    setActionLoading(pedidoId);
    try {
      await api.advancePedido(pedidoId);
      const nextLabel = ESTADOS[pedido.estado_actual + 1]?.label || 'Siguiente';
      showToast(pedido.codigo + ' → ' + nextLabel);
      await loadPedidos();
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      setActionLoading(null);
      setConfirmId(null);
      setConfirmAction(null);
    }
  };

  const rollbackOrder = async (pedidoId) => {
    const pedido = pedidos.find(p => p.id === pedidoId);
    if (!pedido) return;

    setActionLoading(pedidoId);
    try {
      await api.rollbackPedido(pedidoId);
      const prevLabel = ESTADOS[pedido.estado_actual - 1]?.label || 'Anterior';
      showToast(pedido.codigo + ' ← ' + prevLabel);
      await loadPedidos();
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      setActionLoading(null);
      setConfirmId(null);
      setConfirmAction(null);
    }
  };

  const handleExportExcel = async (pedido) => {
    try {
      await api.exportExcel(pedido.id);
      showToast('Excel descargado');
    } catch (e) {
      showToast(e.message, 'error');
    }
  };

  // Advance: admin can advance any estado, each role only their own
  const canAdvance = (p) => {
    if (isAdmin) return true;
    return ESTADOS[p.estado_actual]?.role === session.user.rol;
  };

  // Rollback: send pedido back one estado for corrections
  // Each role can rollback their own estado, admin can rollback any
  const canRollback = (p) => {
    if (p.estado_actual <= 0) return false;
    if (isAdmin) return true;
    return ESTADOS[p.estado_actual]?.role === session.user.rol;
  };

  const canExport = (p) => {
    return p.estado_actual === 3 && (isOficina || isAdmin);
  };

  const showAdvanceBtn = (p) => {
    return p.estado_actual < 3 && canAdvance(p);
  };

  const canCreate = isOficina || isAdmin;

  return (
    <div style={{ padding: 28 }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ position: 'relative' }}>
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar pedidos..."
              style={{ padding: '8px 12px 8px 34px', background: 'var(--bg-2)', border: '1px solid var(--border-2)',
                borderRadius: 'var(--r2)', color: 'var(--text-1)', fontSize: 13, width: 240 }} />
            <div style={{ position: 'absolute', top: '50%', left: 11, transform: 'translateY(-50%)', pointerEvents: 'none' }}>
              <SVG name="search" size={14} color="var(--text-4)" />
            </div>
          </div>
          {isModerator && !adminViewAs && <Select value={filterEstado} onChange={e => setFilterEstado(e.target.value)} options={[
            { value: 'todos', label: 'Todos los estados' }, ...Object.entries(ESTADOS).map(([k, v]) => ({ value: k, label: v.label }))
          ]} />}
        </div>
        {canCreate && (
          <Btn variant="primary" icon="plus" onClick={() => setShowCreate(true)}>Nuevo Pedido</Btn>
        )}
      </div>

      <p style={{ fontSize: 12, color: 'var(--text-4)', marginBottom: 14 }}>
        {filtered.length} pedido{filtered.length !== 1 ? 's' : ''}
        {!isModerator && (' — ' + (ROLE_META[session.user.rol]?.label || ''))}
        {isAdmin && adminViewAs && (' — Vista: ' + (ROLE_META[adminViewAs]?.label || ''))}
      </p>

      {filtered.length === 0 ? (
        <EmptyState icon="check" title="Sin pedidos pendientes" subtitle={search ? 'Intenta otro término' : 'Tu bandeja está vacía'} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filtered.map((p, i) => {
            const est = ESTADOS[p.estado_actual];
            const isConfirming = confirmId === p.id;
            const isLoading = actionLoading === p.id;
            return (
              <div key={p.id} className={'anim-fade d' + Math.min(i + 1, 8)} style={{
                background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 'var(--r3)',
                padding: '16px 20px', transition: '.15s var(--ease)', borderLeft: '3px solid ' + est.color }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-3)'}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-1)'; e.currentTarget.style.borderLeftColor = est.color; }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                      <code style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 500, color: est.color }}>{p.codigo}</code>
                      <Badge color={est.color} bg={est.bg} border={est.borderColor}>{est.label}</Badge>
                    </div>
                    <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 3 }}>{p.cliente}</p>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 8 }}>
                      <span style={{ fontSize: 11, color: 'var(--text-4)', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <SVG name="clock" size={12} color="var(--text-4)" />{timeAgo(p.fecha_actualizacion)}</span>
                      {p.pdf_ruta && <span style={{ fontSize: 11, color: 'var(--text-4)', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <SVG name="file" size={12} color="var(--text-4)" />PDF</span>}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                    <Btn variant="ghost" size="sm" icon="eye" onClick={() => setDetailPedido(p)} />

                    {/* Export Excel button for oficina/admin at state 3 */}
                    {canExport(p) && (
                      <Btn variant="outline" size="sm" icon="download" onClick={() => handleExportExcel(p)}>Excel</Btn>
                    )}

                    {/* Confirmation dialog */}
                    {isConfirming ? (
                      <div style={{ display: 'flex', gap: 4 }}>
                        <Btn variant="ghost" size="sm" onClick={() => { setConfirmId(null); setConfirmAction(null); }}>No</Btn>
                        <Btn variant={confirmAction === 'rollback' ? 'outline' : 'primary'} size="sm"
                          icon={confirmAction === 'rollback' ? 'chevronL' : 'check'} disabled={isLoading}
                          onClick={() => confirmAction === 'rollback' ? rollbackOrder(p.id) : advanceOrder(p.id)}>
                          {isLoading ? '...' : 'Confirmar'}
                        </Btn>
                      </div>
                    ) : (
                      <>
                        {/* Rollback button */}
                        {canRollback(p) && (
                          <Btn variant="outline" size="sm" icon="chevronL"
                            onClick={() => { setConfirmId(p.id); setConfirmAction('rollback'); }}>
                            Devolver
                          </Btn>
                        )}

                        {/* Advance state button for estados 0-2 */}
                        {showAdvanceBtn(p) && (
                          <Btn variant="primary" size="sm" icon="chevronR"
                            onClick={() => { setConfirmId(p.id); setConfirmAction('advance'); }}>
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
      <PedidoDetailModal open={!!detailPedido} onClose={() => setDetailPedido(null)} pedido={detailPedido} onRefresh={loadPedidos} />
    </div>
  );
}
