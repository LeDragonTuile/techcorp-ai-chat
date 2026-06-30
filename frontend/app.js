// ============================================================
//  TechCorp AI — Interface chat
//  Streaming + i18n FR/EN + Stop/Régénérer/Copier + clé API
// ============================================================

const CONFIG = {
  serverType: localStorage.getItem('serverType') || 'auto',
  serverUrl:  localStorage.getItem('serverUrl')  || '',
  modelName:  localStorage.getItem('modelName')  || 'phi3.5-financial',
  apiKey:     localStorage.getItem('apiKey')     || '',
  temperature: parseFloat(localStorage.getItem('temperature') || '0.7'),
  maxTokens:  parseInt(localStorage.getItem('maxTokens') || '2048'),
  systemPrompt: localStorage.getItem('systemPrompt') ||
    "Tu es Phi-3.5-Financial, un assistant expert en finance et business pour TechCorp Industries. Tu réponds en français de manière précise, structurée et professionnelle.",
};

let conversations = JSON.parse(localStorage.getItem('conversations') || '[]');
let currentId = null;
let messages = [];
let busy = false;
let controller = null;          // AbortController de la génération en cours
let lang = localStorage.getItem('lang') || 'fr';

// ─── Internationalisation ───────────────────────────────
const I18N = {
  fr: {
    new_chat: 'Nouvelle conversation', history: 'Historique', settings: 'Paramètres',
    status_connecting: 'Connexion…', status_ollama: 'Ollama connecté',
    status_demo: 'Mode démo actif', status_local: 'Démo locale',
    mode_ollama: '● Phi-3.5 · Ollama', mode_demo: 'Mode démo', mode_local: 'Démo locale',
    hero_title: 'Bonjour 👋 Je suis votre <span class="grad">analyste financier</span>',
    hero_sub: "Spécialisé en finance, valorisation et stratégie d'entreprise pour TechCorp Industries. Par où commençons-nous ?",
    card1_t: 'Analyse de bilan', card1_s: 'Actif, passif & capitaux propres',
    card2_t: "Stratégie d'investissement", card2_s: 'Diversification & allocation',
    card3_t: 'Valorisation startup', card3_s: 'DCF, multiples & Berkus',
    card4_t: 'Gestion des risques', card4_s: 'VaR, volatilité & couverture',
    placeholder: 'Posez votre question financière…',
    hint: '<kbd>Entrée</kbd> pour envoyer · <kbd>Maj</kbd>+<kbd>Entrée</kbd> nouvelle ligne',
    export: 'Exporter la conversation', clear: 'Effacer',
    f_server: "Serveur d'inférence", f_url: "URL de l'API", f_model: 'Modèle',
    f_apikey: 'Clé API (optionnelle)', f_tokens: 'Tokens max', f_system: 'Prompt système',
    f_test: 'Tester la connexion', f_save: 'Enregistrer',
    copy: 'Copier', copied: 'Copié !', regenerate: 'Régénérer', stopped: '⏹ Génération arrêtée.',
    confirm_clear: 'Effacer cette conversation ?', you: 'Vous',
    test_running: 'Test en cours…', empty_hist: 'Aucune conversation',
    new_title: 'Nouvelle conversation', new_sub: 'Posez votre question financière pour démarrer.',
    err_server: "⚠ Serveur injoignable — le mode démo local prend le relais.",
  },
  en: {
    new_chat: 'New conversation', history: 'History', settings: 'Settings',
    status_connecting: 'Connecting…', status_ollama: 'Ollama connected',
    status_demo: 'Demo mode active', status_local: 'Local demo',
    mode_ollama: '● Phi-3.5 · Ollama', mode_demo: 'Demo mode', mode_local: 'Local demo',
    hero_title: 'Hello 👋 I\'m your <span class="grad">financial analyst</span>',
    hero_sub: 'Specialized in finance, valuation and corporate strategy for TechCorp Industries. Where shall we start?',
    card1_t: 'Balance sheet analysis', card1_s: 'Assets, liabilities & equity',
    card2_t: 'Investment strategy', card2_s: 'Diversification & allocation',
    card3_t: 'Startup valuation', card3_s: 'DCF, multiples & Berkus',
    card4_t: 'Risk management', card4_s: 'VaR, volatility & hedging',
    placeholder: 'Ask your financial question…',
    hint: '<kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> new line',
    export: 'Export conversation', clear: 'Clear',
    f_server: 'Inference server', f_url: 'API URL', f_model: 'Model',
    f_apikey: 'API key (optional)', f_tokens: 'Max tokens', f_system: 'System prompt',
    f_test: 'Test connection', f_save: 'Save',
    copy: 'Copy', copied: 'Copied!', regenerate: 'Regenerate', stopped: '⏹ Generation stopped.',
    confirm_clear: 'Clear this conversation?', you: 'You',
    test_running: 'Testing…', empty_hist: 'No conversation',
    new_title: 'New conversation', new_sub: 'Ask your financial question to start.',
    err_server: '⚠ Server unreachable — local demo mode takes over.',
  },
};
function t(k) { return (I18N[lang] && I18N[lang][k]) ?? (I18N.fr[k] ?? k); }

