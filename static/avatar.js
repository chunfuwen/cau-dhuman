/* ============================================================
   DigitalHuman - canvas-drawn animated avatar with human-like
   poses/gestures and mouth movement synced to live audio level.
   ============================================================ */
class DigitalHuman {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.W = canvas.width;
    this.H = canvas.height;
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.ctx.scale(this.dpr, this.dpr);

    this.t = 0;                 // global time
    this.audioLevel = 0;        // 0..1 from analyser
    this.poses = ['idle', 'speak', 'nod', 'wave', 'smile', 'think'];
    this.pose = 'idle';         // current pose
    this.poseStart = 0;
    this.poseDuration = 2000;

    // gesture scheduler
    this.nextGestureAt = 1800 + Math.random() * 2000;

    // handedness for wave
    this.waveArm = 'right';

    this.smile = 0;             // 0..1
    this.blink = 0;             // 0..1 (0 open,1 closed)
    this.nextBlinkAt = 1200 + Math.random() * 2500;
    this.lastBlink = 0;
    this.mouth = 0;             // smoothed open amount 0..1
    this.render = this.render.bind(this);
    requestAnimationFrame(this.render);
  }

  setPose(name, dur) {
    if (this.poses.includes(name)) {
      this.pose = name;
      this.poseStart = this.t;
      this.poseDuration = dur || this.poseDuration;
      if (name === 'wave') this.waveArm = Math.random() > 0.5 ? 'left' : 'right';
    }
  }

  setAudioLevel(level) { this.audioLevel = Math.max(0, Math.min(1, level)); }

  setBubble(text) {
    const bubble = document.getElementById('speech-bubble');
    const el = document.getElementById('speech-text');
    if (el) el.textContent = text || '';
    if (bubble) bubble.classList.toggle('hidden', !text);
  }

  // ---- helpers -------------------------------------------------------
  _blink() {
    let b = 0;
    if (this.t >= this.nextBlinkAt) {
      const dt = this.t - this.nextBlinkAt;
      b = Math.max(0, 1 - dt / 150);
      if (dt > 150) this.nextBlinkAt = this.t + 1200 + Math.random() * 3000;
    }
    this.blink += (b - this.blink) * 0.5;
    return this.blink;
  }

  _smile() {
    const target = (this.pose === 'smile' || this.pose === 'speak') ? 1 : 0.25;
    this.smile += (target - this.smile) * 0.05;
    return this.smile;
  }

  // gesture scheduling during idle
  _tickGestures() {
    if (this.pose === 'idle' && this.t >= this.nextGestureAt) {
      const pick = ['nod', 'smile', 'wave', 'think'][Math.floor(Math.random() * 4)];
      this.setPose(pick, 1600);
      this.nextGestureAt = this.t + 3800 + Math.random() * 2600;
    }
  }

  _poseFactor(name, attack = 90, release = 220) {
    if (this.pose !== name) return 0;
    const dt = this.t - this.poseStart;
    if (dt < attack) return dt / attack;
    const back = this.poseDuration - dt;
    if (back < release) return Math.max(0, back / release);
    return 1;
  }

  // ---- drawing -------------------------------------------------------
  _circle(x, y, r) {
    const c = this.ctx;
    c.beginPath();
    c.arc(x, y, r, 0, Math.PI * 2);
  }

  _ellipse(x, y, rx, ry) {
    const c = this.ctx;
    c.beginPath();
    c.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
  }

  render() {
    const c = this.ctx;
    const W = this.W, H = this.H;
    this.t += 16; // ms per frame approximation
    this._tickGestures();

    // background
    const grad = c.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, '#0e2231');
    grad.addColorStop(1, '#1b3a4e');
    c.fillStyle = grad;
    c.fillRect(0, 0, W, H);

    // floor glow
    c.fillStyle = 'rgba(255,255,255,0.06)';
    this._ellipse(W / 2, H - 40, 150, 18);
    c.fill();

    // head posture: nod/think tilt
    const nod = this._poseFactor('nod');
    const think = this._poseFactor('think');
    const speakDur = Math.min(1, (this.t - this.poseStart) / 2000);
    let headTilt = (nod) * Math.sin(this.t * 0.003) * 0.08
      + (think ? 0.22 : 0)
      + (Math.sin(this.t * 0.025) * 0.015); // micro sways
    let headBob = nod * Math.max(0, Math.sin(this.t * 0.008)) * 6
      + Math.sin(this.t * 0.02) * 1.5;

    const cx = W / 2 + 40 * Math.sin(this.t * 0.006); // walk-in-itel body sway
    const cy = H - 220 + headBob;

    // ----- torso -----
    c.save();
    c.translate(cx, cy);
    c.fillStyle = '#2e7d5b';
    // shoulders / torso (rounded)
    c.beginPath();
    c.moveTo(-78, -6);
    c.bezierCurveTo(-86, 34, -74, 96, -60, 108);
    c.lineTo(60, 108);
    c.bezierCurveTo(74, 96, 86, 34, 78, -6);
    c.bezierCurveTo(40, 22, -40, 22, -78, -6);
    c.fill();
    // collar
    c.fillStyle = '#f5f0e6';
    c.beginPath();
    c.moveTo(-14, -2);
    c.lineTo(0, 14);
    c.lineTo(14, -2);
    c.lineTo(4, -16);
    c.closePath();
    c.fill();
    c.fillStyle = '#3a9d74';
    this._circle(0, 30, 5);
    c.fill();
    // name tag
    if (this.pose === 'wave' || this.pose === 'smile') {
      c.fillStyle = '#fff';
      c.font = '11px sans-serif';
      c.textAlign = 'center';
      c.fillText('农小田 · CAU', 0, -18);
    }

    // ----- arms -----
    this._renderArm(c, -1, nod, think);   // left
    this._renderArm(c, +1, nod, think);   // right

    // ----- neck -----
    c.fillStyle = '#e8b98f';
    c.fillRect(-12, -58, 24, 26);

    // ----- head -----
    c.save();
    c.translate(0, headTilt > 0 ? 0 : 0);
    c.rotate(headTilt);
    this._drawHead(c, think);

    // ----- speech bubble hint (set by app) -----
    c.restore();
    c.restore();

    // nameplate
    c.fillStyle = 'rgba(255,255,255,0.85)';
    c.font = '600 14px sans-serif';
    c.textAlign = 'center';
    c.fillText('数字人 · 农小田', W / 2, H - 16);

    // mouth sync from audio level shown as subtle ring pulse
    const pulse = 0.5 + this.audioLevel * 2.2;
    if (this.audioLevel > 0.02) {
      c.strokeStyle = `rgba(120,220,255,${0.18 * this.audioLevel})`;
      c.lineWidth = 2;
      this._circle(cx, cy - 10, 130 + pulse);
      c.stroke();
    }

    requestAnimationFrame(this.render);
  }

  _renderArm(c, side, nod, think) {
    // shoulder anchored at (±44, -10)
    const S = side; // +1 right, -1 left
    const waving = this.pose === 'wave' && this.waveArm === (S > 0 ? 'right' : 'left');
    const wave = waving ? this._poseFactor('wave') : 0;
    const idleSwing = Math.sin(this.t * 0.0035 + (S > 0 ? 0.7 : 0)) * 0.06 + S * 0.06;
    const sway = idleSwing + wave * Math.sin(this.t * 0.05) * 0.55 + nod * S * 0.08;
    const whisper = Math.sin(this.t * 0.05) * 0.01;

    c.save();
    c.translate(46 * S, -4);
    c.rotate(sway + whisper);
    c.fillStyle = '#2e7d5b';
    // upper arm
    this._roundRect(-9, 0, 18, 62, 9);
    c.fill();
    // forearm
    c.save();
    c.translate(0, 60);
    c.rotate(0.12 * S + wave * 0.35 * Math.sin(this.t * 0.05 + 1));
    c.fillStyle = '#f5f0e6';
    this._roundRect(-8, 0, 16, 44, 8);
    c.fill();
    // hand
    c.fillStyle = '#e8b98f';
    this._circle(0, 46, 9);
    c.fill();
    c.restore();
    c.restore();
  }

  _drawHead(c, think) {
    this.mouth += (this.audioLevel - this.mouth) * 0.35;
    const open = this.mouth;
    const blink = this._blink();
    const sm = this._smile();

    // hair (back)
    c.fillStyle = '#3b2b22';
    this._circle(0, -120, 62);
    c.fill();

    // face
    c.fillStyle = '#f3c9a0';
    this._ellipse(0, -96, 46, 55);
    c.fill();

    // fringe
    c.fillStyle = '#4a372c';
    c.beginPath();
    c.ellipse(-46, -118, 24, 16, -0.5, 0, Math.PI * 2);
    c.fill();
    c.beginPath();
    c.ellipse(46, -118, 24, 16, 0.5, 0, Math.PI * 2);
    c.fill();
    c.beginPath();
    c.ellipse(0, -150, 46, 30, 0, Math.PI, Math.PI * 2);
    c.fill();

    // eyes
    for (const ex of [-18, 18]) {
      const eyeY = -96;
      if (blink < 0.15) {
        c.fillStyle = '#fff';
        this._ellipse(ex, eyeY, 9, 10 + sm * 1.5);
        c.fill();
        c.fillStyle = '#3a2418';
        this._circle(ex, eyeY, 4.2);
        c.fill();
        c.fillStyle = '#fff';
        this._circle(ex + 1.6, eyeY - 1.6, 1.5);
        c.fill();
      } else {
        c.strokeStyle = '#3a2418';
        c.lineWidth = 3;
        c.beginPath();
        c.moveTo(ex - 8, eyeY);
        c.quadraticCurveTo(ex, eyeY + 4, ex + 8, eyeY);
        c.stroke();
      }
    }

    // eyebrows
    c.strokeStyle = '#4a372c';
    c.lineWidth = 3;
    for (const [ex, s] of [[-18, -1], [18, 1]]) {
      c.beginPath();
      c.moveTo(ex - 7, -116);
      c.quadraticCurveTo(ex, -121, ex + 7, -116);
      c.stroke();
    }

    // nose
    c.strokeStyle = 'rgba(180,130,90,0.8)';
    c.lineWidth = 2;
    c.beginPath();
    c.moveTo(0, -84);
    c.quadraticCurveTo(4, -76, 0, -72);
    c.stroke();

    // blush
    c.fillStyle = 'rgba(240,140,120,0.35)';
    this._ellipse(-27, -82, 7, 4);
    c.fill();
    this._ellipse(27, -82, 7, 4);
    c.fill();

    // mouth opening from audio level
    const grow = (open > 0.05 ? 0.06 : 0.0) * open;
    if (open > 0.04) {
      // open speaking mouth
      c.fillStyle = '#6e3a2c';
      c.beginPath();
      c.ellipse(0, -46, 10 + 4 * open, 3 + 13 * open, 0, 0, Math.PI * 2);
      c.fill();
      c.strokeStyle = '#7e4535';
      c.lineWidth = 1.5;
      c.stroke();
    } else {
      // neutral/smiling lip line
      c.strokeStyle = '#7e4535';
      c.lineWidth = 2.5;
      c.beginPath();
      if (sm > 0.4) {
        c.arc(0, -42 + sm * 2, 11 + sm * 3, 0.2, Math.PI - 0.2);
      } else {
        c.moveTo(-8, -46);
        c.quadraticCurveTo(0, -42, 8, -46);
      }
      c.stroke();
    }

    // glasses for 'think'
    if (think) {
      c.strokeStyle = 'rgba(60,60,70,0.9)';
      c.lineWidth = 2;
      this._ellipse(-18, -96, 11, 12);
      c.stroke();
      this._ellipse(18, -96, 11, 12);
      c.stroke();
      c.beginPath();
      c.moveTo(-7, -96);
      c.lineTo(7, -96);
      c.stroke();
    }
  }

  _roundRect(x, y, w, h, r) {
    const c = this.ctx;
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
  }
}

window.DigitalHuman = DigitalHuman;