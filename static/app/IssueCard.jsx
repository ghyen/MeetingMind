// MeetingMind — Issue card (쟁점 카드)
// Position Chip 스타일. 합의/북마크/편집 인터랙션.

const { useState: icU } = React;

function IssueCard({ issue, topicId, topic, active, onCommitConsensus, onAddOpen, onUpdate, onClick, highlighted, readOnly, pendingTokens, tokenThreshold, notes, onSaveNote }) {
  const { MMI, Avatar, Pill, Button, InlineEdit, IconButton } = window.MM;
  const [editMode, setEditMode] = icU(false);
  const [consensusDraft, setConsensusDraft] = icU('');
  const [showConsensusInput, setShowConsensusInput] = icU(false);

  const positions = issue?.positions || [];
  const openQs = issue?.open_questions || [];
  const consensus = issue?.consensus;
  const decision = issue?.decision;
  const title = topic?.title || issue?.topic || '안건';
  const showTokenBar = !readOnly && tokenThreshold > 0;
  const topicNotes = notes || [];

  return (
    <div onClick={readOnly ? undefined : onClick} style={{
      background: 'var(--surface)', borderRadius: 20, padding: 28,
      boxShadow: 'var(--shadow-card)',
      border: `1px solid ${highlighted ? 'var(--accent)' : 'var(--border)'}`,
      cursor: !readOnly && onClick ? 'pointer' : 'default',
      transition: 'border-color 120ms',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, gap: 12 }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 'var(--fs-sm)', color: active ? 'var(--accent)' : 'var(--text-3)', fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
            <MMI.sparkle width="14" height="14"/> {readOnly ? '안건' : (active ? '지금 논의 중' : '이전 안건')}
          </div>
          <div style={{ fontSize: 'var(--fs-2xl)', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em', lineHeight: 1.25 }}>
            {readOnly ? title : (
              <InlineEdit value={title}
                onCommit={(v) => onUpdate && onUpdate({ title: v })}/>
            )}
          </div>
        </div>
        {!readOnly && (
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            {active && <Pill tone="accent"><span style={{ width: 6, height: 6, borderRadius: 3, background: 'var(--accent)', animation: 'mmpulse 1.8s infinite' }}/>실시간</Pill>}
            <IconButton label="편집" onClick={(e) => { e.stopPropagation(); setEditMode(!editMode); }}><MMI.edit width="14" height="14"/></IconButton>
          </div>
        )}
      </div>

      {/* Meta */}
      <div style={{ display: 'flex', gap: 10, marginBottom: showTokenBar ? 12 : 20, fontSize: 'var(--fs-sm)', color: 'var(--text-3)' }}>
        <span>입장 <b style={{ color: 'var(--text-2)' }}>{positions.length}</b></span>
        <span style={{ opacity: 0.4 }}>·</span>
        <span>근거 <b style={{ color: 'var(--text-2)' }}>{positions.reduce((a, p) => a + (p.arguments?.length || 0), 0)}</b></span>
        <span style={{ opacity: 0.4 }}>·</span>
        <span>미결 <b style={{ color: 'var(--text-2)' }}>{openQs.length}</b></span>
      </div>

      {showTokenBar && <IssueTokenBar pendingTokens={pendingTokens} tokenThreshold={tokenThreshold}/>}

      {/* Decision banner */}
      {decision && (
        <div style={{ padding: '12px 14px', background: 'var(--positive-soft)', borderRadius: 12, marginBottom: 14, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <MMI.check width="16" height="16" style={{ color: 'var(--positive)', marginTop: 2, flexShrink: 0 }}/>
          <div>
            <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color: 'var(--positive)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 2 }}>결정</div>
            <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text)', lineHeight: 1.5 }}>{decision}</div>
          </div>
        </div>
      )}

      {/* Consensus */}
      {consensus && (
        <div style={{ padding: '12px 14px', background: 'var(--accent-soft)', borderRadius: 12, marginBottom: 14, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <MMI.sparkle width="16" height="16" style={{ color: 'var(--accent)', marginTop: 2, flexShrink: 0 }}/>
          <div>
            <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 2 }}>합의</div>
            <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text)', lineHeight: 1.5 }}>{consensus}</div>
          </div>
        </div>
      )}

      {/* Positions */}
      {positions.length === 0 ? (
        <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-4)', background: 'var(--surface-muted)', borderRadius: 12, fontSize: 'var(--fs-sm)' }}>
          발언이 쌓이면 입장이 정리돼요
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 10, marginBottom: 14 }}>
          {positions.map((p, i) => (
            <PositionRow key={i} p={p} editMode={editMode}
              onDelete={() => {
                const next = { ...issue, positions: positions.filter((_, j) => j !== i) };
                onUpdate && onUpdate(next);
              }}/>
          ))}
        </div>
      )}

      {/* Open questions */}
      {openQs.length > 0 && (
        <div style={{ padding: '12px 14px', background: 'var(--warning-soft)', borderRadius: 12, marginBottom: 16 }}>
          <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color: 'var(--warning)', marginBottom: 6, letterSpacing: '0.04em', textTransform: 'uppercase' }}>아직 확인할 것</div>
          {openQs.map((q, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '3px 0', fontSize: 'var(--fs-sm)', color: 'var(--text)' }}>
              <span style={{ color: 'var(--warning)', marginTop: 1 }}>·</span>{q}
            </div>
          ))}
        </div>
      )}

      {/* Consensus input */}
      {!readOnly && showConsensusInput && (
        <div style={{ marginBottom: 12 }}>
          <textarea value={consensusDraft} onChange={(e) => setConsensusDraft(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            placeholder="합의 내용을 적어주세요"
            style={{
              width: '100%', minHeight: 60, padding: 12, borderRadius: 10,
              background: 'var(--surface-muted)', border: '1px solid var(--border-strong)',
              color: 'var(--text)', fontSize: 'var(--fs-sm)', fontFamily: 'inherit', resize: 'vertical', outline: 'none',
            }}/>
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <Button variant="primary" size="sm" icon={<MMI.check width="12" height="12"/>}
              onClick={(e) => { e.stopPropagation(); if (consensusDraft.trim()) { onCommitConsensus && onCommitConsensus(consensusDraft.trim()); setConsensusDraft(''); setShowConsensusInput(false); } }}>
              합의로 저장
            </Button>
            <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setShowConsensusInput(false); }}>취소</Button>
          </div>
        </div>
      )}

      {/* Actions */}
      {!readOnly && !showConsensusInput && (
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="primary" size="md" icon={<MMI.check width="14" height="14"/>}
            onClick={(e) => { e.stopPropagation(); setShowConsensusInput(true); }}>
            {consensus ? '합의 수정' : '합의로 정리하기'}
          </Button>
          <Button variant="secondary" size="md" icon={<MMI.bookmark width="14" height="14"/>} onClick={(e) => e.stopPropagation()}>북마크</Button>
        </div>
      )}

      {/* Notes — 자유 메모 */}
      {(onSaveNote || topicNotes.length > 0) && (
        <NotesSection notes={topicNotes} onSave={onSaveNote} readOnly={readOnly || !onSaveNote}/>
      )}
    </div>
  );
}

