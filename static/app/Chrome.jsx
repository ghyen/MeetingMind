// MeetingMind — Top bar, Sidebar, Record bar, Agenda tabs, Start screen, Summary, Settings

const { useState: sU, useEffect: sUE } = React;

function calibrationNoiseLabel(threshold) {
  if (threshold == null) return '';
  if (threshold < 0.01) return '매우 조용함';
  if (threshold < 0.03) return '보통';
  if (threshold < 0.06) return '소음 있음';
  return '소음 많음';
}

// ─── Top bar ───────────────────────────────────────
function TopBar({ title, onTitleChange, onOpenLogs, analyzing, connected, recording, isDark, onToggleTheme }) {
  const { MMI, IconButton, Pill, InlineEdit } = window.MM;
  return (
    <div style={{
      height: 56, padding: '0 20px', flexShrink: 0,
      background: 'var(--surface)', borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', gap: 16,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 26, height: 26, borderRadius: 8, background: 'var(--accent)', color: '#fff', display: 'grid', placeItems: 'center', fontWeight: 800, fontSize: 14, letterSpacing: '-0.02em' }}>M</div>
        <span style={{ fontSize: 'var(--fs-md)', fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.02em' }}>MeetingMind</span>
      </div>
      <div style={{ width: 1, height: 20, background: 'var(--border)' }}/>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', lineHeight: 1 }}>
          {recording ? '녹음 중' : '대기'}
        </div>
        <div style={{ fontSize: 'var(--fs-sm)', fontWeight: 700, color: 'var(--text)', marginTop: 2 }}>
          {onTitleChange
            ? <InlineEdit value={title || '새 회의'} onCommit={onTitleChange} placeholder="회의 제목"/>
            : (title || '새 회의')}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {analyzing && <Pill tone="accent" size="xs">분석 중</Pill>}
        {!connected && <Pill tone="warning" size="xs">재연결 중</Pill>}
        <IconButton label={isDark ? '라이트 모드' : '다크 모드'} onClick={onToggleTheme}>
          {isDark ? <MMI.sun width="16" height="16"/> : <MMI.moon width="16" height="16"/>}
        </IconButton>
        <IconButton label="서버 로그" onClick={onOpenLogs}><MMI.terminal width="16" height="16"/></IconButton>
      </div>
    </div>
  );
}

// ─── Sidebar (meeting history) ─────────────────────
function Sidebar({ meetings, activeId, onSelect, onNew, open = true, onToggleOpen }) {
  const { MMI, Button, IconButton } = window.MM;
  if (!open) {
    return (
      <div style={{
        width: 48, background: 'var(--surface-muted)', borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 12, gap: 10,
        flexShrink: 0,
      }}>
        <button onClick={onToggleOpen} title="사이드바 펼치기" style={{
          width: 32, height: 32, borderRadius: 8, border: 'none', background: 'transparent',
          color: 'var(--text-2)', cursor: 'pointer', display: 'grid', placeItems: 'center',
        }}>
          <MMI.panel width="18" height="18"/>
        </button>
        <button onClick={onNew} title="새 회의" style={{
          width: 32, height: 32, borderRadius: 8, border: 'none', background: 'var(--accent)',
          color: '#fff', cursor: 'pointer', display: 'grid', placeItems: 'center',
        }}>
          <MMI.plus width="14" height="14"/>
        </button>
      </div>
    );
  }
  return (
    <div style={{
      width: 260, background: 'var(--surface-muted)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', flexShrink: 0, minHeight: 0,
    }}>
      <div style={{ padding: '10px 12px 4px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>회의 히스토리</div>
        <button onClick={onToggleOpen} title="사이드바 접기" style={{
          border: 'none', background: 'transparent', color: 'var(--text-3)', cursor: 'pointer',
          padding: 6, borderRadius: 6, display: 'grid', placeItems: 'center',
        }}>
          <MMI.panel width="16" height="16"/>
        </button>
      </div>
      <div style={{ padding: '4px 12px 8px' }}>
        <Button variant="primary" size="md" icon={<MMI.plus width="14" height="14"/>} style={{ width: '100%' }} onClick={onNew}>새 회의 시작</Button>
      </div>
      <div style={{ padding: '4px 12px 8px', fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
        최근 회의
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px 16px' }}>
        {meetings.length === 0 && <div style={{ padding: 16, fontSize: 'var(--fs-sm)', color: 'var(--text-4)', textAlign: 'center' }}>아직 회의가 없어요</div>}
        {meetings.map((m) => {
          const active = m.id === activeId;
          return (
            <div key={m.id} onClick={() => onSelect && onSelect(m.id)} style={{
              padding: '10px 12px', borderRadius: 10, marginBottom: 2,
              background: active ? 'var(--surface)' : 'transparent',
              border: active ? '1px solid var(--border)' : '1px solid transparent',
              cursor: 'pointer',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                {m.active && <span style={{ width: 6, height: 6, borderRadius: 3, background: 'var(--danger)', animation: 'mmpulse 1.8s infinite' }}/>}
                <span style={{ fontSize: 'var(--fs-sm)', fontWeight: 700, color: 'var(--text)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{m.title || '제목 없음'}</span>
              </div>
              <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', display: 'flex', gap: 6 }}>
                <span>{m.date || m.created_at || ''}</span>
                {m.duration && <><span>·</span><span>{m.duration}</span></>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Agenda tabs ───────────────────────────────────
function AgendaTabs({ topics, activeId, onSelect, onAdd, onRename }) {
  const { MMI, InlineEdit } = window.MM;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
      <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', marginRight: 4 }}>안건</div>
      {topics.map((t, i) => {
        const active = t.id === activeId;
        return (
          <button key={t.id} onClick={() => onSelect && onSelect(t.id)} style={{
            padding: '6px 14px', borderRadius: 999, fontSize: 'var(--fs-sm)', fontWeight: 600,
            background: active ? 'var(--accent)' : 'var(--surface-alt)',
            color: active ? '#fff' : 'var(--text-2)',
            border: 'none', cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'inherit',
          }}>
            <span style={{ opacity: 0.7, fontVariantNumeric: 'tabular-nums' }}>{String(i + 1).padStart(2, '0')}</span>
            <span onClick={(e) => e.stopPropagation()}>
              <InlineEdit value={t.title} onCommit={(v) => onRename && onRename(t.id, v)}/>
            </span>
            {t.end_time == null && <span style={{ width: 5, height: 5, borderRadius: 3, background: active ? '#fff' : 'var(--accent)', animation: 'mmpulse 1.8s infinite' }}/>}
          </button>
        );
      })}
      {onAdd && (
        <button onClick={onAdd} style={{
          padding: '6px 12px', borderRadius: 999, fontSize: 'var(--fs-sm)', fontWeight: 600,
          background: 'transparent', color: 'var(--text-3)', border: '1px dashed var(--border-strong)',
          cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4, fontFamily: 'inherit',
        }}>
          <MMI.plus width="12" height="12"/>안건 추가
        </button>
      )}
    </div>
  );
}

// ─── Record bar (floating pill) ────────────────────
function RecordBar({ recording, onStop, onPause, paused, timer, level, muted, onToggleMute, onEnd, onCalibrate, calibrationState = 'idle', calibrationThreshold = null }) {
  const { MMI, Button, Pill } = window.MM;
  const calibrating = calibrationState === 'calibrating';
  const applying = calibrationState === 'pending';
  const calibrated = calibrationState === 'done';
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 14,
      padding: '10px 16px 10px 10px', background: 'var(--bg-elevated)',
      borderRadius: 999, boxShadow: 'var(--shadow-lifted)',
      border: '1px solid var(--border-strong)',
    }}>
      <button onClick={onPause} style={{
        width: 44, height: 44, borderRadius: 22,
        background: paused ? 'var(--accent)' : 'var(--danger)',
        color: '#fff', border: 'none', cursor: 'pointer',
        display: 'grid', placeItems: 'center',
        boxShadow: paused ? 'none' : `0 0 0 4px rgba(240, 68, 56, 0.24)`,
        animation: paused ? 'none' : 'mmpulse 2s ease-in-out infinite',
      }}>
        {paused ? <MMI.play width="16" height="16"/> : <MMI.pause width="16" height="16"/>}
      </button>
      <div>
        <div style={{ fontSize: 'var(--fs-xs)', color: paused ? 'var(--text-3)' : 'var(--danger)', fontWeight: 700, letterSpacing: '0.02em', textTransform: 'uppercase' }}>
          {paused ? '일시정지' : 'REC'}
        </div>
        <div style={{ fontSize: 'var(--fs-lg)', fontWeight: 700, color: 'var(--text)', fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.02em' }}>
          {timer}
        </div>
      </div>
      <div style={{ width: 1, height: 28, background: 'var(--border)' }}/>
      <MicLevel level={level} active={recording && !paused && !muted}/>
      <div style={{ width: 1, height: 28, background: 'var(--border)' }}/>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <Button variant={calibrated ? 'outline' : 'secondary'} size="sm" onClick={onCalibrate}
          disabled={!onCalibrate || calibrating || applying || !recording}
          style={{ minWidth: 76 }}
          icon={calibrated ? <MMI.check width="12" height="12"/> : <MMI.settings width="12" height="12"/>}>
          {applying ? '적용 중' : calibrating ? '측정 중' : '보정'}
        </Button>
        {calibrated && <Pill tone="positive" size="xs">{calibrationThreshold != null ? calibrationThreshold.toFixed(4) : '완료'}</Pill>}
        {calibrationState === 'error' && <Pill tone="danger" size="xs">실패</Pill>}
      </div>
      <div style={{ width: 1, height: 28, background: 'var(--border)' }}/>
      <button onClick={onToggleMute} style={{
        padding: '8px 12px', borderRadius: 999, border: '1px solid var(--border-strong)',
        background: muted ? 'var(--danger-soft)' : 'transparent',
        color: muted ? 'var(--danger)' : 'var(--text-2)',
        fontSize: 'var(--fs-sm)', fontWeight: 600,
        cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: 'inherit',
      }}>
        {muted ? <MMI.micOff width="14" height="14"/> : <MMI.mic width="14" height="14"/>}
        {muted ? '음소거됨' : '마이크'}
      </button>
      <Button variant="danger" size="sm" onClick={onEnd} icon={<MMI.stop width="12" height="12"/>}>회의 종료</Button>
    </div>
  );
}

function MicLevel({ level, active }) {
  // 14 bars, animated from level (0-1)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 2, width: 80, height: 24 }}>
      {Array.from({ length: 14 }).map((_, i) => {
        const threshold = (i + 1) / 14;
        const lit = active && level > threshold * 0.5;
        const h = active ? (4 + (level * 20) * (0.5 + Math.sin((Date.now() / 100 + i) * 0.5) * 0.3)) : 4;
        return <span key={i} style={{
          flex: 1, height: `${Math.min(h, 22)}px`, borderRadius: 1,
          background: lit ? `color-mix(in oklch, var(--accent) ${40 + i * 4}%, var(--border))` : 'var(--border)',
          transition: 'height 100ms ease, background 100ms',
        }}/>;
      })}
    </div>
  );
}

// ─── Start screen (마이크 체크 + 시작) ─────────────
function StartScreen({ onStart, onUpload }) {
  const { MMI, Button } = window.MM;
  const [stage, setStage] = sU('ready'); // ready | checking | ok | error
  const [level, setLevel] = sU(0);
  const [err, setErr] = sU('');
  const [title, setTitle] = sU('');
  const [calibrationState, setCalibrationState] = sU('idle'); // idle | calibrating | done | error
  const [calibrationThreshold, setCalibrationThreshold] = sU(null);
  const streamRef = React.useRef(null);
  const ctxRef = React.useRef(null);
  const analyserRef = React.useRef(null);
  const rafRef = React.useRef(null);

  async function checkMic() {
    setStage('checking'); setErr('');
    setCalibrationState('idle');
    setCalibrationThreshold(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      ctxRef.current = ctx;
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      analyserRef.current = analyser;
      src.connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const loop = () => {
        analyser.getByteTimeDomainData(data);
        let peak = 0;
        for (let i = 0; i < data.length; i++) { const v = Math.abs(data[i] - 128) / 128; if (v > peak) peak = v; }
        setLevel(peak);
        rafRef.current = requestAnimationFrame(loop);
      };
      loop();
      setStage('ok');
    } catch (e) {
      setErr(e.message || '마이크 권한이 필요해요');
      setStage('error');
    }
  }

  async function calibrateMic() {
    const analyser = analyserRef.current;
    if (!analyser) return;
    setCalibrationState('calibrating');
    setCalibrationThreshold(null);
    const data = new Uint8Array(analyser.frequencyBinCount);
    const samples = [];
    const started = performance.now();
    await new Promise((resolve) => {
      const tick = () => {
        if (analyserRef.current !== analyser) { resolve(); return; }
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        samples.push(Math.sqrt(sum / data.length));
        if (performance.now() - started >= 2000) resolve();
        else setTimeout(tick, 100);
      };
      tick();
    });
    if (!samples.length || analyserRef.current !== analyser) {
      setCalibrationState('error');
      return;
    }
    const avgRms = samples.reduce((sum, v) => sum + v, 0) / samples.length;
    const threshold = Math.max(avgRms * 3, 0.005);
    setCalibrationThreshold(threshold);
    setCalibrationState('done');
  }

  function cleanup() {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (streamRef.current) streamRef.current.getTracks().forEach((t) => t.stop());
    if (ctxRef.current) ctxRef.current.close();
    streamRef.current = ctxRef.current = analyserRef.current = null;
  }

  React.useEffect(() => cleanup, []);

  function start() {
    cleanup();
    onStart && onStart({ title: title.trim() || null, calibrationThreshold });
  }

  return (
    <div style={{ flex: 1, display: 'grid', placeItems: 'center', overflow: 'auto', padding: 32 }}>
      <div style={{ maxWidth: 520, width: '100%', display: 'grid', gap: 28, textAlign: 'center' }}>
        <div style={{ width: 72, height: 72, borderRadius: 24, background: 'var(--accent)', color: '#fff', display: 'grid', placeItems: 'center', margin: '0 auto', boxShadow: '0 12px 40px rgba(49, 130, 246, 0.4)' }}>
          <MMI.mic width="32" height="32"/>
        </div>
        <div>
          <div style={{ fontSize: 'var(--fs-3xl)', fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.03em', lineHeight: 1.15 }}>
            회의 시작할까요?
          </div>
          <div style={{ fontSize: 'var(--fs-md)', color: 'var(--text-2)', marginTop: 12, lineHeight: 1.55 }}>
            마이크를 체크한 뒤 시작해요. 쟁점과 결정은 MeetingMind가 실시간으로 정리해드려요.
          </div>
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20, textAlign: 'left' }}>
          <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color: 'var(--text-3)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 8 }}>회의 제목 (선택)</div>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="예: 결제 시스템 리뉴얼 Kickoff"
            style={{ width: '100%', padding: '10px 14px', background: 'var(--surface-muted)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text)', fontSize: 'var(--fs-base)', fontFamily: 'inherit', outline: 'none' }}/>
        </div>

        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{ fontSize: 'var(--fs-sm)', fontWeight: 700, color: 'var(--text)' }}>마이크 체크</div>
            {stage === 'ok' && <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--positive)', fontWeight: 600 }}>● 소리가 잘 들어와요</span>}
            {stage === 'error' && <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger)' }}>● {err}</span>}
          </div>
          <MicLevel level={level} active={stage === 'ok'}/>
          {stage === 'ready' && <Button variant="secondary" size="sm" onClick={checkMic} style={{ marginTop: 12 }} icon={<MMI.mic width="12" height="12"/>}>마이크 확인하기</Button>}
          {stage === 'checking' && <div style={{ marginTop: 8, fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>권한을 요청하는 중...</div>}
          {stage === 'error' && <Button variant="secondary" size="sm" onClick={checkMic} style={{ marginTop: 12 }}>다시 시도</Button>}
          {stage === 'ok' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              <Button variant={calibrationState === 'done' ? 'outline' : 'secondary'} size="sm"
                onClick={calibrateMic} disabled={calibrationState === 'calibrating'}
                icon={calibrationState === 'done' ? <MMI.check width="12" height="12"/> : <MMI.settings width="12" height="12"/>}>
                {calibrationState === 'calibrating' ? '소음 측정 중' : '소음 보정'}
              </Button>
              {calibrationState === 'done' && (
                <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--positive)', fontWeight: 600 }}>
                  완료 · {calibrationNoiseLabel(calibrationThreshold)} · {calibrationThreshold.toFixed(4)}
                </span>
              )}
              {calibrationState === 'error' && (
                <span style={{ fontSize: 'var(--fs-xs)', color: 'var(--danger)', fontWeight: 600 }}>보정 실패</span>
              )}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button variant="primary" size="lg" onClick={start} disabled={stage !== 'ok'}
            icon={<MMI.play width="14" height="14"/>}>
            회의 시작하기
          </Button>
          <Button variant="secondary" size="lg" onClick={onUpload} icon={<MMI.upload width="14" height="14"/>}>
            파일 업로드
          </Button>
        </div>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)' }}>언제든지 일시정지할 수 있어요. 음성은 회의 중에만 처리돼요.</div>
      </div>
    </div>
  );
}

// ─── Settings modal ────────────────────────────────
function SettingsModal({ open, onClose, models, activeModel, onSetModel, onReset }) {
  const { MMI, Button, IconButton } = window.MM;
  if (!open) return null;
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'grid', placeItems: 'center', padding: 24 }}>
      <div onClick={(e) => e.stopPropagation()} style={{ width: 480, maxWidth: '100%', background: 'var(--bg-elevated)', borderRadius: 20, border: '1px solid var(--border)', boxShadow: 'var(--shadow-lifted)', overflow: 'hidden' }}>
        <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: 'var(--fs-lg)', fontWeight: 800, color: 'var(--text)' }}>설정</div>
          <IconButton label="닫기" onClick={onClose}><MMI.close width="14" height="14"/></IconButton>
        </div>
        <div style={{ padding: 22, display: 'grid', gap: 20 }}>
          <div>
            <div style={{ fontSize: 'var(--fs-sm)', fontWeight: 700, color: 'var(--text)', marginBottom: 6 }}>LLM 모델</div>
            <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', marginBottom: 10 }}>분석에 사용할 언어 모델을 선택해요</div>
            {models && Object.entries(models.providers || {}).map(([prov, list]) => (
              <div key={prov} style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color: 'var(--text-3)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 4 }}>{prov}</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {list.map((m) => {
                    const active = activeModel && activeModel.provider === prov && activeModel.model === m;
                    return (
                      <button key={m} onClick={() => onSetModel && onSetModel(prov, m)} style={{
                        padding: '6px 10px', borderRadius: 8, fontSize: 'var(--fs-xs)', fontWeight: 600, cursor: 'pointer',
                        background: active ? 'var(--accent)' : 'var(--surface-alt)',
                        color: active ? '#fff' : 'var(--text-2)',
                        border: 'none', fontFamily: 'inherit',
                      }}>{m}</button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
          <div style={{ borderTop: '1px solid var(--border)', paddingTop: 16 }}>
            <div style={{ fontSize: 'var(--fs-sm)', fontWeight: 700, color: 'var(--text)', marginBottom: 6 }}>회의 상태 초기화</div>
            <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', marginBottom: 10 }}>진행 중인 회의를 종료하고 상태를 비워요</div>
            <Button variant="danger" size="sm" onClick={onReset} icon={<MMI.trash width="12" height="12"/>}>초기화</Button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Summary-in-progress indicator ────────────────
function SummaryProgress() {
  const [sec, setSec] = sU(0);
  sUE(() => {
    const id = setInterval(() => setSec((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);
  // 60초까지는 선형으로 95%까지 채우고, 그 이후는 95%에서 대기 (실제 완료는 서버 응답에 의존)
  const pct = Math.min(95, Math.round((sec / 60) * 95));
  const phase = sec < 8 ? '발화 정리 중…' : sec < 25 ? '쟁점 합치고 결정 뽑는 중…' : '회의록 다듬는 중…';
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
        <div style={{ fontSize: 'var(--fs-md)', fontWeight: 700, color: 'var(--text)' }}>회의록 생성 중</div>
        <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>{sec}s</div>
      </div>
      <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-2)', marginBottom: 14 }}>{phase}</div>
      <div style={{ height: 8, background: 'var(--surface-muted)', borderRadius: 999, overflow: 'hidden', border: '1px solid var(--border)' }}>
        <div style={{
          width: `${pct}%`, height: '100%', background: 'var(--accent)',
          borderRadius: 999, transition: 'width 0.6s ease',
          backgroundImage: 'linear-gradient(90deg, var(--accent), var(--accent) 60%, rgba(255,255,255,0.25))',
          backgroundSize: '200% 100%', animation: 'mmshimmer 1.6s linear infinite',
        }}/>
      </div>
    </div>
  );
}

// ─── Post-meeting summary screen ──────────────────
function SummaryScreen({ meeting, summary, loading, onBack, onNew, issues, topics, notesByTopic }) {
  const { MMI, Button, Avatar, IssueCard } = window.MM;
  if (!meeting) return null;
  const issueCards = (topics || [])
    .map((t) => {
      const iss = issues?.[t.id];
      if (!iss) return null;
      const topicNotes = notesByTopic?.[t.id] || [];
      const hasContent = (iss.positions?.length || 0) > 0 || iss.consensus || iss.decision || (iss.open_questions?.length || 0) > 0 || topicNotes.length > 0;
      if (!hasContent) return null;
      return <IssueCard key={t.id} issue={iss} topicId={t.id} topic={t} active={false} readOnly={true} notes={topicNotes}/>;
    })
    .filter(Boolean);
  return (
    <div style={{ flex: 1, overflow: 'auto', padding: '32px 40px' }}>
      <div style={{ maxWidth: 720, margin: '0 auto', display: 'grid', gap: 20 }}>
        <div>
          <button onClick={onBack} style={{ border: 'none', background: 'transparent', color: 'var(--text-3)', cursor: 'pointer', fontSize: 'var(--fs-sm)', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: 4, padding: 0, marginBottom: 16 }}>
            <MMI.chevL width="14" height="14"/> 회의 목록
          </button>
          <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', fontWeight: 700, letterSpacing: '0.04em' }}>회의 완료</div>
          <div style={{ fontSize: 'var(--fs-3xl)', fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.03em', marginTop: 6, lineHeight: 1.2 }}>{meeting.title || '제목 없음'}</div>
          {meeting.created_at && <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)', marginTop: 6 }}>{meeting.created_at}</div>}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="primary" icon={<MMI.doc width="14" height="14"/>}>회의록 공유</Button>
          <Button variant="secondary" icon={<MMI.upload width="14" height="14"/>}>PDF로 저장</Button>
          <Button variant="ghost" onClick={onNew}>새 회의 시작</Button>
        </div>

        {loading && <SummaryProgress/>}
        {!loading && !summary && (
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 24, color: 'var(--text-3)', fontSize: 'var(--fs-sm)' }}>
            요약을 생성하지 못했어요. 네트워크나 LLM 설정을 확인한 뒤 새 회의로 다시 시도해 보세요.
          </div>
        )}

        {summary?.one_line && (
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 24 }}>
            <div style={{ fontSize: 'var(--fs-xs)', fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 8 }}>한 줄 요약</div>
            <div style={{ fontSize: 'var(--fs-lg)', fontWeight: 600, color: 'var(--text)', lineHeight: 1.55 }}>{summary.one_line}</div>
          </div>
        )}

        {issueCards.length > 0 && (
          <div style={{ display: 'grid', gap: 14 }}>
            <div style={{ fontSize: 'var(--fs-md)', fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>쟁점 구조화</div>
            <div style={{ display: 'grid', gap: 20 }}>{issueCards}</div>
          </div>
        )}

        {summary?.decisions && summary.decisions.length > 0 && (
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 24 }}>
            <div style={{ fontSize: 'var(--fs-md)', fontWeight: 700, color: 'var(--text)', marginBottom: 14 }}>결정 사항</div>
            {summary.decisions.map((d, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, padding: '10px 0', borderTop: i === 0 ? 'none' : '1px solid var(--divider)' }}>
                <div style={{ width: 20, height: 20, borderRadius: 10, background: 'var(--positive-soft)', color: 'var(--positive)', display: 'grid', placeItems: 'center', flexShrink: 0, marginTop: 2 }}>
                  <MMI.check width="12" height="12"/>
                </div>
                <div style={{ fontSize: 'var(--fs-base)', color: 'var(--text)', lineHeight: 1.5 }}>{d}</div>
              </div>
            ))}
          </div>
        )}

        {summary?.action_items && summary.action_items.length > 0 && (
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 16, padding: 24 }}>
            <div style={{ fontSize: 'var(--fs-md)', fontWeight: 700, color: 'var(--text)', marginBottom: 14 }}>액션 아이템</div>
            {summary.action_items.map((a, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '12px 0', borderTop: i === 0 ? 'none' : '1px solid var(--divider)' }}>
                <Avatar s={a.speaker || 'A'} size={30}/>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 'var(--fs-base)', fontWeight: 600, color: 'var(--text)' }}>{a.task || a.title}</div>
                  <div style={{ fontSize: 'var(--fs-sm)', color: 'var(--text-3)', marginTop: 2 }}>{a.who || a.speaker} {a.due && `· ${a.due}`}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Server log modal ─────────────────────────────
function LogsModal({ open, onClose, logs, onClear }) {
  const { MMI, Button, IconButton } = window.MM;
  const scrollRef = React.useRef(null);
  sUE(() => {
    if (open && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [open, logs?.length]);
  if (!open) return null;

  const colorFor = (level) => {
    const l = (level || '').toLowerCase();
    if (l === 'error' || l === 'critical') return 'var(--danger)';
    if (l === 'warning' || l === 'warn') return 'var(--warning)';
    if (l === 'debug') return 'var(--text-4)';
    return 'var(--text-3)';
  };

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'grid', placeItems: 'center', padding: 24 }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: 720, maxWidth: '100%', maxHeight: '80vh',
        background: 'var(--bg-elevated)', borderRadius: 16, border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-lifted)', overflow: 'hidden', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
          <div>
            <div style={{ fontSize: 'var(--fs-md)', fontWeight: 800, color: 'var(--text)' }}>서버 로그</div>
            <div style={{ fontSize: 'var(--fs-xs)', color: 'var(--text-3)', marginTop: 2 }}>{logs.length}줄 · 실시간</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <Button variant="ghost" size="sm" onClick={onClear} icon={<MMI.trash width="12" height="12"/>}>지우기</Button>
            <IconButton label="닫기" onClick={onClose}><MMI.close width="14" height="14"/></IconButton>
          </div>
        </div>
        <div ref={scrollRef} style={{
          flex: 1, overflowY: 'auto', padding: '10px 16px',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          fontSize: 12, lineHeight: 1.55, background: 'var(--surface-muted)',
        }}>
          {logs.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-4)' }}>로그가 아직 없어요</div>
          ) : logs.map((l, i) => (
            <div key={i} style={{ color: colorFor(l.level), whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{l.message}</div>
          ))}
        </div>
      </div>
    </div>
  );
}

window.MM = window.MM || {};
Object.assign(window.MM, { TopBar, Sidebar, AgendaTabs, RecordBar, MicLevel, StartScreen, SettingsModal, SummaryScreen, SummaryProgress, LogsModal });
