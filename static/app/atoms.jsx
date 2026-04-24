// MeetingMind Shared Icons & Atoms
// Stroke SVGs, no emoji. Imported everywhere via window.MM.

const MMI = {
  mic: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="7" y="3" width="6" height="10" rx="3"/><path d="M4 10a6 6 0 0 0 12 0M10 16v2"/></svg>,
  micOff: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="7" y="3" width="6" height="7" rx="3"/><path d="M4 10a6 6 0 0 0 9 5.2M10 16v2M3 3l14 14"/></svg>,
  play: (p) => <svg viewBox="0 0 20 20" fill="currentColor" {...p}><path d="M6 4l11 6-11 6z"/></svg>,
  stop: (p) => <svg viewBox="0 0 20 20" fill="currentColor" {...p}><rect x="5" y="5" width="10" height="10" rx="2"/></svg>,
  pause: (p) => <svg viewBox="0 0 20 20" fill="currentColor" {...p}><rect x="5" y="4" width="4" height="12" rx="1"/><rect x="11" y="4" width="4" height="12" rx="1"/></svg>,
  plus: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...p}><path d="M10 4v12M4 10h12"/></svg>,
  check: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M4 10l4 4 8-8"/></svg>,
  chevR: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...p}><path d="M7 5l5 5-5 5"/></svg>,
  chevL: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...p}><path d="M13 5l-5 5 5 5"/></svg>,
  chevD: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...p}><path d="M5 8l5 5 5-5"/></svg>,
  search: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><circle cx="9" cy="9" r="5"/><path d="M13 13l4 4"/></svg>,
  bell: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M5 8a5 5 0 0 1 10 0v3l1.5 3h-13L5 11z"/><path d="M8 16.5a2 2 0 0 0 4 0"/></svg>,
  doc: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M5 3h7l3 3v11a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"/><path d="M7 9h6M7 12h6M7 15h4"/></svg>,
  settings: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="10" cy="10" r="2"/><path d="M10 2v2M10 16v2M4 10H2M18 10h-2M4.5 4.5L6 6M14 14l1.5 1.5M4.5 15.5L6 14M14 6l1.5-1.5"/></svg>,
  sun: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><circle cx="10" cy="10" r="3.5"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.5 4.5l1.4 1.4M14.1 14.1l1.4 1.4M4.5 15.5l1.4-1.4M14.1 5.9l1.4-1.4"/></svg>,
  moon: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M17 13A7 7 0 0 1 7 3a7 7 0 1 0 10 10z"/></svg>,
  sparkle: (p) => <svg viewBox="0 0 20 20" fill="currentColor" {...p}><path d="M10 1.5l1.8 4.7L16.5 8l-4.7 1.8L10 14.5 8.2 9.8 3.5 8l4.7-1.8zM16 13l.9 2.3 2.1.7-2.1.7L16 19l-.9-2.3-2.1-.7 2.1-.7z"/></svg>,
  panel: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" {...p}><rect x="3" y="4" width="14" height="12" rx="1.5"/><path d="M8 4v12"/></svg>,
  close: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" {...p}><path d="M5 5l10 10M15 5L5 15"/></svg>,
  bookmark: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" {...p}><path d="M5 3h10v14l-5-3.5L5 17z"/></svg>,
  upload: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M10 3v10M6 7l4-4 4 4M3 15v2h14v-2"/></svg>,
  link: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" {...p}><path d="M8 12a3 3 0 0 0 4 0l3-3a3 3 0 0 0-4-4l-1 1M12 8a3 3 0 0 0-4 0l-3 3a3 3 0 0 0 4 4l1-1"/></svg>,
  edit: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M13 4l3 3-9 9H4v-3z"/></svg>,
  send: (p) => <svg viewBox="0 0 20 20" fill="currentColor" {...p}><path d="M3 10l14-6-6 14-2-6z"/></svg>,
  trash: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M4 6h12M8 6V4h4v2M6 6l1 10a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1l1-10"/></svg>,
  arrowR: (p) => <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M4 10h12M11 5l5 5-5 5"/></svg>,
};

function Avatar({ s, name, size = 28, ringed = false }) {
  const bg = window.MM.speakerColorResolved(s);
  return (
    <span style={{
      width: size, height: size, borderRadius: '50%',
      background: bg, color: '#fff',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.42, fontWeight: 700, letterSpacing: '-0.02em',
      flexShrink: 0,
      boxShadow: ringed ? `0 0 0 2px var(--bg), 0 0 0 4px ${bg}` : 'none',
    }}>{window.MM.speakerLetter(s || name)}</span>
  );
}