function NotesSection({ notes, onSave, readOnly }) {
  const { MMI, Button } = window.MM;
  const [draft, setDraft] = icU('');
  const [saving, setSaving] = icU(false);

  async function commit() {
    const text = draft.trim();
    if (!text || saving) return;
    setSaving(true);
    try {
      await onSave(text);
      setDraft('');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid var(--divider)' }}>
      <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color: 'var(--text-3)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>메모</div>
      {notes.length > 0 && (
        <div style={{ display: 'grid', gap: 6, marginBottom: readOnly ? 0 : 12 }}>
          {notes.map((n) => (
            <div key={n.id} style={{
              padding: '10px 12px', background: 'var(--surface-muted)',
              borderRadius: 10, border: '1px solid var(--border)',
              display: 'flex', flexDirection: 'column', gap: 4,
            }}>
              <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text)', lineHeight: 1.5, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{n.text}</div>
              <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>{formatNoteTime(n.created_at)}</div>
            </div>
          ))}
        </div>
      )}
      {!readOnly && (
        <div>
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commit(); }
            }}
            placeholder="메모를 남겨두세요 (Enter로 저장, Shift+Enter 줄바꿈)"
            style={{
              width: '100%', minHeight: 44, padding: '10px 12px', borderRadius: 10,
              background: 'var(--surface-muted)', border: '1px solid var(--border)',
              color: 'var(--text)', fontSize: 'var(--fs-sm)', fontFamily: 'inherit', resize: 'vertical', outline: 'none',
            }}/>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 6 }}>
            <Button variant="secondary" size="sm" icon={<MMI.send width="12" height="12"/>}
              onClick={(e) => { e.stopPropagation(); commit(); }}
              disabled={!draft.trim() || saving}>
              {saving ? '저장 중…' : '메모 저장'}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function formatNoteTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  if (sameDay) return `${hh}:${mm}`;
  return `${d.getMonth() + 1}/${d.getDate()} ${hh}:${mm}`;
}