function applyLang() {
  const d = I18N[lang];
  document.querySelectorAll('[data-i18n]').forEach(el => { if (d[el.dataset.i18n] != null) el.innerHTML = d[el.dataset.i18n]; });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { if (d[el.dataset.i18nPh] != null) el.placeholder = d[el.dataset.i18nPh]; });
  document.querySelectorAll('[data-i18n-title]').forEach(el => { if (d[el.dataset.i18nTitle] != null) el.title = d[el.dataset.i18nTitle]; });
  document.documentElement.lang = lang;
  document.getElementById('langBtn').textContent = lang === 'fr' ? 'EN' : 'FR';
}
function toggleLang() {
  lang = lang === 'fr' ? 'en' : 'fr';
  localStorage.setItem('lang', lang);
  applyLang(); updateStatus();
  if (!messages.length) renderMessages();
}

// ─── Base d'API ─────────────────────────────────────────
function apiBase() {
  if (CONFIG.serverType !== 'auto' && CONFIG.serverUrl) return CONFIG.serverUrl.replace(/\/$/, '');
  if (location.protocol.startsWith('http')) return location.origin;
  return 'http://localhost:8080';
}
function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (CONFIG.apiKey) h['X-API-Key'] = CONFIG.apiKey;
  return h;
}

// ─── Init ───────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  loadSettings(); applyLang(); renderHistory(); updateStatus();
  setInterval(updateStatus, 12000);
  if (conversations.length) loadConversation(conversations[0].id);
});

// ─── Statut serveur ─────────────────────────────────────
async function updateStatus() {
  const dot = document.getElementById('statusDot');
  const txt = document.getElementById('statusText');
  const badge = document.getElementById('modeBadge');
  try {
    const r = await fetch(`${apiBase()}/health`, { signal: AbortSignal.timeout(4000) });
    const d = await r.json();
    if (d.mode === 'ollama') {
      dot.className = 'dot online'; txt.textContent = t('status_ollama');
      badge.className = 'mode-badge live'; badge.textContent = t('mode_ollama');
    } else {
      dot.className = 'dot demo'; txt.textContent = t('status_demo');
      badge.className = 'mode-badge demo'; badge.textContent = t('mode_demo');
    }
  } catch {
    dot.className = 'dot demo'; txt.textContent = t('status_local');
    badge.className = 'mode-badge demo'; badge.textContent = t('mode_local');
  }
}

