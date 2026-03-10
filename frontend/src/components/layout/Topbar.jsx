import { useContext, useState, useEffect, useRef, useMemo } from 'react';
import { AppContext } from '@/context/AppContext';
import { ROLES, ROLE_META, ESTADOS } from '@/config/constants';
import { timeAgo } from '@/utils/helpers';
import { SVG, Badge } from '@/components/ui';

function getInitialTheme() {
  const saved = localStorage.getItem('theme');
  if (saved) return saved;
  return 'dark';
}

export default function Topbar({ title, subtitle, onNavigate }) {
  const { logout, pedidos, session } = useContext(AppContext);
  const [theme, setTheme] = useState(getInitialTheme);
  const [bellOpen, setBellOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Close dropdown on outside click
  useEffect(() => {
    if (!bellOpen) return;
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setBellOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [bellOpen]);

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark');

  // Compute actionable tasks for current role
  const tasks = useMemo(() => {
    if (!session) return [];
    const rol = session.user.rol;

    if (rol === ROLES.ADMIN) {
      return pedidos.filter(p => p.estado_actual <= 3);
    }

    if (rol === ROLES.OFICINA) {
      // Oficina (moderator): notifications for estado 3 (ready for export)
      return pedidos.filter(p => p.estado_actual === 3);
    }

    // Other roles: tasks matching their actionable estado
    const estadoVisible = ROLE_META[rol]?.estadoVisible;
    if (estadoVisible == null) return [];
    return pedidos.filter(p => p.estado_actual === estadoVisible);
  }, [pedidos, session]);

  const taskCount = tasks.length;

  const handleTaskClick = () => {
    setBellOpen(false);
    if (onNavigate) onNavigate('pedidos');
  };

  const btnStyle = { width: 36, height: 36, borderRadius: 'var(--r2)', background: 'var(--bg-2)',
    border: '1px solid var(--border-2)', cursor: 'pointer', display: 'flex', alignItems: 'center',
    justifyContent: 'center', color: 'var(--text-3)', transition: '.15s var(--ease)' };

  return (
    <header style={{ padding: '16px 28px', background: 'var(--bg-1)', borderBottom: '1px solid var(--border-1)',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em' }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2 }}>{subtitle}</p>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {/* Theme toggle */}
        <button onClick={toggleTheme} className="tooltip" data-tip={theme === 'dark' ? 'Modo día' : 'Modo noche'} style={btnStyle}>
          <SVG name={theme === 'dark' ? 'sun' : 'moon'} size={16} />
        </button>

        {/* Notification bell */}
        <div ref={dropdownRef} style={{ position: 'relative' }}>
          <button onClick={() => setBellOpen(o => !o)} style={btnStyle}>
            <SVG name="bell" size={16} />
          </button>
          {taskCount > 0 && (
            <span style={{ position: 'absolute', top: -3, right: -3, minWidth: 16, height: 16, padding: '0 4px',
              borderRadius: '50%', background: 'var(--accent)', color: '#FFFFFF', fontSize: 9, fontWeight: 700,
              display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
              {taskCount > 99 ? '99+' : taskCount}
            </span>
          )}

          {/* Dropdown */}
          {bellOpen && (
            <div className="anim-scale" style={{ position: 'absolute', top: 'calc(100% + 8px)', right: 0,
              width: 340, maxHeight: 420, background: 'var(--bg-1)', border: '1px solid var(--border-2)',
              borderRadius: 'var(--r3)', boxShadow: 'var(--shadow)', zIndex: 100, overflow: 'hidden',
              display: 'flex', flexDirection: 'column' }}>
              {/* Header */}
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-1)',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>Notificaciones</span>
                {taskCount > 0 && (
                  <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600 }}>
                    {taskCount} pendiente{taskCount !== 1 ? 's' : ''}
                  </span>
                )}
              </div>

              {/* Task list */}
              <div style={{ overflowY: 'auto', flex: 1 }}>
                {taskCount === 0 ? (
                  <div style={{ padding: '32px 16px', textAlign: 'center' }}>
                    <SVG name="check" size={24} color="var(--text-4)" />
                    <p style={{ fontSize: 13, color: 'var(--text-4)', marginTop: 8 }}>Sin tareas pendientes</p>
                  </div>
                ) : (
                  tasks.slice(0, 15).map(p => {
                    const est = ESTADOS[p.estado_actual];
                    return (
                      <div key={p.id} onClick={handleTaskClick}
                        style={{ padding: '10px 16px', borderBottom: '1px solid var(--border-1)',
                          cursor: 'pointer', transition: '.12s var(--ease)' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-2)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                              <code style={{ fontFamily: 'var(--mono)', fontSize: 11, color: est.color }}>{p.codigo}</code>
                              <Badge color={est.color} bg={est.bg} border={est.borderColor}>{est.label}</Badge>
                            </div>
                            <p style={{ fontSize: 12, color: 'var(--text-2)', overflow: 'hidden',
                              textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.cliente}</p>
                          </div>
                          <span style={{ fontSize: 10, color: 'var(--text-4)', flexShrink: 0 }}>
                            {timeAgo(p.fecha_actualizacion)}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Footer */}
              {taskCount > 0 && (
                <div onClick={handleTaskClick} style={{ padding: '10px 16px', borderTop: '1px solid var(--border-1)',
                  textAlign: 'center', cursor: 'pointer', transition: '.12s var(--ease)' }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-2)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <span style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 500 }}>
                    Ver todos los pedidos
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        <button onClick={logout} className="tooltip" data-tip="Cerrar sesión" style={btnStyle}>
          <SVG name="logout" size={16} />
        </button>
      </div>
    </header>
  );
}