function Pill({ children, tone = 'neutral', size = 'sm', style }) {
  const map = {
    neutral: { bg: 'var(--surface-alt)', fg: 'var(--text-2)' },
    accent: { bg: 'var(--accent-soft)', fg: 'var(--accent)' },
    positive: { bg: 'var(--positive-soft)', fg: 'var(--positive)' },
    warning: { bg: 'var(--warning-soft)', fg: 'var(--warning)' },
    danger: { bg: 'var(--danger-soft)', fg: 'var(--danger)' },
    ghost: { bg: 'transparent', fg: 'var(--text-3)' },
  };
  const { bg, fg } = map[tone];
  const pad = size === 'xs' ? '2px 8px' : '4px 10px';
  const fs = size === 'xs' ? 'var(--fs-xs)' : 'var(--fs-sm)';
  return <span style={{ background: bg, color: fg, padding: pad, borderRadius: 999, fontSize: fs, fontWeight: 600, whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 4, ...style }}>{children}</span>;
}

function Button({ children, variant = 'primary', size = 'md', onClick, style, icon, disabled, type }) {
  const base = {
    display: 'inline-flex', alignItems: 'center', gap: 6, justifyContent: 'center',
    border: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
    fontFamily: 'inherit', fontWeight: 600, letterSpacing: '-0.01em',
    borderRadius: 10, transition: 'all 120ms ease',
    opacity: disabled ? 0.5 : 1, whiteSpace: 'nowrap',
  };
  const sizes = {
    xs: { padding: '4px 8px', fontSize: 'var(--fs-xs)', height: 24, borderRadius: 6 },
    sm: { padding: '6px 12px', fontSize: 'var(--fs-sm)', height: 30 },
    md: { padding: '10px 16px', fontSize: 'var(--fs-base)', height: 40 },
    lg: { padding: '14px 22px', fontSize: 'var(--fs-md)', height: 52, borderRadius: 14 },
  };
  const variants = {
    primary: { background: 'var(--accent)', color: '#fff' },
    secondary: { background: 'var(--surface-alt)', color: 'var(--text)' },
    ghost: { background: 'transparent', color: 'var(--text-2)' },
    danger: { background: 'var(--danger-soft)', color: 'var(--danger)' },
    dangerSolid: { background: 'var(--danger)', color: '#fff' },
    outline: { background: 'transparent', color: 'var(--text)', boxShadow: 'inset 0 0 0 1px var(--border-strong)' },
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      style={{ ...base, ...sizes[size], ...variants[variant], ...style }}>
      {icon}{children}
    </button>
  );
}

function IconButton({ children, onClick, style, label }) {
  return (
    <button onClick={onClick} title={label} aria-label={label} style={{
      width: 32, height: 32, border: '1px solid var(--border)', background: 'var(--surface)',
      borderRadius: 8, color: 'var(--text-2)', cursor: 'pointer', display: 'grid', placeItems: 'center',
      transition: 'all 120ms', fontFamily: 'inherit', ...style,
    }}
    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface-alt)'; e.currentTarget.style.color = 'var(--text)'; }}
    onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--surface)'; e.currentTarget.style.color = 'var(--text-2)'; }}>
      {children}
    </button>
  );
}

// Inline-editable text. Click to edit, Enter to commit, Esc to cancel.
function InlineEdit({ value, onCommit, style, placeholder, fontSize }) {
  const [editing, setEditing] = React.useState(false);
  const [v, setV] = React.useState(value);
  const ref = React.useRef(null);
  React.useEffect(() => { setV(value); }, [value]);
  React.useEffect(() => {
    if (editing && ref.current) { ref.current.focus(); ref.current.select(); }
  }, [editing]);
  if (editing) {
    return (
      <input ref={ref} value={v} onChange={(e) => setV(e.target.value)}
        onBlur={() => { if (v.trim()) onCommit(v.trim()); else setV(value); setEditing(false); }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { e.target.blur(); }
          if (e.key === 'Escape') { setV(value); setEditing(false); }
        }}
        style={{
          background: 'var(--surface-alt)', border: '1px solid var(--accent)',
          color: 'var(--text)', fontFamily: 'inherit', fontSize: fontSize || 'inherit',
          fontWeight: 'inherit', letterSpacing: 'inherit', padding: '2px 6px', margin: '-2px -6px',
          borderRadius: 6, outline: 'none', ...style,
        }}/>
    );
  }
  return (
    <span onClick={(e) => { e.stopPropagation(); setEditing(true); }} style={{ cursor: 'text', borderRadius: 6, ...style }}
      title="클릭해서 편집">
      {value || <span style={{ color: 'var(--text-4)' }}>{placeholder}</span>}
    </span>
  );
}

window.MM = window.MM || {};
window.MM.MMI = MMI;
window.MM.Avatar = Avatar;
window.MM.Pill = Pill;
window.MM.Button = Button;
window.MM.IconButton = IconButton;
window.MM.InlineEdit = InlineEdit;
