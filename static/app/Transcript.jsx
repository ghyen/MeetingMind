// MeetingMind — Transcript panel (왼쪽, 펼침/접힘)
// 화자 클릭 → 인라인 편집, 발화 클릭 → 쟁점으로 이동 이벤트

const { useState: tU, useEffect: tUE, useRef: tUR } = React;

function TranscriptPanel({ utterances, live, speakerNames, onRenameSpeaker, onJumpToIssue, partialText, partialSpeaker, analyzing, open, onToggleOpen, bookmarks = [], onBookmark }) {
  const { MMI, Avatar, InlineEdit, Pill } = window.MM;
  const scrollRef = tUR(null);
  const [query, setQuery] = tU('');
  tUE(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [utterances.length, partialText]);

  const filtered = query
    ? utterances.filter((u) => u.text.includes(query) || (speakerNames[u.speaker] || '').includes(query))
    : utterances;

  if (!open) {
    return (
      <div onClick={onToggleOpen} style={{
        width: 48, background: 'var(--surface)', borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 16, gap: 14,
        cursor: 'pointer',
      }}>
        <div style={{ width: 32, height: 32, borderRadius: 10, background: 'var(--accent-soft)', color: 'var(--accent)', display: 'grid', placeItems: 'center' }}>
          <MMI.doc width="16" height="16"/>
        </div>
        <div style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)', fontSize: 12, fontWeight: 600, color: 'var(--text-2)', letterSpacing: '0.02em' }}>
          스크립트 · {utterances.length}
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: 340, background: 'var(--surface)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', minHeight: 0, flexShrink: 0 }}>
      <div style={{ padding: '14px 18px 10px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 'var(--fs-md)', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' }}>실시간 스크립트</div>
          <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', marginTop: 2 }}>
            {utterances.length}개 발화 · {Object.keys(speakerNames || {}).length || 0}명
            {analyzing && <span style={{ marginLeft: 8, color: 'var(--accent)' }}>● 분석 중</span>}
          </div>
        </div>
        <button onClick={onToggleOpen} style={{ border: 'none', background: 'transparent', color: 'var(--text-3)', cursor: 'pointer', padding: 6, borderRadius: 6, display: 'grid', placeItems: 'center' }}
          title="접기">
          <MMI.panel width="18" height="18"/>
        </button>
      </div>

      <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: 'var(--surface-muted)', borderRadius: 10, color: 'var(--text-3)' }}>
          <MMI.search width="14" height="14"/>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="스크립트 검색"
            style={{ flex: 1, minWidth: 0, background: 'transparent', border: 'none', color: 'var(--text)', outline: 'none', fontSize: 'var(--fs-sm)', fontFamily: 'inherit' }}/>
          {query && <button onClick={() => setQuery('')} style={{ border: 'none', background: 'transparent', color: 'var(--text-3)', cursor: 'pointer', padding: 2, display: 'grid', placeItems: 'center' }}><MMI.close width="12" height="12"/></button>}
        </div>
      </div>

      <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto' }}>
        {filtered.length === 0 && !live && (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-4)' }}>
            <MMI.mic width="24" height="24" style={{ opacity: 0.4, marginBottom: 8 }}/>
            <div style={{ fontSize: 'var(--fs-sm)' }}>녹음을 시작하면 여기에 실시간으로 쌓여요</div>
          </div>
        )}
        {filtered.map((u, i) => (
          <TranscriptItem key={i} u={u} speakerName={speakerNames[u.speaker]} highlighted={bookmarks.includes(i)}
            onRename={(name) => onRenameSpeaker(u.speaker, name)}
            onClick={() => onJumpToIssue && onJumpToIssue(u)}
            onBookmark={() => onBookmark && onBookmark(i)}/>
        ))}
        {live && partialText && (
          <LiveUtterance text={partialText} speaker={partialSpeaker} speakerName={speakerNames[partialSpeaker]}/>
        )}
        <div style={{ height: 40 }}/>
      </div>
    </div>
  );
}

function TranscriptItem({ u, speakerName, onRename, onClick, highlighted, onBookmark }) {
  const { Avatar, InlineEdit, MMI } = window.MM;
  const [hover, setHover] = tU(false);
  return (
    <div onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{
        padding: '10px 18px', display: 'flex', gap: 10,
        background: highlighted ? 'var(--accent-soft)' : hover ? 'var(--surface-alt)' : 'transparent',
        cursor: 'pointer', transition: 'background 100ms', position: 'relative',
      }}>
      <div onClick={onClick} style={{ display: 'flex', gap: 10, flex: 1, minWidth: 0 }}>
        <Avatar s={u.speaker} size={26}/>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 2 }}>
            <span style={{ fontSize: 'var(--fs-sm)', fontWeight: 700, color: 'var(--text)' }} onClick={(e) => e.stopPropagation()}>
              <InlineEdit value={speakerName || u.speaker} onCommit={onRename} placeholder="이름 없음"/>
            </span>
            <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>{u.time}</span>
          </div>
          <div style={{ fontSize: 'var(--fs-sm)', lineHeight: 1.55, color: 'var(--text)', wordBreak: 'break-word' }}>{u.text}</div>
        </div>
      </div>
      {hover && (
        <button onClick={(e) => { e.stopPropagation(); onBookmark && onBookmark(); }}
          style={{ position: 'absolute', top: 8, right: 8, border: 'none', background: 'var(--surface)', color: highlighted ? 'var(--accent)' : 'var(--text-3)', cursor: 'pointer', padding: 4, borderRadius: 6, display: 'grid', placeItems: 'center' }}
          title="북마크">
          <MMI.bookmark width="14" height="14"/>
        </button>
      )}
    </div>
  );
}

function LiveUtterance({ text, speaker, speakerName }) {
  const { Avatar } = window.MM;
  return (
    <div style={{ padding: '10px 18px', display: 'flex', gap: 10, background: 'var(--accent-soft)', borderLeft: '3px solid var(--accent)' }}>
      <Avatar s={speaker || 'A'} size={26}/>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
          <span style={{ fontSize: 'var(--fs-sm)', fontWeight: 700, color: 'var(--text)' }}>{speakerName || speaker || '화자 식별 중'}</span>
          <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--accent)', fontWeight: 600 }}>듣는 중</span>
          <WaveBars/>
        </div>
        <div style={{ fontSize: 'var(--fs-sm)', lineHeight: 1.55, color: 'var(--text-2)', fontStyle: 'italic' }}>{text}</div>
      </div>
    </div>
  );
}

function WaveBars() {
  return (
    <span style={{ display: 'inline-flex', gap: 2, alignItems: 'center', height: 12 }}>
      {[0.6, 1, 0.8, 0.4, 0.7].map((h, i) => (
        <span key={i} style={{
          width: 2, height: `${h * 12}px`, background: 'var(--accent)', borderRadius: 1,
          animation: `mmwave ${0.6 + i * 0.1}s ease-in-out infinite alternate`,
        }}/>
      ))}
    </span>
  );
}

window.MM = window.MM || {};
window.MM.TranscriptPanel = TranscriptPanel;
window.MM.TranscriptItem = TranscriptItem;
window.MM.LiveUtterance = LiveUtterance;
window.MM.WaveBars = WaveBars;