function PositionRow({ p, editMode, onDelete }) {
  const { Avatar, MMI, IconButton } = window.MM;
  const color = window.MM.speakerColorResolved(p.speaker);
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 12,
      padding: '14px 16px', background: 'var(--surface-muted)', borderRadius: 14,
      borderLeft: `3px solid ${color}`,
      position: 'relative',
    }}>
      <Avatar s={p.speaker} size={32}/>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: 'var(--fs-sm)', fontWeight: 700, color: 'var(--text)' }}>{p.speaker}</span>
          <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>입장</span>
        </div>
        <div style={{ fontSize: 'var(--fs-md)', fontWeight: 600, color: 'var(--text)', marginBottom: 8, lineHeight: 1.4, letterSpacing: '-0.01em' }}>
          {p.stance}
        </div>
        {(p.arguments?.length > 0 || p.evidence?.length > 0) && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {(p.arguments || []).map((a, i) => (
              <span key={i} style={{
                background: 'var(--surface)', color: 'var(--text-2)', fontSize: 'var(--fs-xs)',
                padding: '4px 10px', borderRadius: 999, border: '1px solid var(--border)', fontWeight: 500,
              }}>{a}</span>
            ))}
            {(p.evidence || []).map((e, i) => (
              <span key={`e${i}`} style={{
                background: 'var(--accent-soft)', color: 'var(--accent)', fontSize: 'var(--fs-xs)',
                padding: '4px 10px', borderRadius: 999, fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4,
              }}><MMI.link width="10" height="10"/>{e}</span>
            ))}
          </div>
        )}
      </div>
      {editMode && (
        <IconButton label="삭제" onClick={(e) => { e.stopPropagation(); onDelete && onDelete(); }} style={{ width: 28, height: 28 }}>
          <MMI.trash width="12" height="12"/>
        </IconButton>
      )}
    </div>
  );
}

function IssueTokenBar({ pendingTokens, tokenThreshold }) {
  const pending = pendingTokens || 0;
  const threshold = tokenThreshold || 500;
  const pct = Math.min(100, Math.round(pending / threshold * 100));
  const wasHighRef = React.useRef(false);
  const [analyzing, setAnalyzing] = icU(false);

  React.useEffect(() => {
    if (pending >= threshold * 0.5) {
      wasHighRef.current = true;
    } else if (pending === 0 && wasHighRef.current) {
      wasHighRef.current = false;
      setAnalyzing(true);
      const t = setTimeout(() => setAnalyzing(false), 8000);
      return () => clearTimeout(t);
    }
  }, [pending, threshold]);

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 10,
      padding: '8px 12px', marginBottom: 16,
      background: 'var(--surface-muted)', borderRadius: 10,
      border: '1px solid var(--border)',
    }}>
      <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontWeight: 600, whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        {analyzing && (
          <span style={{
            width: 10, height: 10, borderRadius: '50%',
            border: '2px solid var(--accent)', borderTopColor: 'transparent',
            animation: 'mmspin 0.8s linear infinite',
          }}/>
        )}
        {analyzing ? '쟁점 분석 중…' : `구조화 ${pending}/${threshold}`}
      </span>
      <div style={{ flex: 1, height: 4, background: 'var(--surface)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{
          width: analyzing ? '100%' : `${pct}%`, height: '100%',
          background: 'var(--accent)', borderRadius: 2,
          transition: 'width 0.4s ease',
          opacity: analyzing ? 0.5 : 1,
          backgroundImage: analyzing ? 'linear-gradient(90deg, var(--accent), var(--accent) 60%, rgba(255,255,255,0.25))' : 'none',
          backgroundSize: '200% 100%',
          animation: analyzing ? 'mmshimmer 1.6s linear infinite' : 'none',
        }}/>
      </div>
    </div>
  );
}

window.MM = window.MM || {};
window.MM.IssueCard = IssueCard;
window.MM.PositionRow = PositionRow;
window.MM.IssueTokenBar = IssueTokenBar;
window.MM.NotesSection = NotesSection;