// ─── Paramètres ─────────────────────────────────────────
function loadSettings() {
  document.getElementById('serverType').value = CONFIG.serverType;
  document.getElementById('serverUrl').value = CONFIG.serverUrl || apiBase();
  document.getElementById('modelNameInput').value = CONFIG.modelName;
  document.getElementById('apiKeyInput').value = CONFIG.apiKey;
  document.getElementById('temperature').value = CONFIG.temperature;
  document.getElementById('tempVal').textContent = CONFIG.temperature;
  document.getElementById('maxTokens').value = CONFIG.maxTokens;
  document.getElementById('systemPrompt').value = CONFIG.systemPrompt;
}
function saveSettings() {
  CONFIG.serverType = document.getElementById('serverType').value;
  CONFIG.serverUrl = document.getElementById('serverUrl').value.trim();
  CONFIG.modelName = document.getElementById('modelNameInput').value.trim();
  CONFIG.apiKey = document.getElementById('apiKeyInput').value.trim();
  CONFIG.temperature = parseFloat(document.getElementById('temperature').value);
  CONFIG.maxTokens = parseInt(document.getElementById('maxTokens').value);
  CONFIG.systemPrompt = document.getElementById('systemPrompt').value;
  Object.entries(CONFIG).forEach(([k, v]) => localStorage.setItem(k, v));
  toggleSettings(); updateStatus();
}
function updateServerUrl() {
  const map = { auto: '', ollama: 'http://localhost:11434', triton: 'http://localhost:8000', custom: '' };
  const type = document.getElementById('serverType').value;
  document.getElementById('serverUrl').value = type === 'auto' ? apiBase() : (map[type] || '');
}
function toggleSettings() { document.getElementById('settingsModal').classList.toggle('open'); }
function closeSettings(e) { if (e.target.id === 'settingsModal') toggleSettings(); }
async function testConnection() {
  const el = document.getElementById('testResult');
  el.className = 'test-result show'; el.textContent = t('test_running');
  const url = document.getElementById('serverUrl').value.trim() || apiBase();
  try {
    const r = await fetch(`${url}/health`, { signal: AbortSignal.timeout(5000) });
    const d = await r.json();
    el.className = 'test-result show success';
    el.textContent = `✓ ${d.mode}${d.ollama_connected ? ' (Ollama)' : ''}${d.security?.auth_required ? ' · 🔒 auth' : ''}`;
  } catch (e) {
    el.className = 'test-result show error';
    el.textContent = `✗ ${e.message} — ${t('mode_local')}`;
  }
}

// ─── Conversations ──────────────────────────────────────
function newConversation() {
  if (busy) stopGeneration();
  currentId = Date.now().toString(); messages = [];
  renderMessages(); renderHistory(); closeSidebar();
}
function loadConversation(id) {
  if (busy) stopGeneration();
  const c = conversations.find(x => x.id === id); if (!c) return;
  currentId = id; messages = c.messages || [];
  renderMessages(); renderHistory(); closeSidebar();
}
function saveConversation() {
  const title = (messages.find(m => m.role === 'user')?.content || 'Conversation').slice(0, 42);
  const entry = { id: currentId, title, messages, ts: Date.now() };
  const i = conversations.findIndex(c => c.id === currentId);
  if (i >= 0) conversations[i] = entry; else conversations.unshift(entry);
  conversations = conversations.slice(0, 50);
  localStorage.setItem('conversations', JSON.stringify(conversations));
  renderHistory();
}
function renderHistory() {
  document.getElementById('historyList').innerHTML = conversations.map(c =>
    `<div class="history-item ${c.id === currentId ? 'active' : ''}" onclick="loadConversation('${c.id}')">${escapeHtml(c.title)}</div>`
  ).join('') || `<div style="font-size:12px;color:var(--dim);padding:8px 10px">${t('empty_hist')}</div>`;
}

// ─── Envoi / Stop / Régénérer ───────────────────────────
function onSendClick() { busy ? stopGeneration() : sendMessage(); }

async function sendMessage() {
  const input = document.getElementById('userInput');
  const text = input.value.trim();
  if (!text || busy) return;
  if (!currentId) currentId = Date.now().toString();
  hideHero();
  input.value = ''; autoResize(input);
  messages.push({ role: 'user', content: text });
  addMessage('user', text);
  saveConversation();
  await stream();
}

function stopGeneration() {
  if (controller) { controller.abort(); controller = null; }
}

function regenerateLast() {
  if (busy) return;
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'assistant') { messages.splice(i, 1); break; }
  }
  renderMessages(); saveConversation(); stream();
}

async function stream() {
  busy = true; setBusyUI(true);
  controller = new AbortController();
  const el = addTyping();
  const bubble = el.querySelector('.bubble');
  let full = '', aborted = false;

  try {
    const res = await fetch(`${apiBase()}/v1/chat`, {
      method: 'POST', headers: authHeaders(), signal: controller.signal,
      body: JSON.stringify({
        messages, model: CONFIG.modelName, temperature: CONFIG.temperature,
        max_tokens: CONFIG.maxTokens, stream: true, system: CONFIG.systemPrompt,
      }),
    });
    if (!res.ok || !res.body) throw new Error('HTTP ' + res.status);

    bubble.innerHTML = '';
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += dec.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop();
      for (const part of parts) {
        const line = part.split('\n').find(l => l.startsWith('data: '));
        if (!line) continue;
        try {
          const dd = JSON.parse(line.slice(6));
          if (dd.error) { bubble.innerHTML = `<span class="err">⚠ ${escapeHtml(dd.error)}</span>`; continue; }
          if (dd.delta) { full += dd.delta; bubble.innerHTML = mdToHtml(full); scrollDown(); }
        } catch {}
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      aborted = true;
      if (!full) bubble.innerHTML = `<span class="muted">${t('stopped')}</span>`;
    } else {
      full = await localDemoStream(bubble);   // repli démo si réseau KO
    }
  }

  controller = null; busy = false; setBusyUI(false);
  if (full) {
    if (!messages.length || messages[messages.length - 1].role !== 'assistant')
      messages.push({ role: 'assistant', content: full });
    addAssistantActions(el, full, true);
    saveConversation();
  }
  scrollDown();
}

