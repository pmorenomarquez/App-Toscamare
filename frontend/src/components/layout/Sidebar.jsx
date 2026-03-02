import { useContext } from 'react';
import { AppContext } from '@/context/AppContext';
import { ROLES, ROLE_META } from '@/config/constants';
import { SVG } from '@/components/ui';

export default function Sidebar({ currentView, setView }) {
  const { session } = useContext(AppContext);
  const { user } = session;
  const role = ROLE_META[user.rol];

  const getNavItemsByRole = () => {
    const baseItems = [
      { id: 'pedidos', label: 'Mi Cuadrante', icon: 'box' },
    ];

    if (user.rol === ROLES.ADMIN) {
      return [
        { id: 'dashboard', label: 'Dashboard', icon: 'home' },
        ...baseItems,
        { id: 'pipeline', label: 'Pipeline', icon: 'grid' },
        { id: 'usuarios', label: 'Usuarios', icon: 'users' },
      ];
    }

    if (user.rol === ROLES.OFICINA) {
      return [
        { id: 'dashboard', label: 'Dashboard', icon: 'home' },
        ...baseItems,
        { id: 'pipeline', label: 'Pipeline', icon: 'grid' },
      ];
    }

    return baseItems;
  };

  const navItems = getNavItemsByRole();

  return (
    <aside style={{ width: 230, flexShrink: 0, background: 'var(--bg-1)', borderRight: '1px solid var(--border-1)',
      display: 'flex', flexDirection: 'column', height: '100vh', position: 'sticky', top: 0 }}>
      {/* Brand */}
      <div style={{ padding: '20px 18px', borderBottom: '1px solid var(--border-1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 34, height: 34, borderRadius: 9, background: 'var(--accent-dim)',
            border: '1px solid var(--accent-border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <SVG name="box" size={18} color="var(--accent)" />
          </div>
          <div>
            <span style={{ fontSize: 14, fontWeight: 600, display: 'block', lineHeight: 1.2 }}>Toscamare</span>
            <span style={{ fontSize: 10, color: 'var(--text-4)', letterSpacing: '.04em' }}>v1.0</span>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '12px 10px', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {navItems.map(item => {
          const active = currentView === item.id;
          return (
            <button key={item.id} onClick={() => setView(item.id)} style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px',
              background: active ? 'var(--bg-3)' : 'transparent', border: 'none',
              borderRadius: 'var(--r2)', cursor: 'pointer', transition: '.12s var(--ease)',
              color: active ? 'var(--text-1)' : 'var(--text-3)',
              borderLeft: active ? '2px solid var(--accent)' : '2px solid transparent',
            }}
              onMouseEnter={e => !active && (e.currentTarget.style.background = 'var(--bg-2)')}
              onMouseLeave={e => !active && (e.currentTarget.style.background = 'transparent')}>
              <SVG name={item.icon} size={17} color={active ? 'var(--accent)' : 'var(--text-4)'} />
              <span style={{ fontSize: 13, fontWeight: active ? 500 : 400 }}>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* User card */}
      <div style={{ padding: '14px 14px 16px', borderTop: '1px solid var(--border-1)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 34, height: 34, borderRadius: '50%', background: role.color + '18',
            border: '1px solid ' + role.color + '30', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <SVG name="user" size={16} color={role.color} />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.nombre}</p>
            <p style={{ fontSize: 11, color: role.color }}>{role.label}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
