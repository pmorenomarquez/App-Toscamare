import { useState, useContext } from 'react';
import { AppContext } from '@/context/AppContext';
import { ESTADOS } from '@/config/constants';
import { timeAgo } from '@/utils/helpers';
import { Badge } from '@/components/ui';
import PedidoDetailModal from '@/components/pedidos/PedidoDetailModal';

export default function PipelineView() {
  const { pedidos, loadPedidos } = useContext(AppContext);
  const [detail, setDetail] = useState(null);

  return (
    <div style={{ padding: 28 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, minHeight: 'calc(100vh - 180px)' }}>
        {Object.entries(ESTADOS).filter(([k]) => parseInt(k) <= 3).map(([estado, cfg]) => {
          const items = pedidos.filter(p => p.estado_actual === parseInt(estado));
          return (
            <div key={estado} className="anim-fade" style={{ background: 'var(--bg-1)', border: '1px solid var(--border-1)',
              borderRadius: 'var(--r3)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-1)', display: 'flex',
                alignItems: 'center', justifyContent: 'space-between', background: cfg.bg }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: cfg.color, boxShadow: '0 0 8px ' + cfg.color + '40' }} />
                  <span style={{ fontSize: 13, fontWeight: 600, color: cfg.color }}>{cfg.label}</span>
                </div>
                <span style={{ fontSize: 12, fontWeight: 700, color: cfg.color, background: cfg.color + '20',
                  padding: '2px 9px', borderRadius: 5 }}>{items.length}</span>
              </div>
              <div style={{ padding: 10, flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {items.length === 0 ? <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-4)', fontSize: 12 }}>Vacío</div> :
                  items.map(p => (
                    <div key={p.id} onClick={() => setDetail(p)} style={{ padding: '12px 14px', background: 'var(--bg-2)',
                      border: '1px solid var(--border-2)', borderRadius: 'var(--r2)', cursor: 'pointer', transition: '.12s var(--ease)' }}
                      onMouseEnter={e => e.currentTarget.style.borderColor = cfg.color + '50'}
                      onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-2)'}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <code style={{ fontFamily: 'var(--mono)', fontSize: 11, color: cfg.color }}>{p.codigo}</code>
                      </div>
                      <p style={{ fontSize: 13, fontWeight: 500, marginBottom: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.cliente}</p>
                      <span style={{ fontSize: 10, color: 'var(--text-4)' }}>{timeAgo(p.fecha_actualizacion)}</span>
                    </div>
                  ))
                }
              </div>
            </div>
          );
        })}
      </div>
      <PedidoDetailModal open={!!detail} onClose={() => setDetail(null)} pedido={detail} onRefresh={loadPedidos} />
    </div>
  );
}