// Streaming démo 100 % client (aperçu statique sans backend)
async function localDemoStream(bubble) {
  const last = [...messages].reverse().find(m => m.role === 'user')?.content || '';
  const text = clientBrain(last);
  bubble.innerHTML = ''; let acc = '';
  const tokens = text.match(/\S+\s*|\n/g) || [text];
  for (const tk of tokens) {
    if (!busy) break;
    acc += tk; bubble.innerHTML = mdToHtml(acc); scrollDown();
    await new Promise(r => setTimeout(r, 14));
  }
  return acc;
}

function sendSuggestion(el) {
  document.getElementById('userInput').value = el.dataset.q || el.textContent.trim();
  sendMessage();
}
function handleKeydown(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }

function setBusyUI(b) {
  document.getElementById('sendIcon').style.display = b ? 'none' : 'block';
  document.getElementById('stopIcon').style.display = b ? 'block' : 'none';
  document.getElementById('sendBtn').classList.toggle('is-stop', b);
}

// ─── Rendu DOM ──────────────────────────────────────────
function addMessage(role, content) {
  document.getElementById('messages').appendChild(makeMsg(role, content));
  scrollDown();
}
function makeMsg(role, content) {
  const d = document.createElement('div');
  d.className = `msg ${role}`;
  const time = new Date().toLocaleTimeString(lang === 'fr' ? 'fr-FR' : 'en-US', { hour: '2-digit', minute: '2-digit' });
  d.innerHTML = `
    <div class="avatar">${role === 'user' ? t('you')[0] : 'AI'}</div>
    <div class="msg-col">
      <div class="bubble">${role === 'user' ? escapeHtml(content) : mdToHtml(content)}</div>
      <div class="msg-time">${time}</div>
    </div>`;
  return d;
}
function addAssistantActions(msgEl, content, isLast) {
  const col = msgEl.querySelector('.msg-col');
  if (!col || col.querySelector('.msg-actions')) return;
  const bar = document.createElement('div');
  bar.className = 'msg-actions';
  bar.innerHTML = `
    <button class="act-btn" data-content="${encodeURIComponent(content)}" onclick="copyMessage(this)">
      <svg viewBox="0 0 16 16" width="13" height="13" fill="none"><rect x="5" y="5" width="8" height="8" rx="1.5" stroke="currentColor" stroke-width="1.4"/><path d="M3 11V3.5C3 3.2 3.2 3 3.5 3H11" stroke="currentColor" stroke-width="1.4"/></svg>
      <span class="lbl">${t('copy')}</span>
    </button>
    ${isLast ? `<button class="act-btn" onclick="regenerateLast()">
      <svg viewBox="0 0 16 16" width="13" height="13" fill="none"><path d="M13 8a5 5 0 1 1-1.5-3.5M13 2v3h-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span class="lbl">${t('regenerate')}</span>
    </button>` : ''}`;
  col.appendChild(bar);
}
function copyMessage(btn) {
  const text = decodeURIComponent(btn.dataset.content || '');
  navigator.clipboard?.writeText(text).then(() => {
    const lbl = btn.querySelector('.lbl'); const old = lbl.textContent;
    lbl.textContent = t('copied'); btn.classList.add('ok');
    setTimeout(() => { lbl.textContent = old; btn.classList.remove('ok'); }, 1300);
  });
}
function addTyping() {
  const d = document.createElement('div');
  d.className = 'msg assistant';
  d.innerHTML = `<div class="avatar">AI</div><div class="msg-col">
    <div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div></div>`;
  document.getElementById('messages').appendChild(d);
  scrollDown();
  return d;
}
function renderMessages() {
  const c = document.getElementById('messages');
  c.innerHTML = '';
  if (!messages.length) { c.innerHTML = heroHTML(); applyLang(); return; }
  const lastAssistant = messages.map(m => m.role).lastIndexOf('assistant');
  messages.forEach((m, idx) => {
    const el = makeMsg(m.role, m.content);
    c.appendChild(el);
    if (m.role === 'assistant') addAssistantActions(el, m.content, idx === lastAssistant);
  });
  scrollDown();
}
function hideHero() { const h = document.getElementById('hero'); if (h) h.remove(); }
function scrollDown() { const m = document.getElementById('messages'); m.scrollTop = m.scrollHeight; }
function autoResize(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 180) + 'px'; }

