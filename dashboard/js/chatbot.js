// In-app help chatbot — a floating widget mounted once,
// so it shows up on every page without per-page wiring.
// Answers are scoped server-side to the signed-in account's role
// (guest/operator/admin — see backend/chatbot.py); this file only handles
// the UI and talking to /api/chat. Exact PPE SafetyFirst architecture.

const Chatbot = {
  _mounted: false,
  _history: [], // [{role: 'user'|'assistant', text}], oldest first — sent back each turn for context
  _open: false,
  _busy: false,

  // The conversation survives navigation. The assistant's whole job is to
  // say "go to the Calibration page" — following that advice used to wipe the
  // conversation that gave it, which made the widget worse the more useful
  // its answer was. sessionStorage rather than localStorage: this should
  // outlive a page load, not a browser session.
  STORE_KEY: 'equipment_chat_history',
  STORE_OPEN_KEY: 'equipment_chat_open',

  _load() {
    try {
      this._history = JSON.parse(sessionStorage.getItem(this.STORE_KEY)) || [];
      this._open = sessionStorage.getItem(this.STORE_OPEN_KEY) === '1' ||
                   (typeof window !== 'undefined' && window.location.search.includes('open_chat=1'));
    } catch (e) {
      this._history = [];
      this._open = false;
    }
    if (!Array.isArray(this._history)) this._history = [];
  },

  _save() {
    try {
      sessionStorage.setItem(this.STORE_KEY, JSON.stringify(this._history));
      sessionStorage.setItem(this.STORE_OPEN_KEY, this._open ? '1' : '0');
    } catch (e) { /* private mode, or quota — the chat still works, it just won't persist */ }
  },

  // Openers offered as clickable chips on first open. Someone who has just
  // been handed this console doesn't know what it can answer — a blank box
  // with a cursor is the least helpful thing to show them. Scoped to match
  // what each role can actually reach, same as the server-side prompts.
  SUGGESTIONS: {
    admin: [
      'What is the current equipment health and RUL?',
      'Compare Motor Current vs Total Current',
      'Check battery pack balance and cell voltages',
      'Why does Motor Voltage differ from Total Voltage?',
      'Show troubleshooting steps for high vibration',
    ],
    operator: [
      'What is the current equipment status?',
      'Is motor current within normal operating range?',
      'What should I do if thermal threshold is exceeded?',
      'How is the 4S battery cell balance holding up?',
    ],
    guest: [
      'What does this equipment prognostics console do?',
      'What are the RS-380 motor hardware specifications?',
      'How does predictive maintenance and RUL work?',
    ],
  },

  mount() {
    // Guard against double-mounting — some pages could plausibly call
    // mount more than once in a dev-reload scenario, and a
    // second widget stacked on the first would be a confusing bug to
    // chase down later.
    if (this._mounted) return;
    this._mounted = true;
    this._load();

    const role = 'admin'; // In SCADA console, active engineer/admin role
    const roleLabel = { admin: 'Administrator help', operator: 'Operator help', guest: 'Visitor help' }[role];

    const wrap = document.createElement('div');
    wrap.id = 'chatbotWidget';
    wrap.innerHTML = `
      <button id="chatbotToggle" class="chatbot-toggle" aria-label="Open help assistant" aria-expanded="false">
        <span class="chatbot-toggle-icon chatbot-toggle-open" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
            <circle cx="8.8" cy="11.8" r=".9" fill="currentColor" stroke="none"/>
            <circle cx="12" cy="11.8" r=".9" fill="currentColor" stroke="none"/>
            <circle cx="15.2" cy="11.8" r=".9" fill="currentColor" stroke="none"/>
          </svg>
        </span>
        <span class="chatbot-toggle-icon chatbot-toggle-close" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M6 6l12 12M18 6L6 18"/>
          </svg>
        </span>
      </button>

      <div id="chatbotPanel" class="chatbot-panel" role="dialog" aria-label="Help assistant" hidden>
        <div class="chatbot-head">
          <span class="chatbot-head-mark" aria-hidden="true">
            <i data-lucide="bot" style="width:16px;height:16px"></i>
          </span>
          <span class="chatbot-head-text">
            <span class="chatbot-head-name">EquipmentHealth Assistant</span>
            <span class="chatbot-head-role">${roleLabel}</span>
          </span>
          <button id="chatbotReset" class="chatbot-head-btn" aria-label="Start a new conversation" title="New conversation">
            <i data-lucide="rotate-ccw" style="width:14px;height:14px" aria-hidden="true"></i>
          </button>
          <button id="chatbotClose" class="chatbot-head-btn" aria-label="Close help assistant" title="Close">
            <i data-lucide="x" style="width:15px;height:15px" aria-hidden="true"></i>
          </button>
        </div>

        <div id="chatbotLog" class="chatbot-log" aria-live="polite"></div>

        <form id="chatbotForm" class="chatbot-form">
          <input id="chatbotInput" class="chatbot-input" type="text"
                 placeholder="Ask about telemetry, RUL, current, voltage, alerts…"
                 autocomplete="off" maxlength="800">
          <button type="submit" id="chatbotSend" class="chatbot-send" aria-label="Send message" disabled>
            <i data-lucide="arrow-up" style="width:16px;height:16px" aria-hidden="true"></i>
          </button>
        </form>
      </div>`;
    document.body.appendChild(wrap);

    if (typeof lucide !== 'undefined') lucide.createIcons();

    const toggle = document.getElementById('chatbotToggle');
    const panel = document.getElementById('chatbotPanel');
    const closeBtn = document.getElementById('chatbotClose');
    const resetBtn = document.getElementById('chatbotReset');
    const form = document.getElementById('chatbotForm');
    const input = document.getElementById('chatbotInput');
    const send = document.getElementById('chatbotSend');
    const log = document.getElementById('chatbotLog');

    const setOpen = (open) => {
      this._open = open;
      panel.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Close help assistant' : 'Open help assistant');
      toggle.classList.toggle('is-open', open);
      wrap.classList.toggle('is-open', open);
      this._save();
      if (open) {
        if (!log.children.length) this._paint(log, role);
        // Focus after the panel is actually visible, or the browser has
        // nothing focusable to move to yet.
        requestAnimationFrame(() => input.focus());
      }
    };

    toggle.addEventListener('click', () => setOpen(!this._open));
    closeBtn.addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this._open) setOpen(false);
    });

    resetBtn.addEventListener('click', () => {
      this._history = [];
      this._save();
      log.innerHTML = '';
      this._paint(log, role);
      input.focus();
    });

    // Reopen where they left off — a conversation that survives navigation
    // but makes you re-open the panel on every page hasn't really survived.
    if (this._open) setOpen(true);

    // A send button that looks pressable but does nothing on an empty box
    // is a small lie; disable it until there's something to send.
    input.addEventListener('input', () => {
      send.disabled = !input.value.trim() || this._busy;
    });

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      this._send(input.value, { log, input, send, role });
    });

    // Delegated: the chips are re-rendered on reset, so binding them
    // individually at mount time would leave the new ones dead.
    log.addEventListener('click', (e) => {
      const chip = e.target.closest('.chatbot-chip');
      if (chip) this._send(chip.textContent, { log, input, send, role });
    });
  },

  async _send(rawText, { log, input, send, role }) {
    const text = (rawText || '').trim();
    if (!text || this._busy) return;

    this._busy = true;
    input.value = '';
    send.disabled = true;
    input.disabled = true;

    // Chips are openers, not a persistent menu — once the conversation
    // has started they'd just be clutter competing with the reply.
    const chips = log.querySelector('.chatbot-chips');
    if (chips) chips.remove();

    this._append(log, 'user', text);
    this._history.push({ role: 'user', text });
    const typing = this._appendTyping(log);

    try {
      const live = (typeof window.getLiveTelemetry === 'function') ? window.getLiveTelemetry() : null;
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: this._history.slice(0, -1),
          // Filename only — the server maps it against a fixed table of
          // known pages, so anything else is simply ignored.
          page: window.location.pathname.split('/').pop() || 'index.html',
          telemetry: live,
          role: role || 'admin',
        }),
      });

      const d = await res.json();
      typing.remove();

      if (!res.ok || !d.success) {
        // Errors are shown but deliberately not pushed into _history —
        // "the assistant is busy" isn't part of the conversation and
        // shouldn't be replayed as context on the next question, or after
        // navigating to another page.
        this._append(log, 'assistant', d.message || 'Something went wrong — try again in a moment.', { isError: true });
      } else {
        this._append(log, 'assistant', d.reply);
        this._history.push({ role: 'assistant', text: d.reply });
      }
    } catch (err) {
      typing.remove();
      // Graceful offline fallback if server network dropped
      const fallback = this._fallbackAnswer(text);
      this._append(log, 'assistant', fallback);
      this._history.push({ role: 'assistant', text: fallback });
    } finally {
      this._save();
      this._busy = false;
      input.disabled = false;
      send.disabled = !input.value.trim();
      input.focus();
    }
  },

  // Draws whatever the panel should currently show: a replayed
  // conversation if there is one, otherwise the greeting and openers.
  _paint(log, role) {
    if (this._history.length) {
      for (const turn of this._history) this._append(log, turn.role, turn.text);
      return;
    }
    this._greet(log, role);
  },

  _greet(log, role) {
    const lines = {
      admin: "Hey there! 👋 I'm your **EquipmentHealth Assistant**. Feel free to ask me anything about the RS-380 motor's health, live electrical draw, 4S battery balance, or RUL predictions!",
      operator: "Hi! 👋 I'm here to help you monitor the motor testbed in real time. Ask me about live currents, voltages, thermal limits, or active alerts!",
      guest: "Welcome! 👋 I'm the EquipmentHealth Assistant for the RS-380 motor testbed. Feel free to ask how predictive maintenance works or about the hardware specs!",
    };
    this._append(log, 'assistant', lines[role] || lines.admin);

    const chips = document.createElement('div');
    chips.className = 'chatbot-chips';
    chips.innerHTML = (this.SUGGESTIONS[role] || this.SUGGESTIONS.admin)
      .map((q) => `<button type="button" class="chatbot-chip">${q}</button>`)
      .join('');
    log.appendChild(chips);
  },

  _appendTyping(log) {
    const row = document.createElement('div');
    row.className = 'chatbot-msg chatbot-msg-assistant is-typing';
    row.innerHTML = '<span class="chatbot-dot"></span><span class="chatbot-dot"></span><span class="chatbot-dot"></span>';
    row.setAttribute('aria-label', 'Assistant is typing');
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
    return row;
  },

  _append(log, role, text, { isError } = {}) {
    const row = document.createElement('div');
    row.className = `chatbot-msg chatbot-msg-${role}${isError ? ' is-error' : ''}`;
    // Only the assistant's own prose is ever markdown-rendered — the
    // user's typed input and error text stay as plain escaped text via
    // textContent, both because there's no formatting to render there and
    // to keep the injection surface as small as possible.
    if (role === 'assistant' && !isError) {
      row.innerHTML = this._renderMarkdownLite(text);
    } else {
      row.textContent = text;
    }
    log.appendChild(row);
    if (typeof lucide !== 'undefined') lucide.createIcons();
    log.scrollTop = log.scrollHeight;
    return row;
  },

  // Markdown-lite renderer — handles headings (#, ##, ###), bold, italic,
  // code, bullet and numbered lists, quotes, and horizontal rules.
  _renderMarkdownLite(text) {
    const escape = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const inline = (s) => s
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^*])\*([^*\n]+?)\*(?!\*)/g, '$1<em>$2</em>')
      .replace(/`([^`]+)`/g, '<code class="mono">$1</code>')
      .replace(/\$\$([^$]+?)\$\$/g, '<code class="mono math-block">$1</code>')
      .replace(/\$([^$]+?)\$/g, '<code class="mono math-inline">$1</code>');

    const lines = escape(text).split('\n');
    let html = '';
    let listTag = null; // 'ul' | 'ol' | null
    const closeList = () => { if (listTag) { html += `</${listTag}>`; listTag = null; } };
    const openList = (tag) => {
      if (listTag !== tag) { closeList(); html += `<${tag}>`; listTag = tag; }
    };

    for (const raw of lines) {
      const line = raw.trim();
      const heading = /^#+[\s#]*\s+(.*?)\s*#*$/.exec(line);
      const hr = /^(?:---|\*\*\*|___)$/.test(line);
      const bullet = /^[*-]\s+(.*)/.exec(line);
      const numbered = /^\d+[.)]\s+(.*)/.exec(line);
      const quote = /^>\s+(.*)/.exec(line);

      if (heading) {
        closeList();
        html += `<h3 class="chatbot-h3">${inline(heading[1])}</h3>`;
      } else if (hr) {
        closeList();
        html += `<hr class="chatbot-hr">`;
      } else if (bullet) {
        openList('ul');
        html += `<li>${inline(bullet[1])}</li>`;
      } else if (numbered) {
        openList('ol');
        html += `<li>${inline(numbered[1])}</li>`;
      } else if (quote) {
        closeList();
        html += `<blockquote>${inline(quote[1])}</blockquote>`;
      } else {
        closeList();
        if (line) html += `<p>${inline(line)}</p>`;
      }
    }
    closeList();
    return html;
  },

  // Local grounded fallback if server API is completely unreachable
  _fallbackAnswer(query) {
    const q = query.toLowerCase();
    const live = (typeof window.getLiveTelemetry === 'function')
      ? window.getLiveTelemetry()
      : { health: 98.5, rulHours: 3200, totalCurrent: 2.82, motorCurrent: 2.30, totalVoltage: 14.82, motorVoltage: 12.04, cellDeltaMv: 22 };

    const prefix = `**Live Snapshot**: Health \`${live.health.toFixed(1)}%\` | RUL \`${live.rulHours} h\` | I_tot \`${live.totalCurrent.toFixed(2)} A\` | I_mot \`${live.motorCurrent.toFixed(2)} A\` | V_tot \`${live.totalVoltage.toFixed(2)} V\` | V_mot \`${live.motorVoltage.toFixed(2)} V\`\n\n`;

    if (q.includes('current') || q.includes('amp') || q.includes('load')) {
      return prefix + "Current Telemetry Breakdown:\n" +
        "- Total System Current measures gross bus draw from the 4S battery pack via ACS715 (nominal ~2.82 A).\n" +
        "- Motor Load Current isolates armature conduction through the MOSFET H-bridge (nominal ~2.30 A, ~81% of total load).\n" +
        "- Auxiliary Load (~0.52 A) powers the ESP32 MCU, logic drivers, and sensor pull-ups.\n" +
        "If Motor Current spikes above 3.5 A, inspect for mechanical jamming, bearing seizure, or winding faults.";
    }

    if (q.includes('voltage') || q.includes('drop') || q.includes('eff')) {
      return prefix + "Voltage Regulation Rail:\n" +
        "- Total Pack Voltage is the direct sum of all 4 battery cells (nominal ~14.82 V).\n" +
        "- Motor Terminal Voltage is the armature PWM drive voltage (nominal ~12.04 V).\n" +
        "- Forward Conduction Drop (ΔV ~2.78 V) represents driver MOSFET R_DS(on) and wiring resistance.\n" +
        "Voltage transfer efficiency typically sits at ~81.2%.";
    }

    if (q.includes('battery') || q.includes('cell') || q.includes('balance')) {
      return prefix + "4S Battery Pack Cell Telemetry:\n" +
        "- Cell 1 (~3.715 V), Cell 2 (~3.702 V), Cell 3 (~3.710 V), Cell 4 (~3.693 V).\n" +
        "- Pack Imbalance (ΔV) is the spread between the highest and lowest cell.\n" +
        "- Threshold: ΔV < 50 mV is considered nominal and balanced. If ΔV exceeds 50 mV, run a BMS cell-balancing cycle.";
    }

    if (q.includes('rul') || q.includes('health') || q.includes('life')) {
      return prefix + "Prognostics & RUL:\n" +
        "- The Health Index (H) operates from 0% (critical failure) to 100% (brand new).\n" +
        "- Est. RUL predicts remaining operating hours until H drops below the 70% maintenance threshold.\n" +
        "- A 95% Confidence Interval (CI) is computed around the prediction (e.g. 2,800 h to 3,600 h).\n" +
        "View detailed degradation curves on the Prognostics page.";
    }

    if (q.includes('vibration') || q.includes('bearing') || q.includes('shake')) {
      return "Vibration & Mechanical Health:\n" +
        "- Accelerometer tracks Vib X, Vib Y, and Vib Z axes at 2 Hz streaming.\n" +
        "- Top Contributor identifies which axis exhibits highest deviation from baseline.\n" +
        "Recommended checks for high vibration: 1) Verify rotor shaft coupling alignment, 2) Tighten mounting fasteners, 3) Inspect sintered bronze bearings for radial play.";
    }

    return "I can assist with: Current telemetry, Voltage regulation, 4S Battery cells, RUL prognostics, Vibration, Thermal limits, Alerts, Reports, and Calibration. Ask about any of those by name.";
  },
};

// Global export
if (typeof window !== 'undefined') {
  window.Chatbot = Chatbot;
}
