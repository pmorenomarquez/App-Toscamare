import { useContext } from 'react';
import { AppContext } from '@/context/AppContext';
import { ROLES, ROLE_META, ESTADOS } from '@/config/constants';
import { timeAgo } from '@/utils/helpers';
import { SVG, Btn, Badge } from '@/components/ui';

export default function DashboardView({ setView }) {
  const { pedidos, session } = useContext(AppContext);
  const isModerator = session.user.rol === ROLES.ADMIN || session.user.rol === ROLES.OFICINA;

  const stats = Object.entries(ESTADOS).map(([e, cfg]) => ({
    estado: parseInt(e), ...cfg, count: pedidos.filter(p => p.estado_actual === parseInt(e)).length,
  }));

  const myPedidos = isModerator ? pedidos : pedidos.filter(p => {
    return p.estado_actual === ROLE_META[session.user.rol].estadoVisible;
  });

  return (
    <div style={{ padding: 28 }}>
      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14, marginBottom: 28 }}>
        {stats.map((s, i) => (
          <div key={s.estado} className={'anim-fade d' + (i + 1)} onClick={() => setView('pedidos')}
            style={{ background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 'var(--r3)',
              padding: '18px 20px', cursor: 'pointer', transition: '.15s var(--ease)' }}
            onMouseEnter={e => e.currentTarget.style.borderColor = s.color + '40'}
            onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-1)'}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-4)', textTransform: 'uppercase', letterSpacing: '.04em' }}>{s.label}</span>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: s.color, boxShadow: '0 0 8px ' + s.color + '50' }} />
            </div>
            <span style={{ fontSize: 34, fontWeight: 700, color: s.color, letterSpacing: '-0.03em' }}>{s.count}</span>
          </div>
        ))}
        <div className="anim-fade d5" style={{ background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 'var(--r3)', padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-4)', textTransform: 'uppercase', letterSpacing: '.04em' }}>Total</span>
            <SVG name="box" size={16} color="var(--text-4)" />
          </div>
          <span style={{ fontSize: 34, fontWeight: 700, letterSpacing: '-0.03em' }}>{pedidos.length}</span>
        </div>
      </div>

      {/* Recent pedidos */}
      <div className="anim-fade d4" style={{ background: 'var(--bg-2)', border: '1px solid var(--border-1)', borderRadius: 'var(--r3)', overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 14, fontWeight: 600 }}>Pedidos Recientes</span>
          <Btn variant="ghost" size="sm" icon="chevronR" onClick={() => setView('pedidos')}>Ver todos</Btn>
        </div>
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          {myPedidos.slice(0, 8).map(p => (
            <div key={p.id} style={{ padding: '12px 18px', borderBottom: '1px solid var(--border-1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <code style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--accent)' }}>{p.codigo}</code>
                <p style={{ fontSize: 13, color: 'var(--text-2)', marginTop: 2 }}>{p.cliente}</p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Badge color={ESTADOS[p.estado_actual].color}>{ESTADOS[p.estado_actual].label}</Badge>
                <span style={{ fontSize: 10, color: 'var(--text-4)' }}>{timeAgo(p.fecha_actualizacion)}</span>
              </div>
            </div>
          ))}
          {myPedidos.length === 0 && <div style={{ padding: '30px 18px', textAlign: 'center', color: 'var(--text-4)', fontSize: 13 }}>Sin pedidos</div>}
        </div>
      </div>
    </div>
  );
}