function clearChat() {
  if (!messages.length || !confirm(t('confirm_clear'))) return;
  const i = conversations.findIndex(c => c.id === currentId);
  if (i >= 0) conversations.splice(i, 1);
  localStorage.setItem('conversations', JSON.stringify(conversations));
  newConversation();
}
function exportChat() {
  if (!messages.length) return;
  const txt = messages.map(m => `[${m.role.toUpperCase()}]\n${m.content}`).join('\n\n———\n\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([txt], { type: 'text/plain' }));
  a.download = `techcorp-chat-${Date.now()}.txt`; a.click();
}

function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }
function closeSidebar() { document.getElementById('sidebar').classList.remove('open'); }

function heroHTML() {
  return `
  <section class="hero" id="hero">
    <div class="hero-orb"><svg viewBox="0 0 24 24" width="34" height="34" fill="none"><path d="M4 16l5-5 4 4 7-8" stroke="white" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="20" cy="7" r="2" fill="white"/></svg></div>
    <h2 id="heroTitle" data-i18n="hero_title">${t('hero_title')}</h2>
    <p id="heroSub" data-i18n="hero_sub">${t('hero_sub')}</p>
    <div class="cards">
      <button class="card" onclick="sendSuggestion(this)" data-q="Explique-moi les 3 composantes d'un bilan financier.">
        <div class="card-ic ic-blue"><svg viewBox="0 0 20 20" width="18" height="18" fill="none"><path d="M3 17h14M5 17V9M9 17V5M13 17v-7M17 17V3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg></div>
        <div><strong data-i18n="card1_t">${t('card1_t')}</strong><span data-i18n="card1_s">${t('card1_s')}</span></div></button>
      <button class="card" onclick="sendSuggestion(this)" data-q="Quelle stratégie d'investissement pour diversifier un portefeuille ?">
        <div class="card-ic ic-violet"><svg viewBox="0 0 20 20" width="18" height="18" fill="none"><path d="M10 2v16M10 2l5 4M10 2L5 6M4 12c0 3 2.7 5 6 5s6-2 6-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
        <div><strong data-i18n="card2_t">${t('card2_t')}</strong><span data-i18n="card2_s">${t('card2_s')}</span></div></button>
      <button class="card" onclick="sendSuggestion(this)" data-q="Comment évaluer la valorisation d'une startup ?">
        <div class="card-ic ic-emerald"><svg viewBox="0 0 20 20" width="18" height="18" fill="none"><path d="M10 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4L10 14.3 5.2 16.7l.9-5.4L2.2 7.7l5.4-.8L10 2z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg></div>
        <div><strong data-i18n="card3_t">${t('card3_t')}</strong><span data-i18n="card3_s">${t('card3_s')}</span></div></button>
      <button class="card" onclick="sendSuggestion(this)" data-q="Quels sont les principaux risques financiers et comment les gérer ?">
        <div class="card-ic ic-amber"><svg viewBox="0 0 20 20" width="18" height="18" fill="none"><path d="M10 2.5l7 12.5H3L10 2.5z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M10 8v3.5M10 13.5v.01" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg></div>
        <div><strong data-i18n="card4_t">${t('card4_t')}</strong><span data-i18n="card4_s">${t('card4_s')}</span></div></button>
    </div>
  </section>`;
}

