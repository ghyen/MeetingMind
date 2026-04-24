// MeetingMind — Right rail (AI 도우미: 알림, 참고자료, 채팅)

const { useState: rrU, useRef: rrUR, useEffect: rrUE } = React;

function RightRail({ interventions, references, onProposeNext, onDismissIntervention, onAskAi }) {
  const { MMI, Pill } = window.MM;
  const [tab, setTab] = rrU('alerts'); // alerts | refs | chat

  return (
    <div style={{ width: 340, background: 'var(--surface)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', flexShrink: 0, minHeight: 0 }}>
      <div style={{ padding: '14px 18px 0', flexShrink: 0 }}>
        <div style={{ fontSize: 'var(--fs-md)', fontWeight: 700, color: 'var(--text)' }}>AI 도우미</div>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', marginTop: 2 }}>회의 중 도움이 될 만한 제안이에요</div>
        <div style={{ display: 'flex', gap: 4, marginTop: 12, background: 'var(--surface-muted)', padding: 3, borderRadius: 10 }}>
          {[['alerts', '알림', interventions.length], ['refs', '자료', references.length], ['chat', '채팅', null]].map(([k, l, n]) => (
            <button key={k} onClick={() => setTab(k)} style={{
              flex: 1, padding: '6px 8px', fontSize: 'var(--fs-sm)', fontWeight: 600,
              background: tab === k ? 'var(--surface-alt)' : 'transparent',
              color: tab === k ? 'var(--text)' : 'var(--text-3)',
              border: 'none', borderRadius: 7, cursor: 'pointer', fontFamily: 'inherit',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 4,
            }}>{l}{n != null && n > 0 && <span style={{ fontSize: 10, padding: '0 5px', borderRadius: 6, background: tab === k ? 'var(--accent)' : 'var(--border-strong)', color: '#fff' }}>{n}</span>}</button>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: 16, minHeight: 0 }}>
        {tab === 'alerts' && <AlertsTab interventions={interventions} onProposeNext={onProposeNext} onDismiss={onDismissIntervention}/>}
        {tab === 'refs' && <RefsTab references={references}/>}
        {tab === 'chat' && <ChatTab onAsk={onAskAi}/>}
      </div>
    </div>
  );
}

function AlertsTab({ interventions, onProposeNext, onDismiss }) {
  const { MMI } = window.MM;
  if (interventions.length === 0) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-4)' }}>
        <MMI.bell width="24" height="24" style={{ opacity: 0.4, marginBottom: 8 }}/>
        <div style={{ fontSize: 'var(--fs-sm)' }}>지금은 조용해요. 회의가 진행되면 도움이 될 만한 순간에 알려드릴게요.</div>
      </div>
    );
  }
  return <>{interventions.map((iv, i) => <InterventionCard key={i} iv={iv} onPropose={onProposeNext} onDismiss={() => onDismiss && onDismiss(i)}/>)}</>;
}

function InterventionCard({ iv, onPropose, onDismiss }) {
  const level = iv.level || 'info';
  const color = level === 'warning' ? 'var(--warning)' : level === 'action_required' ? 'var(--danger)' : 'var(--accent)';
  const bg = level === 'warning' ? 'var(--warning-soft)' : level === 'action_required' ? 'var(--danger-soft)' : 'var(--accent-soft)';
  const label = {
    no_decision: '결정 지연', info_needed: '자료 필요', loop: '반복 감지',
    consensus: '합의 근접', silence: '침묵', time_over: '시간 초과',
  }[iv.trigger_type] || '알림';
  return (
    <div style={{ padding: '12px 14px', background: bg, borderRadius: 12, border: `1px solid color-mix(in oklch, ${color} 20%, transparent)`, marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ width: 6, height: 6, borderRadius: 3, background: color, animation: 'mmpulse 1.8s infinite' }}/>
        <span style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color, letterSpacing: '0.02em' }}>{label}</span>
        {iv.time && <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>{iv.time}</span>}
      </div>
      <div style={{ fontSize: 'var(--fs-sm)', lineHeight: 1.5, color: 'var(--text)', marginBottom: 10 }}>{iv.message}</div>
      <div style={{ display: 'flex', gap: 6 }}>
        <button onClick={() => onPropose && onPropose(iv)} style={{ fontSize: 'var(--fs-xs)', fontWeight: 600, background: 'var(--surface)', border: '1px solid var(--border)', padding: '5px 10px', borderRadius: 8, color: 'var(--text)', cursor: 'pointer', fontFamily: 'inherit' }}>다음 스텝 제안</button>
        <button onClick={onDismiss} style={{ fontSize: 'var(--fs-xs)', fontWeight: 600, background: 'transparent', border: 'none', padding: '5px 6px', color: 'var(--text-3)', cursor: 'pointer', fontFamily: 'inherit' }}>나중에</button>
      </div>
    </div>
  );
}

function RefsTab({ references }) {
  const { MMI } = window.MM;
  if (references.length === 0) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-4)' }}>
        <MMI.doc width="24" height="24" style={{ opacity: 0.4, marginBottom: 8 }}/>
        <div style={{ fontSize: 'var(--fs-sm)' }}>이야기가 진행되면 관련 자료를 찾아드릴게요</div>
      </div>
    );
  }
  return <>{references.map((r, i) => <ReferenceCard key={i} r={r}/>)}</>;
}

