// MeetingMind — Issue card (쟁점 카드)
// Position Chip 스타일. 합의/북마크/편집 인터랙션.

const { useState: icU } = React;

function IssueCard({ issue, topicId, topic, active, onCommitConsensus, onAddOpen, onUpdate, onClick, highlighted }) {
  const { MMI, Avatar, Pill, Button, InlineEdit, IconButton } = window.MM;
  const [editMode, setEditMode] = icU(false);
  const [consensusDraft, setConsensusDraft] = icU('');
  const [showConsensusInput, setShowConsensusInput] = icU(false);

  const positions = issue?.positions || [];
  const openQs = issue?.open_questions || [];
  const consensus = issue?.consensus;
  const decision = issue?.decision;

  return (
    <div onClick={onClick} style={{
      background: 'var(--surface)', borderRadius: 20, padding: 28,
      boxShadow: 'var(--shadow-card)',
      border: `1px solid ${highlighted ? 'var(--accent)' : 'var(--border)'}`,
      cursor: onClick ? 'pointer' : 'default',
      transition: 'border-color 120ms',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, gap: 12 }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontSize: 'var(--fs-sm)', color: active ? 'var(--accent)' : 'var(--text-3)', fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
            <MMI.sparkle width="14" height="14"/> {active ? '지금 논의 중' : '이전 안건'}
          </div>
          <div style={{ fontSize: 'var(--fs-2xl)', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em', lineHeight: 1.25 }}>
            <InlineEdit value={topic?.title || issue?.topic || '안건'}
              onCommit={(v) => onUpdate && onUpdate({ title: v })}/>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          {active && <Pill tone="accent"><span style={{ width: 6, height: 6, borderRadius: 3, background: 'var(--accent)', animation: 'mmpulse 1.8s infinite' }}/>실시간</Pill>}
          <IconButton label="편집" onClick={(e) => { e.stopPropagation(); setEditMode(!editMode); }}><MMI.edit width="14" height="14"/></IconButton>
        </div>
      </div>

      {/* Meta */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, fontSize: 'var(--fs-sm)', color: 'var(--text-3)' }}>
        <span>입장 <b style={{ color: 'var(--text-2)' }}>{positions.length}</b></span>
        <span style={{ opacity: 0.4 }}>·</span>
        <span>근거 <b style={{ color: 'var(--text-2)' }}>{positions.reduce((a, p) => a + (p.arguments?.length || 0), 0)}</b></span>
        <span style={{ opacity: 0.4 }}>·</span>
        <span>미결 <b style={{ color: 'var(--text-2)' }}>{openQs.length}</b></span>
      </div>

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
      {showConsensusInput && (
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
      {!showConsensusInput && (
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="primary" size="md" icon={<MMI.check width="14" height="14"/>}
            onClick={(e) => { e.stopPropagation(); setShowConsensusInput(true); }}>
            {consensus ? '합의 수정' : '합의로 정리하기'}
          </Button>
          <Button variant="secondary" size="md" icon={<MMI.bookmark width="14" height="14"/>} onClick={(e) => e.stopPropagation()}>북마크</Button>
        </div>
      )}
    </div>
  );
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

window.MM = window.MM || {};
window.MM.IssueCard = IssueCard;
window.MM.PositionRow = PositionRow;
