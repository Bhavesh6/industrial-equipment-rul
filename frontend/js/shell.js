// Renders the shared console shell (sidebar + topbar) for EquipmentHealth
// Ensures all authenticated pages share identical navigation and styling.

const Shell = {
  nav: [
    { section: 'Operations' },
    { id: 'admin', href: 'admin.html', icon: 'fa-gauge-high', label: 'SCADA Overview' },
    { id: 'analytics', href: 'analytics.html', icon: 'fa-chart-simple', label: 'Prognostics & SHAP' },
    { id: 'alerts', href: 'alerts.html', icon: 'fa-triangle-exclamation', label: 'Anomaly Alerts' },
    { id: 'violations', href: 'violations.html', icon: 'fa-wave-square', label: 'Waveform Scopes' },
    { section: 'Diagnostics & History' },
    { id: 'reports', href: 'reports.html', icon: 'fa-file-lines', label: 'Historian Reports' },
    { id: 'settings', href: 'settings.html', icon: 'fa-sliders', label: 'Sensor Calibration' },
    { id: 'audit', href: 'audit.html', icon: 'fa-scroll', label: 'Parameter Audit' },
    { section: 'Public Landing' },
    { id: 'index', href: 'index.html', icon: 'fa-arrow-up-right-from-square', label: 'Public Showcase' }
  ],

  initials(name) {
    if (!name) return 'EH';
    return name.trim().split(/\s+/).slice(0, 2).map((p) => p[0].toUpperCase()).join('');
  },

  render(activeId, { title, subtitle } = {}) {
    const user = (typeof Auth !== 'undefined' && Auth.getUser && Auth.getUser()) || { name: 'Lead Engineer', is_admin: true };
    const isAdmin = true;

    const visible = this.nav;

    const navHtml = visible
      .map((item) => {
        if (item.section) return `<div class="sidebar-section">${item.section}</div>`;
        const active = item.id === activeId ? ' is-active' : '';
        const current = item.id === activeId ? ' aria-current="page"' : '';
        return `<a href="${item.href}" class="nav-item${active}"${current} title="${item.label}">
                  <i class="fas ${item.icon}" aria-hidden="true"></i><span class="nav-label">${item.label}</span>
                </a>`;
      })
      .join('');

    let roleLabel = 'Diagnostic Engineer';
    let roleBadgeClass = 'badge-amber';
    let roleTier = 'admin';

    const sidebar = document.createElement('aside');
    sidebar.className = 'sidebar';
    sidebar.id = 'appSidebar';
    sidebar.dataset.role = roleTier;
    sidebar.innerHTML = `
      <div class="sidebar-brand-row">
        <a href="index.html" class="sidebar-brand" title="EquipmentHealth">
          <span class="sidebar-mark" style="background:var(--accent);color:#fff;border-radius:8px;padding:6px 9px;"><i class="fas fa-bolt" aria-hidden="true"></i></span>
          <span class="sidebar-brand-text">
            <span class="sidebar-name" style="font-family:var(--font-head);font-weight:700;">EquipmentHealth</span><br>
            <span class="sidebar-sub" style="font-size:0.70rem;color:var(--muted);">RS-380 IIoT Digital Twin</span>
          </span>
        </a>
        <button class="sidebar-collapse-btn" id="menuToggle" aria-label="Toggle navigation" aria-expanded="true">
          <i class="fas fa-angles-left" aria-hidden="true"></i>
        </button>
      </div>
      <nav class="sidebar-nav" aria-label="Main">${navHtml}</nav>
      <div class="sidebar-foot">
        <div class="sidebar-user" title="${user.name || 'Engineer'} — ${roleLabel}">
          <span class="avatar" style="background:var(--accent);color:#fff;">${this.initials(user.name)}</span>
          <span class="sidebar-user-text">
            <span class="sidebar-user-name">${user.name || 'Lead Engineer'}</span><br>
            <span class="badge ${roleBadgeClass}" style="margin-top:3px;font-size:.62rem;padding:1px 8px">${roleLabel}</span>
          </span>
        </div>
        <div style="margin-top:10px;font-size:0.72rem;color:var(--muted);display:flex;justify-content:space-between;">
          <span>Node: <strong>ESP32-S3</strong></span>
          <span style="color:var(--ok);"><strong>● 50 Hz Live</strong></span>
        </div>
      </div>`;

    const main = document.querySelector('.main');
    const topbar = document.createElement('header');
    topbar.className = 'topbar';
    topbar.innerHTML = `
      <div style="display:flex;align-items:center;gap:14px;min-width:0">
        <button class="btn btn-outline btn-sm menu-toggle-mobile" id="menuToggleMobile" aria-label="Open navigation" aria-expanded="false">
          <i class="fas fa-bars" aria-hidden="true"></i>
        </button>
        <div style="min-width:0">
          <h1 style="font-family:var(--font-head);margin:0;font-size:1.35rem;">${title || 'Equipment Health Monitoring'}</h1>
          ${subtitle ? `<div class="topbar-sub" style="font-size:0.80rem;color:var(--muted);">${subtitle}</div>` : ''}
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:12px">
        <div class="pill ok" style="font-size:0.76rem;padding:4px 10px;">
          <span class="pulse-dot" style="background:var(--ok);width:7px;height:7px;border-radius:50%;display:inline-block;"></span>
          <span>RS-380 Cell 01: <strong>Normal</strong></span>
        </div>
        <a href="index.html" class="btn btn-outline btn-sm" title="Public View"><i class="fas fa-arrow-up-right-from-square"></i></a>
      </div>`;

    if (main) {
      main.insertBefore(topbar, main.firstChild);
    }
    const app = document.querySelector('.app');
    if (app) {
      app.insertBefore(sidebar, app.firstChild);
    }

    // Bind sidebar collapse toggle
    const toggle = document.getElementById('menuToggle');
    if (toggle) {
      toggle.addEventListener('click', () => {
        const isCollapsed = sidebar.classList.toggle('is-collapsed');
        toggle.setAttribute('aria-expanded', !isCollapsed);
      });
    }

    const mobileToggle = document.getElementById('menuToggleMobile');
    if (mobileToggle) {
      mobileToggle.addEventListener('click', () => {
        sidebar.classList.toggle('is-open-mobile');
      });
    }
  }
};

window.Shell = Shell;
