import { useContext } from 'react';
import { AppContext } from '@/context/AppContext';
import { ROLE_META, ESTADOS } from '@/config/constants';
import { SVG, Spinner } from '@/components/ui';

export default function LoginScreen() {
  const { loginMicrosoft, loading } = useContext(AppContext);

  // While checking if there's a saved session, show loading
  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: 'var(--bg-0)' }}>
        <div style={{ textAlign: 'center' }}>
          <Spinner />
          <p style={{ marginTop: 16, color: 'var(--text-3)', fontSize: 14 }}>Verificando sesión...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: 'var(--bg-0)' }}>
      {/* Left panel — branding */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center',
        alignItems: 'center', background: 'linear-gradient(145deg, var(--bg-0) 0%, var(--bg-2) 50%, var(--bg-0) 100%)',
        borderRight: '1px solid var(--border-1)', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, opacity: .04,
          backgroundImage: 'linear-gradient(var(--accent) 1px, transparent 1px), linear-gradient(90deg, var(--accent) 1px, transparent 1px)',
          backgroundSize: '60px 60px' }} />
        <div style={{ position: 'absolute', width: 400, height: 400, borderRadius: '50%',
          background: 'radial-gradient(circle, var(--accent-dim) 0%, transparent 70%)',
          top: '30%', left: '40%', transform: 'translate(-50%,-50%)' }} />
        <div className="anim-fade" style={{ position: 'relative', zIndex: 1, textAlign: 'center', padding: 40 }}>
          <div style={{ width: 72, height: 72, borderRadius: 18, background: 'var(--accent-dim)',
            border: '1px solid var(--accent-border)', display: 'inline-flex', alignItems: 'center',
            justifyContent: 'center', marginBottom: 28 }}>
            <SVG name="box" size={36} color="var(--accent)" />
          </div>
          <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: '-0.03em', lineHeight: 1.2 }}>
            Toscamare
          </h1>
          <p style={{ color: 'var(--text-3)', fontSize: 14, marginTop: 12, maxWidth: 320 }}>
            Gestión de pedidos para minoristas y mayoristas
          </p>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
            gap: 6, marginTop: 32, flexWrap: 'wrap' }}>
            {Object.entries(ESTADOS).map(([k, v], i) => (
              <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ padding: '4px 10px', borderRadius: 5, fontSize: 10, fontWeight: 600,
                  color: v.color, background: v.bg, border: '1px solid ' + v.borderColor,
                  letterSpacing: '.03em' }}>{v.label}</span>
                {i < 3 && <SVG name="chevronR" size={12} color="var(--text-4)" />}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — login */}
      <div style={{ width: 460, display: 'flex', flexDirection: 'column', justifyContent: 'center',
        padding: '40px 50px', background: 'var(--bg-1)' }}>
        <div className="anim-fade d2">
          <h2 style={{ fontSize: 22, fontWeight: 600, marginBottom: 6 }}>Iniciar Sesión</h2>
          <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 32 }}>
            Usa tu cuenta de Microsoft / Outlook para acceder
          </p>

          {/* Microsoft OAuth button */}
          <button onClick={loginMicrosoft} style={{
            width: '100%', padding: '14px 20px', borderRadius: 'var(--r2)',
            background: 'var(--bg-3)', border: '1px solid var(--border-3)', color: 'var(--text-1)',
            fontSize: 15, fontWeight: 500, cursor: 'pointer', display: 'flex',
            alignItems: 'center', justifyContent: 'center', gap: 12,
            transition: '.15s var(--ease)',
          }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-4)'}
            onMouseLeave={e => e.currentTarget.style.background = 'var(--bg-3)'}>
            <svg width="20" height="20" viewBox="0 0 21 21">
              <rect x="1" y="1" width="9" height="9" fill="#f25022" />
              <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
              <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
              <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
            </svg>
            Iniciar con Microsoft
          </button>

          <p style={{ fontSize: 12, color: 'var(--text-4)', textAlign: 'center', marginTop: 20,
            lineHeight: 1.6 }}>
            Tu email de Microsoft debe estar registrado en el sistema.<br />
            Si no tienes acceso, contacta al administrador.
          </p>

          {/* Roles info */}
          <div style={{ marginTop: 40, padding: 18, background: 'var(--bg-0)',
            borderRadius: 'var(--r2)', border: '1px solid var(--border-1)' }}>
            <p style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-4)',
              textTransform: 'uppercase', letterSpacing: '.06em', marginBottom: 12 }}>
              Roles del sistema
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {Object.entries(ROLE_META).filter(([k]) => k !== 'admin').map(([key, meta]) => (
                <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: meta.color,
                    boxShadow: '0 0 6px ' + meta.color + '50' }} />
                  <span style={{ fontSize: 13, color: meta.color, fontWeight: 500 }}>
                    {meta.label}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-4)', marginLeft: 'auto' }}>
                    Estado {meta.estadoVisible}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
