import SVG from './SVG';

const SIZES = { sm: { padding:'8px 16px', fontSize:14 }, md: { padding:'12px 20px', fontSize:15 }, lg: { padding:'14px 28px', fontSize:17 } };

export default function Btn({ children, variant='secondary', size='md', icon, danger, disabled, onClick, style:s, ...rest }) {
  const vars = {
    primary:   { background: danger ? 'var(--danger)' : 'var(--accent)', color: '#FFFFFF' },
    secondary: { background: 'var(--bg-3)', color: 'var(--text-1)', border: '1px solid var(--border-2)' },
    ghost:     { background: 'transparent', color: danger ? 'var(--danger)' : 'var(--text-2)' },
    outline:   { background: 'transparent', color: danger ? 'var(--danger)' : 'var(--text-1)', border: '1px solid ' + (danger ? 'var(--danger)' : 'var(--border-2)') },
  };
  return (
    <button disabled={disabled} onClick={onClick}
      style={{ display:'inline-flex', alignItems:'center', justifyContent:'center', gap:7, border:'none',
        borderRadius:'var(--r2)', cursor: disabled?'not-allowed':'pointer', fontFamily:'var(--font)',
        fontWeight:500, transition:'.15s var(--ease)', opacity: disabled?.45:1, whiteSpace:'nowrap',
        ...SIZES[size], ...(vars[variant]||vars.secondary), ...s }}
      onMouseEnter={e=>!disabled&&(e.currentTarget.style.opacity='.85')}
      onMouseLeave={e=>!disabled&&(e.currentTarget.style.opacity=disabled?'.45':'1')} {...rest}>
      {icon && <SVG name={icon} size={size==='sm'?14:16} />}
      {children}
    </button>
  );
}