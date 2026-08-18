/* CAU Digital Human - frontend controller:
   - RAG chat API calls
   - TTS audio playback with live analyser -> drives avatar mouth
   - Chinese speech input
   - quick Q&A chips + status pills */
(function () {
  'use strict';

  const avatar = new DigitalHuman(document.getElementById('avatar'));
  const messagesEl = document.getElementById('messages');
  const inputEl = document.getElementById('input');
  const sendBtn = document.getElementById('send-btn');
  const micBtn = document.getElementById('mic-btn');
  const ttsToggle = document.getElementById('tts-toggle');
  const voiceSelect = document.getElementById('voice-select');
  const bubbleEl = document.getElementById('speech-text');
  const llmStatus = document.getElementById('llm-status');
  const kbStatus = document.getElementById('kb-status');

  let AudioCtx = window.AudioContext || window.webkitAudioContext;
  let actx = null, analyser = null, liveNode = null;
  let playing = false;

  // ---------- audio + mouth sync ----------
  async function playAudio(url) {
    if (url && url.endsWith('.wav')) {
      // offline fallback cue: animate ~1.4s mouth movement
      startSpeaking(1400);
      setTimeout(() => stopSpeaking(), 1400);
      return;
    }
    if (!AudioCtx) return;
    actx = actx || new AudioCtx();
    if (actx.state === 'suspended') await actx.resume();
    try {
      const resp = await fetch(url);
      const buf = await resp.arrayBuffer();
      const audioBuf = await actx.decodeAudioData(buf);
      analyser = actx.createAnalyser();
      analyser.fftSize = 512;
      const src = actx.createBufferSource();
      src.buffer = audioBuf;
      src.connect(analyser);
      analyser.connect(actx.destination);
      stopSpeaking();
      playing = true;
      src.onended = () => { stopSpeaking(); playing = false; };
      src.start(0);
      startSpeaking(audioBuf.duration * 1000);
      tickMouth();
    } catch (e) {
      console.error('audio playback failed', e);
    }
  }

  function tickMouth() {
    if (!playing || !analyser) return;
    const data = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(data);
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i];
    const level = sum / data.length / 255;
    avatar.audioLevel = level > 0.05 ? Math.min(1, level * 2.2) : 0;
    requestAnimationFrame(tickMouth);
  }

  let speakTimer = null;
  function startSpeaking(ms) {
    avatar.setPose('speak', ms || 2500);
    clearTimeout(speakTimer);
    speakTimer = null;
  }
  function stopSpeaking() {
    avatar.audioLevel = 0;
    avatar.setPose('idle', 1600);
  }

  // ---------- chat ----------
  async function sendMessage(text) {
    text = (text || '').trim();
    if (!text) return;
    addMessage('user', text);
    inputEl.value = '';
    const typing = addMessage('digital', '').firstElementChild;
    typing.classList.add('typing');
    avatar.setPose('think', 1400);

    const use_tts = ttsToggle.checked;
    const voice = voiceSelect.value;
    try {
      const resp = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: [], voice, use_tts })
      });
      const data = await resp.json();
      typing.classList.remove('typing');
      typing.innerHTML = escapeHtml(data.answer).replace(/\n/g, '<br>');
      renderSources(data.sources || []);
      setStatus(data.mode);

      avatar.setPose('smile', 1500);
      const first = (data.answer || '').split('\n').find(l => l.trim());
      if (bubbleEl) bubbleEl.textContent = first || '';
      setTimeout(() => { if (bubbleEl) bubbleEl.textContent = ''; }, 7000);

      if (use_tts) {
        if (data.audio_url) {
          await playAudio(data.audio_url);
        } else {
          startSpeaking(1500);
          setTimeout(() => stopSpeaking(), 1500);
        }
      }
    } catch (e) {
      typing.classList.remove('typing');
      typing.innerHTML = '<span style="color:#ff9b8c">连接后端失败，请确认服务已启动（uvicorn app.main:app）</span>';
    }
  }

  // ---------- status / quick chips ----------
  function setStatus(mode) {
    if (mode === 'online') {
      llmStatus.textContent = 'DeepSeek 在线';
      llmStatus.style.background = '#173b2a';
    } else {
      llmStatus.textContent = '离线演示模式（未配置 Key）';
      llmStatus.style.background = '#4a3d18';
    }
  }

  async function loadStatus() {
    try {
      const r = await fetch('/healthz');
      const j = await r.json();
      kbStatus.textContent = `知识库 ${j.retrieval.n_documents} 篇 / ${j.retrieval.n_chunks} 片段`;
      setStatus(j.llm_connected ? 'online' : 'offline-demo');
    } catch (e) {}
  }

  document.querySelectorAll('#quick button').forEach(btn => {
    btn.addEventListener('click', () => sendMessage(btn.dataset.q));
  });

  // ---------- speech recognition ----------
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognizing = false;
  if (SR) {
    const rec = new SR();
    rec.lang = 'zh-CN';
    rec.interimResults = false;
    rec.onstart = () => { micBtn.classList.add('active'); recognizing = true; };
    rec.onend = () => { micBtn.classList.remove('active'); recognizing = false; };
    rec.onresult = (e) => {
      const t = e.results[0][0].transcript;
      if (t) sendMessage(t);
    };
    micBtn.addEventListener('click', () => {
      if (recognizing) { rec.stop(); return; }
      try { rec.start(); } catch (e) { /* already started */ }
    });
  } else {
    micBtn.disabled = true;
    micBtn.title = '当前浏览器不支持语音输入';
  }

  // ---------- helpers ----------
  function addMessage(role, text) {
    const wrap = document.createElement('div');
    wrap.className = `row ${role}`;
    const inner = document.createElement('div');
    inner.className = role === 'user' ? 'bubble user' : 'bubble digital';
    inner.innerHTML = text ? escapeHtml(text).replace(/\n/g, '<br>') : '';
    wrap.appendChild(inner);
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return wrap;
  }

  function renderSources(sources) {
    if (!sources.length) return;
    const wrap = document.createElement('div');
    wrap.className = 'sources';
    wrap.innerHTML = '<span class="src-title">知识库引用来源</span>';
    sources.forEach(s => {
      const chip = document.createElement('div');
      chip.className = 'src-chip';
      chip.textContent = `${s.doc_title} › ${s.section}`;
      chip.title = `file: ${s.source}`;
      wrap.appendChild(chip);
    });
    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function escapeHtml(s) {
    return (s || '').replace(/[&<>"']/g, c => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
  }

  // init
  sendBtn.addEventListener('click', () => sendMessage(inputEl.value));
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(inputEl.value); }
  });
  avatar.setBubble('你好呀，我是农小田，中国农大的数字人助理！');
  loadStatus();
  setTimeout(async () => {
    await sendMessage('请介绍一下中国农业大学的学校概况');
  }, 600);
})();