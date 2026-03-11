export default function Badge({ color, bg, border, children, style:s }) {
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'5px 12px', borderRadius:'var(--r1)',
      fontSize:13, fontWeight:600, letterSpacing:'.02em', color, background: bg||color+'14',
      border:'1px solid '+(border||color+'30'), ...s }}>
      <span style={{ width:7, height:7, borderRadius:'50%', background:color, boxShadow:'0 0 6px '+color+'50' }} />
      {children}
    </span>
  );
}