function ReferenceCard({ r }) {
  return (
    <a href={r.url || '#'} target={r.url ? '_blank' : '_self'} rel="noreferrer" onClick={(e) => { if (!r.url) e.preventDefault(); }}
      style={{ textDecoration: 'none', display: 'block' }}>
      <div style={{ padding: '12px 14px', background: 'var(--surface-muted)', borderRadius: 12, marginBottom: 8, cursor: 'pointer', transition: 'background 120ms' }}
        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--surface-alt)'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'var(--surface-muted)'}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
          <span style={{ fontSize: 9, fontWeight: 700, color: r.source === 'internal' ? 'var(--accent)' : 'var(--text-3)', background: r.source === 'internal' ? 'var(--accent-soft)' : 'var(--surface)', padding: '2px 6px', borderRadius: 4, letterSpacing: '0.04em' }}>
            {r.source === 'internal' ? '사내' : '웹'}
          </span>
          {r.relevance_score != null && <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>관련도 {Math.round((r.relevance_score || 0) * 100)}%</span>}
        </div>
        <div style={{ fontSize: 'var(--fs-sm)', fontWeight: 700, color: 'var(--text)', marginBottom: 4, lineHeight: 1.35 }}>{r.title}</div>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-2)', lineHeight: 1.5 }}>{r.snippet}</div>
      </div>
    </a>
  );
}

function ChatTab({ onAsk }) {
  const { MMI, Button } = window.MM;
  const [msgs, setMsgs] = rrU([]);
  const [input, setInput] = rrU('');
  const [busy, setBusy] = rrU(false);
  const endRef = rrUR(null);
  rrUE(() => { if (endRef.current) endRef.current.scrollIntoView({ block: 'end' }); }, [msgs]);

  async function send() {
    if (!input.trim() || busy) return;
    const q = input.trim();
    setMsgs((m) => [...m, { role: 'user', text: q }]);
    setInput(''); setBusy(true);
    try {
      const a = await (onAsk ? onAsk(q) : Promise.resolve('질문을 이해하지 못했어요.'));
      setMsgs((m) => [...m, { role: 'assistant', text: a || '답변을 찾지 못했어요.' }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: 'assistant', text: '오류: ' + (e?.message || e), error: true }]);
    } finally { setBusy(false); }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: 1, overflowY: 'auto', marginBottom: 12 }}>
        {msgs.length === 0 && (
          <div style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--text-4)' }}>
            <MMI.sparkle width="24" height="24" style={{ color: 'var(--accent)', marginBottom: 8 }}/>
            <div style={{ fontSize: 'var(--fs-sm)', marginBottom: 12 }}>회의 내용에 대해 무엇이든 물어보세요</div>
            <div style={{ display: 'grid', gap: 6 }}>
              {['지금까지 결정된 것만 알려줘', '박민호님 입장 요약해줘', '언급된 수치 정리해줘'].map((s, i) => (
                <button key={i} onClick={() => setInput(s)} style={{
                  padding: '8px 12px', background: 'var(--surface-muted)', border: '1px solid var(--border)',
                  borderRadius: 10, color: 'var(--text-2)', fontSize: 'var(--fs-xs)', fontFamily: 'inherit',
                  textAlign: 'left', cursor: 'pointer',
                }}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} style={{ marginBottom: 10, display: 'flex', flexDirection: m.role === 'user' ? 'row-reverse' : 'row' }}>
            <div style={{
              maxWidth: '85%', padding: '8px 12px', borderRadius: 12,
              background: m.role === 'user' ? 'var(--accent)' : m.error ? 'var(--danger-soft)' : 'var(--surface-alt)',
              color: m.role === 'user' ? '#fff' : m.error ? 'var(--danger)' : 'var(--text)',
              fontSize: 'var(--fs-sm)', lineHeight: 1.55, whiteSpace: 'pre-wrap',
            }}>{m.text}</div>
          </div>
        ))}
        {busy && <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', padding: '4px 12px' }}>생각하는 중…</div>}
        <div ref={endRef}/>
      </div>
      <div style={{ display: 'flex', gap: 6, padding: '8px', background: 'var(--surface-muted)', borderRadius: 12, border: '1px solid var(--border)' }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
          placeholder="무엇이든 물어보세요"
          style={{ flex: 1, minWidth: 0, background: 'transparent', border: 'none', color: 'var(--text)', outline: 'none', fontSize: 'var(--fs-sm)', fontFamily: 'inherit', padding: '4px 8px' }}/>
        <button onClick={send} disabled={!input.trim() || busy} style={{
          width: 30, height: 30, border: 'none', borderRadius: 8,
          background: input.trim() && !busy ? 'var(--accent)' : 'var(--border)', color: '#fff',
          cursor: input.trim() && !busy ? 'pointer' : 'not-allowed',
          display: 'grid', placeItems: 'center',
        }}><MMI.send width="14" height="14"/></button>
      </div>
    </div>
  );
}

window.MM = window.MM || {};
window.MM.RightRail = RightRail;
