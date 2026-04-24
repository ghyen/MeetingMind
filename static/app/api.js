// MeetingMind API Client
// Wraps REST + WebSocket endpoints. Clients import via window.MM.api / window.MM.ws

(function() {
  const BASE = ''; // same origin as backend (FastAPI serves /static/)

  const api = {
    async _req(path, opts = {}) {
      const r = await fetch(BASE + path, {
        headers: { 'Content-Type': 'application/json' },
        ...opts,
      });
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return r.json();
    },
    startMeeting(body = {}) { return this._req('/api/meeting/start', { method: 'POST', body: JSON.stringify(body) }); },
    endMeeting() { return this._req('/api/meeting/end', { method: 'POST' }); },
    state() { return this._req('/api/meeting/state'); },
    simulate(body) { return this._req('/api/meeting/simulate', { method: 'POST', body: JSON.stringify(body) }); },
    updateIssue(topicId, body) { return this._req(`/api/meeting/issues/${topicId}`, { method: 'PUT', body: JSON.stringify(body) }); },
    summary() { return this._req('/api/meeting/summary'); },
    ask(question) { return this._req('/api/meeting/ask', { method: 'POST', body: JSON.stringify({ question }) }); },
    reset() { return this._req('/api/meeting/reset', { method: 'POST' }); },
    listMeetings() { return this._req('/api/meetings'); },
    getMeeting(id) { return this._req(`/api/meetings/${id}`); },
    models() { return this._req('/api/models'); },
    setModel(provider, model) { return this._req('/api/model', { method: 'POST', body: JSON.stringify({ provider, model }) }); },
    updateSpeakerNames(meetingId, speakerNames) {
      const path = meetingId ? `/api/meetings/${meetingId}/speaker-names` : '/api/meeting/speaker-names';
      return this._req(path, { method: 'PUT', body: JSON.stringify({ speaker_names: speakerNames }) });
    },
    async upload(file) {
      const fd = new FormData();
      fd.append('file', file);
      const r = await fetch(BASE + '/api/meeting/upload', { method: 'POST', body: fd });
      return r.json();
    },
    saveNote(topicId, text) {
      return this._req('/api/meeting/notes', { method: 'POST', body: JSON.stringify({ topic_id: topicId, text }) });
    },
    listNotes(topicId) {
      const q = topicId != null ? `?topic_id=${topicId}` : '';
      return this._req(`/api/meeting/notes${q}`);
    },
    listMeetingNotes(meetingId, topicId) {
      const q = topicId != null ? `?topic_id=${topicId}` : '';
      return this._req(`/api/meetings/${meetingId}/notes${q}`);
    },
  };

  // WebSocket manager — reconnects, dispatches typed messages
  class WS {
    constructor(path, opts = {}) {
      this.path = path;
      this.handlers = new Set();
      this.openHandlers = new Set();
      this.closeHandlers = new Set();
      this.ws = null;
      this.reconnect = opts.reconnect !== false;
      this.retryMs = 1500;
      this._stopped = false;
    }
    connect() {
      const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
      this.ws = new WebSocket(`${proto}//${location.host}${this.path}`);
      this.ws.binaryType = 'arraybuffer';
      this.ws.onopen = () => { this.openHandlers.forEach((h) => h()); };
      this.ws.onmessage = (e) => {
        if (typeof e.data === 'string') {
          try { const data = JSON.parse(e.data); this.handlers.forEach((h) => h(data)); } catch (err) { /* ignore */ }
        }
      };
      this.ws.onclose = () => {
        this.closeHandlers.forEach((h) => h());
        if (this.reconnect && !this._stopped) setTimeout(() => this.connect(), this.retryMs);
      };
      this.ws.onerror = () => {};
    }
    send(data) {
      if (!this.ws || this.ws.readyState !== 1) return false;
      if (typeof data === 'string') this.ws.send(data); else this.ws.send(data);
      return true;
    }
    onMessage(fn) { this.handlers.add(fn); return () => this.handlers.delete(fn); }
    onOpen(fn) { this.openHandlers.add(fn); return () => this.openHandlers.delete(fn); }
    onClose(fn) { this.closeHandlers.add(fn); return () => this.closeHandlers.delete(fn); }
    close() { this._stopped = true; if (this.ws) this.ws.close(); }
  }

  // Audio capture → float32 PCM chunks → WS
  class AudioStreamer {
    constructor(ws) {
      this.ws = ws;
      this.stream = null;
      this.ctx = null;
      this.node = null;
      this.level = 0;  // 0-1 for UI meter
      this.muted = false;
    }
    async start() {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      this.ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      const src = this.ctx.createMediaStreamSource(this.stream);
      const bufSize = 4096;
      this.node = this.ctx.createScriptProcessor(bufSize, 1, 1);
      this.node.onaudioprocess = (e) => {
        if (this.muted) return;
        const pcm = e.inputBuffer.getChannelData(0);
        // level: peak
        let peak = 0;
        for (let i = 0; i < pcm.length; i++) { const v = Math.abs(pcm[i]); if (v > peak) peak = v; }
        this.level = peak;
        this.ws.send(pcm.buffer);
      };
      src.connect(this.node);
      this.node.connect(this.ctx.destination);
    }
    stop() {
      if (this.node) this.node.disconnect();
      if (this.ctx) this.ctx.close();
      if (this.stream) this.stream.getTracks().forEach((t) => t.stop());
      this.node = this.ctx = this.stream = null;
      this.level = 0;
    }
    setMuted(m) { this.muted = m; if (m) this.level = 0; }
    calibrate() { this.ws.send('calibrate'); }
  }

  window.MM = window.MM || {};
  window.MM.api = api;
  window.MM.WS = WS;
  window.MM.AudioStreamer = AudioStreamer;
})();