// ─── Mini-cerveau financier côté client (repli aperçu) ──
function clientBrain(q) {
  const x = (q || '').toLowerCase();
  if (/^(bonjour|salut|hello|hi|hey|coucou)/.test(x) || x.length < 4)
    return "Bonjour 👋 Je suis **Phi-3.5-Financial**. Posez-moi une question sur l'analyse financière, l'investissement ou la valorisation.";
  if (x.includes('roi') || x.includes('rentab'))
    return "**Le ROI (Return on Investment)**\n\nMesure la rentabilité d'un investissement.\n\n```\nROI = (Gain net / Coût) × 100\n```\n\n**Exemple :** 10 000 € qui rapportent 12 500 € → **ROI = 25 %**.\n\n> 💡 *Aperçu en mode démo local.*";
  if (x.includes('bilan') || x.includes('actif') || x.includes('passif'))
    return "**Les 3 composantes d'un bilan**\n\n1. **Actif** — ce que l'entreprise possède\n2. **Passif** — ce qu'elle doit\n3. **Capitaux propres** — ce qui revient aux actionnaires\n\n```\nActif = Passif + Capitaux propres\n```";
  if (x.includes('diversif') || x.includes('portefeuille') || x.includes('investiss'))
    return "**Diversification de portefeuille**\n\n- Répartir entre **classes d'actifs**\n- Varier **secteurs** et **zones géographiques**\n- Réduit le **risque spécifique**\n\n*Principe de Markowitz (1952).*";
  if (x.includes('startup') || x.includes('valoris'))
    return "**Valoriser une startup**\n\n- **Comparables** : VE/CA, VE/ARR\n- **Méthode Berkus** (pré-revenus)\n- **Venture Capital** : valeur de sortie / rendement attendu";
  if (x.includes('risque') || x.includes('var'))
    return "**Gestion des risques**\n\n| Type | Couverture |\n|------|------------|\n| Marché | Dérivés, hedging |\n| Crédit | Garanties |\n| Liquidité | Trésorerie de réserve |\n\nMesure : **VaR**, **volatilité (σ)**, **bêta (β)**.";
  return "Voici une analyse structurée :\n\n**Points clés** — rentabilité, risque, horizon temporel et coût d'opportunité.\n\n> 💡 *Mode démo local. Lancez `python run.py` pour le serveur, ou Ollama pour le vrai Phi-3.5-Financial.*";
}

// ─── Markdown → HTML (parser par blocs) ─────────────────
function mdToHtml(src) {
  if (!src) return '';
  const lines = src.replace(/\r/g, '').split('\n');
  let html = '', i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {
      const lng = line.slice(3).trim(); let code = ''; i++;
      while (i < lines.length && !/^```/.test(lines[i])) { code += lines[i] + '\n'; i++; }
      i++; html += `<pre><code${lng ? ` class="language-${lng}"` : ''}>${escapeHtml(code.replace(/\n$/, ''))}</code></pre>`; continue;
    }
    let m;
    if ((m = line.match(/^(#{1,3})\s+(.*)$/))) { const n = m[1].length; html += `<h${n}>${inline(m[2])}</h${n}>`; i++; continue; }
    if (/^>\s?/.test(line)) {
      let q = ''; while (i < lines.length && /^>\s?/.test(lines[i])) { q += lines[i].replace(/^>\s?/, '') + ' '; i++; }
      html += `<blockquote>${inline(q.trim())}</blockquote>`; continue;
    }
    if (line.includes('|') && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i + 1]) && lines[i + 1].includes('-')) {
      const head = splitRow(line); i += 2; let rows = '';
      while (i < lines.length && lines[i].includes('|')) { rows += `<tr>${splitRow(lines[i]).map(c => `<td>${inline(c)}</td>`).join('')}</tr>`; i++; }
      html += `<table><thead><tr>${head.map(c => `<th>${inline(c)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>`; continue;
    }
    if (/^\s*[-*•]\s+/.test(line)) {
      let items = ''; while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) { items += `<li>${inline(lines[i].replace(/^\s*[-*•]\s+/, ''))}</li>`; i++; }
      html += `<ul>${items}</ul>`; continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      let items = ''; while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) { items += `<li>${inline(lines[i].replace(/^\s*\d+\.\s+/, ''))}</li>`; i++; }
      html += `<ol>${items}</ol>`; continue;
    }
    if (line.trim() === '') { i++; continue; }
    let para = line; i++;
    while (i < lines.length && lines[i].trim() !== '' && !/^(#{1,3}\s|>|```|\s*[-*•]\s|\s*\d+\.\s)/.test(lines[i]) && !lines[i].includes('|')) { para += ' ' + lines[i]; i++; }
    html += `<p>${inline(para)}</p>`;
  }
  return html;
}
function splitRow(row) { return row.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(s => s.trim()); }
function inline(s) {
  s = escapeHtml(s);
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
  return s;
}
function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
