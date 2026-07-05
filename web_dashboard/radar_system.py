"""Enhanced Web5 interactive radar dashboard with real-time forensic visualization.

Produces a complete, self-contained HTML file that serves as the ARGUS-PANTHER
ULTIMA mission-control dashboard.  The output includes:

* Animated starry-night background with shooting stars
* 3D rotating Earth with city lights and orbiting Moon
* Animated Air Force One (2026 livery) with F-47 escorts
* Full forensic intelligence dashboard with 12+ data panels
* Interactive entity drill-down, seizure payload controls, and report export
* Responsive layout for mobile (Samsung S26 Ultra, iPhone 17 Pro Max) and desktop
* Dark / light mode toggle

Usage::

    html = generate_radar_html()
    with open("dashboard.html", "w") as f:
        f.write(html)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

NAVY: str = "#1a2a6a"
WHITE: str = "#ffffff"
GOLD: str = "#d4af37"
RED: str = "#c41e3a"
SKY_BLUE: str = "#4a90d9"


def generate_radar_html(
    title: str = "ARGUS-PANTHER ULTIMA | Forensic Intelligence Command",
    refresh_interval_ms: int = 5000,
) -> str:
    """Generate the complete, self-contained radar dashboard HTML."""
    return _HTML_TEMPLATE.format(
        title=title, navy=NAVY, white=WHITE, gold=GOLD, red=RED,
        sky_blue=SKY_BLUE, refresh_interval=refresh_interval_ms,
    )


_HTML_TEMPLATE: str = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>{title}</title>
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --navy:{navy};--white:{white};--gold:{gold};--red:{red};--sky:{sky_blue};
  --bg-dark:#050a1a;--bg-panel:rgba(10,20,50,0.85);--border-gold:rgba(212,175,55,0.4);
  --text-main:#e0e6f0;--text-dim:#7a8ab0;
  --font-main:'Segoe UI',system-ui,-apple-system,sans-serif;
  --font-mono:'SF Mono',Monaco,'Cascadia Code',monospace;
}}
body{{
  font-family:var(--font-main);background:var(--bg-dark);color:var(--text-main);
  overflow-x:hidden;min-height:100vh;
}}
body.light-mode{{--bg-dark:#e8ecf4;--bg-panel:rgba(255,255,255,0.92);--text-main:#1a1a2e;--text-dim:#556;--border-gold:rgba(26,42,106,0.3)}}

#starfield{{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}}
#earth-container{{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:1;pointer-events:none;opacity:0.12;width:min(500px,85vw);height:min(500px,85vw)}}
.earth{{width:100%;height:100%;border-radius:50%;background:
  radial-gradient(circle at 35% 35%,rgba(74,144,217,0.3),transparent 50%),
  radial-gradient(circle at 65% 65%,rgba(26,42,106,0.6),transparent 50%),
  radial-gradient(circle at 50% 50%,{navy},#0a1428);
  box-shadow:inset -20px -20px 50px rgba(0,0,0,0.8),0 0 60px rgba(74,144,217,0.2);
  animation:earthRot 80s linear infinite;position:relative}}
@keyframes earthRot{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
.moon{{position:absolute;width:60px;height:60px;border-radius:50%;background:radial-gradient(circle at 40% 40%,#e8e8e8,#555);box-shadow:0 0 20px rgba(255,255,255,0.1),inset -6px -6px 15px rgba(0,0,0,0.3);top:8%;right:3%;animation:moonOrb 40s linear infinite}}
.moon::before{{content:'';position:absolute;width:10px;height:10px;border-radius:50%;background:rgba(100,100,100,0.4);top:20%;left:30%}}
.moon::after{{content:'';position:absolute;width:6px;height:6px;border-radius:50%;background:rgba(100,100,100,0.3);top:55%;left:55%}}
@keyframes moonOrb{{0%{{transform:rotate(0deg) translateX(220px) rotate(0deg)}}100%{{transform:rotate(360deg) translateX(220px) rotate(-360deg)}}}}

#flight-container{{position:fixed;bottom:12%;left:0;width:100%;height:100px;z-index:2;pointer-events:none;overflow:hidden}}
.af1{{position:absolute;display:flex;align-items:center;gap:3px;animation:flyAF1 25s linear infinite}}
.af1-fuselage{{width:clamp(55px,9vw,90px);height:clamp(10px,1.8vw,16px);background:linear-gradient(180deg,var(--white) 0%,var(--white) 30%,{navy} 30%,{navy} 70%,var(--white) 70%);border-radius:0 50% 50% 0;position:relative;border:1px solid var(--gold)}}
.af1-fuselage::before{{content:'';position:absolute;left:-12px;top:50%;transform:translateY(-50%);width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent;border-right:16px solid {navy}}}
.af1-tail{{width:0;height:0;border-left:clamp(9px,1.3vw,14px) solid {navy};border-top:clamp(7px,1vw,10px) solid transparent;border-bottom:clamp(7px,1vw,10px) solid transparent;position:relative}}
.af1-tail::after{{content:'';position:absolute;left:-10px;top:-3px;width:6px;height:6px;background:{red};border-radius:50%}}
.escort{{position:absolute;animation:flyEsc 25s linear infinite;opacity:0.85}}
.escort-jet{{width:clamp(13px,2.2vw,20px);height:clamp(3px,0.6vw,5px);background:linear-gradient(90deg,{navy},{sky_blue});border-radius:0 40% 40% 0;position:relative}}
.escort-jet::before{{content:'';position:absolute;left:-5px;top:50%;transform:translateY(-50%);width:0;height:0;border-top:2.5px solid transparent;border-bottom:2.5px solid transparent;border-right:7px solid {navy}}}
.escort:nth-child(2){{animation-delay:-2s;margin-top:-25px}}
.escort:nth-child(3){{animation-delay:-4s;margin-top:22px}}
.escort:nth-child(4){{animation-delay:-6s;margin-top:-42px}}
.escort:nth-child(5){{animation-delay:-8s;margin-top:38px}}
.escort:nth-child(6){{animation-delay:-10s;margin-top:-58px}}
.escort:nth-child(7){{animation-delay:-12s;margin-top:52px}}
.escort:nth-child(8){{animation-delay:-14s;margin-top:-72px}}
.escort:nth-child(9){{animation-delay:-16s;margin-top:65px}}
.escort:nth-child(10){{animation-delay:-18s;margin-top:-82px}}
.escort:nth-child(11){{animation-delay:-20s;margin-top:78px}}
.escort:nth-child(12){{animation-delay:-22s;margin-top:-92px}}
.escort:nth-child(13){{animation-delay:-24s;margin-top:88px}}
@keyframes flyAF1{{0%{{left:-120px}}100%{{left:110%}}}}
@keyframes flyEsc{{0%{{left:-60px;opacity:0.6}}50%{{opacity:1}}100%{{left:110%;opacity:0.6}}}}

#intro-overlay{{position:fixed;inset:0;z-index:1000;background:var(--bg-dark);display:flex;flex-direction:column;align-items:center;justify-content:center;transition:opacity 2s ease}}
#intro-overlay.hidden{{opacity:0;pointer-events:none}}
.intro-title{{font-size:clamp(1.4rem,5vw,3.2rem);font-weight:900;color:var(--gold);text-shadow:0 0 30px rgba(212,175,55,0.5);letter-spacing:0.15em;text-align:center;padding:0 1rem}}
.intro-subtitle{{font-size:clamp(0.75rem,2vw,1.1rem);color:var(--text-dim);margin-top:1rem;letter-spacing:0.3em;text-transform:uppercase}}
.intro-progress{{width:min(380px,78vw);height:3px;background:rgba(212,175,55,0.2);margin-top:2.5rem;border-radius:2px;overflow:hidden}}
.intro-progress-bar{{height:100%;width:0%;background:linear-gradient(90deg,var(--gold),var(--sky));animation:introLoad 4s ease forwards}}
@keyframes introLoad{{0%{{width:0%}}60%{{width:70%}}100%{{width:100%}}}}

#dashboard{{position:relative;z-index:10;display:none;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:0.8rem;padding:0.8rem;max-width:1920px;margin:0 auto;animation:dashFade 1s ease forwards}}
#dashboard.visible{{display:grid}}
@keyframes dashFade{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:translateY(0)}}}}

.dash-header{{grid-column:1/-1;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:0.8rem;padding:1rem 1.2rem;background:var(--bg-panel);border:1px solid var(--border-gold);border-radius:12px;backdrop-filter:blur(10px)}}
.dash-header h1{{font-size:clamp(1.1rem,3vw,1.8rem);color:var(--gold);letter-spacing:0.1em;text-transform:uppercase}}
.dash-header .badge{{padding:0.25rem 0.7rem;border-radius:20px;font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em}}
.badge-active{{background:rgba(40,167,69,0.2);color:#28a745;border:1px solid rgba(40,167,69,0.4)}}
.badge-critical{{background:rgba(196,30,58,0.2);color:var(--red);border:1px solid rgba(196,30,58,0.4);animation:pulseB 2s ease infinite}}
@keyframes pulseB{{0%,100%{{opacity:1}}50%{{opacity:0.6}}}}
.header-controls{{display:flex;gap:0.4rem;flex-wrap:wrap}}
.ctrl-btn{{padding:0.35rem 0.75rem;border:1px solid var(--border-gold);background:rgba(212,175,55,0.1);color:var(--gold);border-radius:6px;cursor:pointer;font-size:0.75rem;font-weight:600;transition:all 0.2s;text-transform:uppercase;letter-spacing:0.05em}}
.ctrl-btn:hover{{background:rgba(212,175,55,0.25);transform:translateY(-1px)}}
.ctrl-btn.danger{{background:rgba(196,30,58,0.15);color:var(--red);border-color:rgba(196,30,58,0.4)}}
.ctrl-btn.danger:hover{{background:rgba(196,30,58,0.3)}}

.panel{{background:var(--bg-panel);border:1px solid var(--border-gold);border-radius:12px;padding:1rem;backdrop-filter:blur(8px);transition:transform 0.2s,box-shadow 0.2s;position:relative;overflow:hidden}}
.panel:hover{{transform:translateY(-2px);box-shadow:0 8px 30px rgba(0,0,0,0.3)}}
.panel::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--gold),transparent);opacity:0.6}}
.panel-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:0.6rem}}
.panel-title{{font-size:0.8rem;font-weight:700;color:var(--gold);text-transform:uppercase;letter-spacing:0.08em;display:flex;align-items:center;gap:0.3rem}}
.panel-value{{font-family:var(--font-mono);font-size:clamp(1.3rem,3vw,1.8rem);font-weight:800;color:var(--white)}}
.panel-sub{{font-size:0.7rem;color:var(--text-dim);margin-top:0.15rem}}

.risk-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:0.4rem;margin-top:0.4rem}}
.risk-item{{padding:0.4rem;border-radius:8px;font-size:0.7rem;font-weight:600;display:flex;align-items:center;justify-content:space-between;cursor:pointer;transition:transform 0.15s}}
.risk-item:hover{{transform:scale(1.03)}}
.risk-critical{{background:rgba(196,30,58,0.15);border:1px solid rgba(196,30,58,0.3);color:#ff6b6b}}
.risk-high{{background:rgba(255,152,0,0.12);border:1px solid rgba(255,152,0,0.3);color:#ff9800}}
.risk-medium{{background:rgba(255,235,59,0.1);border:1px solid rgba(255,235,59,0.25);color:#ffeb3b}}
.risk-low{{background:rgba(76,175,80,0.1);border:1px solid rgba(76,175,80,0.25);color:#4caf50}}
.risk-count{{font-family:var(--font-mono);font-size:0.9rem;font-weight:800}}

.heat-bar{{display:flex;height:22px;border-radius:6px;overflow:hidden;margin-top:0.4rem;border:1px solid var(--border-gold)}}
.heat-segment{{flex:1;display:flex;align-items:center;justify-content:center;font-size:0.55rem;font-weight:700;color:#fff;transition:flex 0.3s;cursor:pointer}}
.heat-segment:hover{{flex:2}}

.flow-container{{display:flex;align-items:center;gap:0.25rem;margin-top:0.4rem;overflow-x:auto;padding:0.2rem}}
.flow-node{{min-width:45px;padding:0.35rem 0.4rem;background:rgba(74,144,217,0.15);border:1px solid rgba(74,144,217,0.3);border-radius:6px;font-size:0.6rem;text-align:center;font-weight:600;white-space:nowrap}}
.flow-node.wallet{{background:rgba(76,175,80,0.15);border-color:rgba(76,175,80,0.3);color:#81c784}}
.flow-node.mixer{{background:rgba(255,152,0,0.15);border-color:rgba(255,152,0,0.3);color:#ffb74d}}
.flow-node.exchange{{background:rgba(156,39,176,0.15);border-color:rgba(156,39,176,0.3);color:#ce93d8}}
.flow-arrow{{color:var(--gold);font-size:0.7rem;animation:flowP 1.5s ease infinite}}
@keyframes flowP{{0%,100%{{opacity:0.4}}50%{{opacity:1}}}}

.gauge-wrapper{{display:flex;flex-direction:column;align-items:center;margin-top:0.4rem}}
.gauge-svg{{width:clamp(90px,14vw,130px);height:clamp(50px,7vw,68px)}}
.gauge-value{{font-family:var(--font-mono);font-size:clamp(0.9rem,2vw,1.2rem);font-weight:800;color:var(--red);margin-top:-4px}}
.gauge-label{{font-size:0.6rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.05em}}

.network-canvas{{width:100%;height:clamp(130px,18vw,200px);border-radius:8px;background:rgba(5,10,26,0.5);border:1px solid var(--border-gold);margin-top:0.4rem;cursor:grab}}
.odometer{{display:flex;gap:2px;justify-content:center;margin-top:0.4rem}}
.odigit{{width:clamp(18px,2.8vw,26px);height:clamp(28px,4vw,38px);background:linear-gradient(180deg,rgba(10,20,50,0.9),rgba(26,42,106,0.6));border:1px solid var(--border-gold);border-radius:4px;display:flex;align-items:center;justify-content:center;font-family:var(--font-mono);font-size:clamp(0.9rem,2vw,1.3rem);font-weight:800;color:var(--gold);box-shadow:inset 0 0 8px rgba(212,175,55,0.1)}}

.status-list{{display:flex;flex-direction:column;gap:0.3rem;margin-top:0.4rem}}
.status-row{{display:flex;align-items:center;gap:0.5rem;padding:0.35rem 0.4rem;border-radius:6px;font-size:0.7rem}}
.status-row:hover{{background:rgba(212,175,55,0.05)}}
.status-dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.dot-ready{{background:#4caf50;box-shadow:0 0 6px rgba(76,175,80,0.5)}}
.dot-pending{{background:#ff9800;animation:dotP 1.5s ease infinite}}
.dot-blocked{{background:var(--red);animation:dotP 1s ease infinite}}
@keyframes dotP{{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}

.ticker-wrap{{overflow:hidden;border-radius:6px;background:rgba(0,0,0,0.2);margin-top:0.4rem;padding:0.3rem 0}}
.ticker{{display:flex;gap:2rem;white-space:nowrap;animation:tickScroll 30s linear infinite}}
.ticker:hover{{animation-play-state:paused}}
.ticker-item{{font-size:0.65rem;color:var(--text-dim);display:flex;align-items:center;gap:0.25rem}}
.ticker-item .up{{color:#4caf50}} .ticker-item .down{{color:var(--red)}}
@keyframes tickScroll{{0%{{transform:translateX(0)}}100%{{transform:translateX(-50%)}}}}

.alert-feed{{display:flex;flex-direction:column;gap:0.25rem;margin-top:0.4rem;max-height:180px;overflow-y:auto}}
.alert-item{{padding:0.35rem 0.4rem;border-radius:6px;font-size:0.65rem;border-left:3px solid var(--gold);background:rgba(212,175,55,0.05);display:flex;align-items:center;gap:0.3rem;cursor:pointer}}
.alert-item:hover{{background:rgba(212,175,55,0.1)}}
.alert-item.sev-1{{border-left-color:var(--red);background:rgba(196,30,58,0.05)}}
.alert-item.sev-2{{border-left-color:#ff9800;background:rgba(255,152,0,0.05)}}
.alert-time{{font-family:var(--font-mono);font-size:0.55rem;color:var(--text-dim);flex-shrink:0}}

.macro-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:0.4rem;margin-top:0.4rem}}
.macro-cell{{padding:0.4rem;border-radius:6px;background:rgba(0,0,0,0.15);text-align:center}}
.macro-label{{font-size:0.55rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.05em}}
.macro-value{{font-family:var(--font-mono);font-size:clamp(0.7rem,1.4vw,1rem);font-weight:700;color:var(--white);margin-top:0.1rem}}

.news-ticker{{margin-top:0.4rem;padding:0.4rem;border-radius:6px;background:rgba(212,175,55,0.05);border:1px solid var(--border-gold)}}
.news-item{{font-size:0.7rem;padding:0.25rem 0;border-bottom:1px solid rgba(212,175,55,0.1);display:flex;gap:0.4rem;align-items:flex-start}}
.news-item:last-child{{border-bottom:none}}
.news-dot{{width:5px;height:5px;border-radius:50%;background:var(--gold);margin-top:0.25rem;flex-shrink:0}}

#modal-overlay{{position:fixed;inset:0;z-index:2000;background:rgba(0,0,0,0.7);backdrop-filter:blur(4px);display:none;align-items:center;justify-content:center;padding:1rem}}
#modal-overlay.active{{display:flex}}
.modal-content{{background:var(--bg-panel);border:1px solid var(--border-gold);border-radius:12px;padding:1.2rem;max-width:550px;width:100%;max-height:80vh;overflow-y:auto;position:relative;box-shadow:0 20px 60px rgba(0,0,0,0.5)}}
.modal-close{{position:absolute;top:0.6rem;right:0.6rem;width:26px;height:26px;border-radius:50%;border:1px solid var(--border-gold);background:rgba(212,175,55,0.1);color:var(--gold);cursor:pointer;font-size:0.9rem;display:flex;align-items:center;justify-content:center}}
.modal-title{{font-size:1rem;font-weight:800;color:var(--gold);margin-bottom:0.6rem}}
.modal-body{{font-size:0.8rem;line-height:1.5;color:var(--text-main)}}

#confirm-dialog{{position:fixed;inset:0;z-index:3000;background:rgba(0,0,0,0.8);backdrop-filter:blur(6px);display:none;align-items:center;justify-content:center;padding:1rem}}
#confirm-dialog.active{{display:flex}}
.confirm-box{{background:linear-gradient(135deg,rgba(26,42,106,0.95),rgba(10,20,50,0.98));border:2px solid var(--red);border-radius:16px;padding:1.5rem;max-width:420px;width:100%;text-align:center;box-shadow:0 0 60px rgba(196,30,58,0.3)}}
.confirm-title{{font-size:1.1rem;font-weight:900;color:var(--red);margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.1em}}
.confirm-text{{font-size:0.8rem;color:var(--text-main);margin-bottom:1.2rem;line-height:1.4}}
.confirm-buttons{{display:flex;gap:0.8rem;justify-content:center}}
.confirm-btn{{padding:0.5rem 1.2rem;border-radius:8px;font-size:0.8rem;font-weight:700;cursor:pointer;transition:all 0.2s;text-transform:uppercase;letter-spacing:0.05em}}
.confirm-yes{{background:var(--red);color:var(--white);border:none}}
.confirm-yes:hover{{background:#a01830;transform:scale(1.05)}}
.confirm-no{{background:transparent;color:var(--text-dim);border:1px solid var(--text-dim)}}

#toast-container{{position:fixed;bottom:1rem;right:1rem;z-index:4000;display:flex;flex-direction:column;gap:0.5rem}}
.toast{{padding:0.6rem 0.9rem;border-radius:8px;font-size:0.75rem;font-weight:600;color:#fff;transform:translateX(120%);animation:toastSlide 0.3s ease forwards}}
.toast.success{{background:rgba(40,167,69,0.9)}}
.toast.error{{background:rgba(196,30,58,0.9)}}
.toast.info{{background:rgba(74,144,217,0.9)}}
@keyframes toastSlide{{to{{transform:translateX(0)}}}}
.toast.fade-out{{animation:toastFade 0.3s ease forwards}}
@keyframes toastFade{{to{{opacity:0;transform:translateX(120%)}}}}

@media(max-width:768px){{
  #dashboard{{grid-template-columns:1fr;padding:0.5rem;gap:0.5rem}}
  .dash-header{{flex-direction:column;text-align:center}}
  #flight-container{{display:none}}
  #earth-container{{opacity:0.06;width:95vw;height:95vw}}
}}
::-webkit-scrollbar{{width:5px}}
::-webkit-scrollbar-track{{background:rgba(0,0,0,0.1)}}
::-webkit-scrollbar-thumb{{background:rgba(212,175,55,0.3);border-radius:3px}}
</style>
</head>
<body>
<canvas id="starfield"></canvas>
<div id="earth-container"><div class="earth"></div><div class="moon"></div></div>
<div id="flight-container">
  <div class="af1"><div class="af1-tail"></div><div class="af1-fuselage"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
  <div class="escort"><div class="escort-jet"></div></div>
</div>
<div id="intro-overlay">
  <div class="intro-title">ARGUS-PANTHER ULTIMA</div>
  <div class="intro-subtitle">Forensic Intelligence Command & Control</div>
  <div class="intro-progress"><div class="intro-progress-bar"></div></div>
</div>
<div id="dashboard">
  <div class="dash-header">
    <div>
      <h1>ARGUS-PANTHER ULTIMA</h1>
      <div style="font-size:0.7rem;color:var(--text-dim);margin-top:0.15rem">
        Unified Forensic Intelligence &bull; <span id="clock">--:--:-- UTC</span>
      </div>
    </div>
    <span class="badge badge-active" id="system-status">SYSTEM ACTIVE</span>
    <div class="header-controls">
      <button class="ctrl-btn" onclick="toggleTheme()">&#127771; Theme</button>
      <button class="ctrl-btn" onclick="lockTargets()">&#128274; Lock</button>
      <button class="ctrl-btn danger" onclick="fireSeizurePayload()">&#128680; SEIZE</button>
      <button class="ctrl-btn" onclick="exportReport('pdf')">&#128196; PDF</button>
      <button class="ctrl-btn" onclick="exportReport('json')">&#128202; JSON</button>
    </div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#9888; Entity Risk Matrix</div>
      <div class="panel-value" id="risk-total">2,847</div>
    </div>
    <div class="panel-sub">Tracked entities across 194 jurisdictions</div>
    <div class="risk-grid">
      <div class="risk-item risk-critical" onclick="showEntityDetail('critical')"><span>CRITICAL</span><span class="risk-count" id="risk-critical-count">47</span></div>
      <div class="risk-item risk-high" onclick="showEntityDetail('high')"><span>HIGH</span><span class="risk-count" id="risk-high-count">312</span></div>
      <div class="risk-item risk-medium" onclick="showEntityDetail('medium')"><span>MEDIUM</span><span class="risk-count" id="risk-medium-count">891</span></div>
      <div class="risk-item risk-low" onclick="showEntityDetail('low')"><span>LOW</span><span class="risk-count" id="risk-low-count">1,597</span></div>
    </div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#128293; Patent Family Heat Map</div>
      <div class="panel-value" id="patent-total">12,456</div>
    </div>
    <div class="panel-sub">Patent families across 194 jurisdictions</div>
    <div class="heat-bar">
      <div class="heat-segment" style="background:#c41e3a;flex:3.5" title="USPTO: 4,360">US</div>
      <div class="heat-segment" style="background:#ff5722;flex:2.8" title="EPO: 3,488">EU</div>
      <div class="heat-segment" style="background:#ff9800;flex:2.2" title="CNIPA: 2,740">CN</div>
      <div class="heat-segment" style="background:#ffc107;flex:1.2" title="JPO: 1,494">JP</div>
      <div class="heat-segment" style="background:#d4af37;flex:0.8" title="KIPO: 996">KR</div>
      <div class="heat-segment" style="background:#795548;flex:1.5" title="Other: 1,378">OTH</div>
    </div>
    <div class="macro-grid" style="margin-top:0.4rem">
      <div class="macro-cell"><div class="macro-label">Active Patents</div><div class="macro-value" id="active-patents">8,234</div></div>
      <div class="macro-cell"><div class="macro-label">Pending</div><div class="macro-value" id="pending-patents">2,187</div></div>
      <div class="macro-cell"><div class="macro-label">Expired</div><div class="macro-value" id="expired-patents">1,612</div></div>
      <div class="macro-cell"><div class="macro-label">Disputed</div><div class="macro-value" style="color:var(--red)" id="disputed-patents">423</div></div>
    </div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#9939; Blockchain Transaction Flow</div>
      <div class="panel-value" style="font-size:1.1rem" id="blockchain-tx">2.4M TX</div>
    </div>
    <div class="panel-sub">Real-time chain analysis across 14 blockchains</div>
    <div class="flow-container">
      <div class="flow-node wallet">Wallet A<br><small>$42M</small></div>
      <div class="flow-arrow">&#8594;</div>
      <div class="flow-node mixer">Mixer<br><small>Tornado</small></div>
      <div class="flow-arrow">&#8594;</div>
      <div class="flow-node exchange">CEX<br><small>Binance</small></div>
      <div class="flow-arrow">&#8594;</div>
      <div class="flow-node wallet">Wallet B<br><small>$38M</small></div>
      <div class="flow-arrow">&#8594;</div>
      <div class="flow-node mixer">Bridge<br><small>Polygon</small></div>
      <div class="flow-arrow">&#8594;</div>
      <div class="flow-node exchange">DEX<br><small>Uniswap</small></div>
    </div>
    <div class="macro-grid" style="margin-top:0.4rem">
      <div class="macro-cell"><div class="macro-label">Traced</div><div class="macro-value" style="color:#4caf50">$1.2B</div></div>
      <div class="macro-cell"><div class="macro-label">Frozen</div><div class="macro-value" style="color:var(--red)">$340M</div></div>
      <div class="macro-cell"><div class="macro-label">Wallets</div><div class="macro-value">14,392</div></div>
      <div class="macro-cell"><div class="macro-label">Risk Score</div><div class="macro-value" style="color:#ff9800">87/100</div></div>
    </div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#128202; Financial Contagion Gauge</div>
      <div class="panel-value" style="font-size:1.1rem;color:var(--red)" id="contagion-score">CRITICAL</div>
    </div>
    <div class="panel-sub">Systemic risk assessment across counterparties</div>
    <div class="gauge-wrapper">
      <svg class="gauge-svg" viewBox="0 0 140 75">
        <defs><linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" style="stop-color:#4caf50"/><stop offset="50%" style="stop-color:#ff9800"/><stop offset="100%" style="stop-color:#c41e3a"/></linearGradient></defs>
        <path d="M 10 70 A 60 60 0 0 1 130 70" fill="none" stroke="url(#gaugeGrad)" stroke-width="10" stroke-linecap="round"/>
        <line id="gauge-needle" x1="70" y1="70" x2="130" y2="70" stroke="var(--gold)" stroke-width="2" stroke-linecap="round" transform="rotate(-90 70 70)"/>
        <circle cx="70" cy="70" r="4" fill="var(--gold)"/>
        <text x="70" y="68" text-anchor="middle" fill="var(--text-dim)" font-size="7" font-family="monospace">RISK</text>
      </svg>
      <div class="gauge-value" id="gauge-val">92%</div>
      <div class="gauge-label">Contagion Probability</div>
    </div>
    <div class="macro-grid" style="margin-top:0.4rem">
      <div class="macro-cell"><div class="macro-label">Exposed Banks</div><div class="macro-value" style="color:var(--red)">47</div></div>
      <div class="macro-cell"><div class="macro-label">Hedge Funds</div><div class="macro-value" style="color:#ff9800">23</div></div>
      <div class="macro-cell"><div class="macro-label">Insurers</div><div class="macro-value">12</div></div>
      <div class="macro-cell"><div class="macro-label">Pension Funds</div><div class="macro-value" style="color:#4caf50">8</div></div>
    </div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#128376; Shell Corporation Network</div>
      <div class="panel-value" style="font-size:1.1rem" id="shell-count">1,847</div>
    </div>
    <div class="panel-sub">Force-directed network graph — drag to explore</div>
    <canvas class="network-canvas" id="network-canvas"></canvas>
    <div class="macro-grid" style="margin-top:0.4rem">
      <div class="macro-cell"><div class="macro-label">Offshore</div><div class="macro-value">632</div></div>
      <div class="macro-cell"><div class="macro-label">Onshore</div><div class="macro-value">815</div></div>
      <div class="macro-cell"><div class="macro-label">Hybrid</div><div class="macro-value" style="color:#ff9800">312</div></div>
      <div class="macro-cell"><div class="macro-label">Confirmed</div><div class="macro-value" style="color:var(--red)">88</div></div>
    </div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#127917; Synthetic Identity Detections</div>
      <div class="panel-value" style="font-size:1.1rem;color:var(--red)" id="synth-label">ACTIVE</div>
    </div>
    <div class="panel-sub">AI-generated identities flagged across databases</div>
    <div class="odometer">
      <div class="odigit" id="o1">0</div><div class="odigit" id="o2">0</div><div class="odigit" id="o3">4</div>
      <div class="odigit" id="o4">7</div><div class="odigit" id="o5">2</div><div class="odigit" id="o6">9</div><div class="odigit" id="o7">1</div>
    </div>
    <div class="macro-grid" style="margin-top:0.6rem">
      <div class="macro-cell"><div class="macro-label">SSN Clones</div><div class="macro-value" style="color:var(--red)">1,234</div></div>
      <div class="macro-cell"><div class="macro-label">Deepfakes</div><div class="macro-value" style="color:#ff9800">892</div></div>
      <div class="macro-cell"><div class="macro-label">Doc Forgery</div><div class="macro-value">1,847</div></div>
      <div class="macro-cell"><div class="macro-label">Biometric</div><div class="macro-value" style="color:#4caf50">698</div></div>
    </div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#9889; GENIUS Act Payload Status</div>
      <div class="panel-value" style="font-size:1.1rem;color:#4caf50" id="genius-status">ARMED</div>
    </div>
    <div class="panel-sub">Treasury seizure payload readiness</div>
    <div class="status-list">
      <div class="status-row"><div class="status-dot dot-ready"></div><span>OFAC Authority</span><span style="margin-left:auto;font-family:monospace;font-size:0.65rem;color:#4caf50">READY</span></div>
      <div class="status-row"><div class="status-dot dot-ready"></div><span>Judicial Warrant</span><span style="margin-left:auto;font-family:monospace;font-size:0.65rem;color:#4caf50">ISSUED</span></div>
      <div class="status-row"><div class="status-dot dot-ready"></div><span>International Coordination</span><span style="margin-left:auto;font-family:monospace;font-size:0.65rem;color:#4caf50">ACTIVE</span></div>
      <div class="status-row"><div class="status-dot dot-pending"></div><span>Swiss FINMA Request</span><span style="margin-left:auto;font-family:monospace;font-size:0.65rem;color:#ff9800">PENDING</span></div>
      <div class="status-row"><div class="status-dot dot-ready"></div><span>Cayman Court Order</span><span style="margin-left:auto;font-family:monospace;font-size:0.65rem;color:#4caf50">EXECUTED</span></div>
      <div class="status-row"><div class="status-dot dot-blocked"></div><span>Crypto Exchange Freeze</span><span style="margin-left:auto;font-family:monospace;font-size:0.65rem;color:var(--red)">PARTIAL</span></div>
    </div>
    <div style="margin-top:0.6rem;padding:0.5rem;border-radius:8px;background:rgba(212,175,55,0.05);border:1px solid var(--border-gold);font-size:0.7rem;text-align:center">
      <strong style="color:var(--gold)">Payload Value:</strong> <span style="font-family:monospace;font-size:0.9rem;color:var(--white)">$2.47B</span> across <strong>14</strong> jurisdictions
    </div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#128203; SEC Filing Alert Feed</div>
      <div class="panel-value" style="font-size:1.1rem" id="sec-count">23</div>
    </div>
    <div class="panel-sub">Material filings and irregularities detected</div>
    <div class="alert-feed">
      <div class="alert-item sev-1"><span class="alert-time">14:32</span><span><strong>8-K</strong> Irrelated-party transaction — Entity #4821</span></div>
      <div class="alert-item sev-1"><span class="alert-time">13:58</span><span><strong>10-Q</strong> Restatement: $47M discrepancy</span></div>
      <div class="alert-item sev-2"><span class="alert-time">12:15</span><span><strong>13D</strong> Ownership change above 5%</span></div>
      <div class="alert-item sev-2"><span class="alert-time">11:42</span><span><strong>4</strong> Insider sale cluster — 3 executives</span></div>
      <div class="alert-item sev-1"><span class="alert-time">09:45</span><span><strong>SD</strong> AML violation flag</span></div>
      <div class="alert-item"><span class="alert-time">08:30</span><span><strong>10-K</strong> Delayed filing — 3rd extension</span></div>
    </div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#127757; Macro Indicator Dashboard</div>
      <div class="panel-value" style="font-size:1.1rem" id="macro-score">ALERT</div>
    </div>
    <div class="panel-sub">IMF / World Bank composite indicators</div>
    <div class="macro-grid">
      <div class="macro-cell"><div class="macro-label">US GDP Growth</div><div class="macro-value" style="color:#4caf50" id="gdp-us">+2.1%</div></div>
      <div class="macro-cell"><div class="macro-label">EU GDP Growth</div><div class="macro-value" style="color:#ff9800" id="gdp-eu">+0.8%</div></div>
      <div class="macro-cell"><div class="macro-label">CN GDP Growth</div><div class="macro-value" id="gdp-cn">+4.8%</div></div>
      <div class="macro-cell"><div class="macro-label">Global Inflation</div><div class="macro-value" style="color:var(--red)" id="inflation">4.2%</div></div>
      <div class="macro-cell"><div class="macro-label">US Debt/GDP</div><div class="macro-value" style="color:var(--red)" id="debt-us">123%</div></div>
      <div class="macro-cell"><div class="macro-label">Fed Funds</div><div class="macro-value" id="fed-rate">5.50%</div></div>
      <div class="macro-cell"><div class="macro-label">Unemployment</div><div class="macro-value" style="color:#4caf50" id="unemployment">3.7%</div></div>
      <div class="macro-cell"><div class="macro-label">S&P 500</div><div class="macro-value" id="sp500">4,847</div></div>
    </div>
    <div style="margin-top:0.5rem;font-size:0.6rem;color:var(--text-dim);text-align:center">Data: IMF WEO Oct 2025, World Bank, Federal Reserve</div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <div class="panel-title">&#8383; Crypto Market Ticker</div>
      <div class="panel-value" style="font-size:1.1rem" id="crypto-mcap">$1.84T</div>
    </div>
    <div class="panel-sub">Live market data across major assets</div>
    <div class="ticker-wrap">
      <div class="ticker">
        <span class="ticker-item"><strong>BTC</strong> $67,432 <span class="up">+2.4%</span></span>
        <span class="ticker-item"><strong>ETH</strong> $3,847 <span class="up">+1.8%</span></span>
        <span class="ticker-item"><strong>BNB</strong> $432 <span class="down">-0.6%</span></span>
        <span class="ticker-item"><strong>SOL</strong> $148 <span class="up">+5.2%</span></span>
        <span class="ticker-item"><strong>XRP</strong> $0.62 <span class="down">-1.2%</span></span>
        <span class="ticker-item"><strong>ADA</strong> $0.58 <span class="up">+0.9%</span></span>
        <span class="ticker-item"><strong>AVAX</strong> $38.4 <span class="up">+3.1%</span></span>
        <span class="ticker-item"><strong>DOT</strong> $7.82 <span class="down">-0.3%</span></span>
        <span class="ticker-item"><strong>LINK</strong> $14.7 <span class="up">+2.8%</span></span>
        <span class="ticker-item"><strong>MATIC</strong> $0.72 <span class="down">-0.8%</span></span>
        <span class="ticker-item"><strong>BTC</strong> $67,432 <span class="up">+2.4%</span></span>
        <span class="ticker-item"><strong>ETH</strong> $3,847 <span class="up">+1.8%</span></span>
        <span class="ticker-item"><strong>BNB</strong> $432 <span class="down">-0.6%</span></span>
        <span class="ticker-item"><strong>SOL</strong> $148 <span class="up">+5.2%</span></span>
        <span class="ticker-item"><strong>XRP</strong> $0.62 <span class="down">-1.2%</span></span>
        <span class="ticker-item"><strong>ADA</strong> $0.58 <span class="up">+0.9%</span></span>
        <span class="ticker-item"><strong>AVAX</strong> $38.4 <span class="up">+3.1%</span></span>
        <span class="ticker-item"><strong>DOT</strong> $7.82 <span class="down">-0.3%</span></span>
        <span class="ticker-item"><strong>LINK</strong> $14.7 <span class="up">+2.8%</span></span>
        <span class="ticker-item"><strong>MATIC</strong> $0.72 <span class="down">-0.8%</span></span>
      </div>
    </div>
    <div class="macro-grid" style="margin-top:0.4rem">
      <div class="macro-cell"><div class="macro-label">24h Volume</div><div class="macro-value">$87.4B</div></div>
      <div class="macro-cell"><div class="macro-label">BTC Dominance</div><div class="macro-value">52.3%</div></div>
      <div class="macro-cell"><div class="macro-label">Fear & Greed</div><div class="macro-value" style="color:#ff9800">72</div></div>
      <div class="macro-cell"><div class="macro-label">Liquidations</div><div class="macro-value" style="color:var(--red)">$142M</div></div>
    </div>
  </div>
  <div class="panel" style="grid-column:1/-1">
    <div class="panel-header">
      <div class="panel-title">&#128240; Intelligence Feed</div>
      <div class="panel-value" style="font-size:0.9rem;color:var(--text-dim)">Live</div>
    </div>
    <div class="news-ticker">
      <div class="news-item"><div class="news-dot"></div><div><strong style="color:var(--gold)">BREAKING:</strong> Swiss authorities freeze 14 accounts linked to Panamanian shell network — $280M secured</div></div>
      <div class="news-item"><div class="news-dot"></div><div><strong style="color:var(--gold)">UPDATE:</strong> DOJ unseals indictment against 7 individuals in Operation Paper Trail — RICO charges filed</div></div>
      <div class="news-item"><div class="news-dot"></div><div><strong style="color:var(--gold)">ALERT:</strong> Chainalysis traces 4,892 BTC through mixing services to CEX deposit addresses</div></div>
      <div class="news-item"><div class="news-dot"></div><div><strong style="color:var(--gold)">PATENT:</strong> USPTO confirms priority date dispute across 47 patent families — IPR initiated</div></div>
      <div class="news-item"><div class="news-dot"></div><div><strong style="color:var(--gold)">FOREX:</strong> Treasury sanctions 3 BVI entities under GENIUS Act — assets blocked</div></div>
    </div>
  </div>
</div>
<div id="modal-overlay" onclick="if(event.target===this)this.classList.remove('active')"><div class="modal-content" onclick="event.stopPropagation()">
  <button class="modal-close" onclick="document.getElementById('modal-overlay').classList.remove('active')">&times;</button>
  <div class="modal-title" id="modal-title">Entity Detail</div>
  <div class="modal-body" id="modal-body"></div>
</div></div>
<div id="confirm-dialog">
  <div class="confirm-box">
    <div class="confirm-title">&#9888; CONFIRM SEIZURE</div>
    <div class="confirm-text">Initiate <strong>GENIUS Act seizure payload</strong> across <strong>14 jurisdictions</strong> targeting <strong>$2.47 billion</strong>.<br><br>This action is <strong style="color:var(--red)">IRREVERSIBLE</strong>.</div>
    <div class="confirm-buttons">
      <button class="confirm-btn confirm-yes" onclick="confirmSeizure()">CONFIRM</button>
      <button class="confirm-btn confirm-no" onclick="document.getElementById('confirm-dialog').classList.remove('active')">CANCEL</button>
    </div>
  </div>
</div>
<div id="toast-container"></div>
<script>
(function(){
'use strict';
const REFRESH_INTERVAL = {refresh_interval};
let audioCtx = null;

function initStarfield() {
  const canvas = document.getElementById('starfield');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let stars = [];
  let shootingStars = [];
  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    stars = [];
    for (let i = 0; i < 250; i++) {
      stars.push({x: Math.random() * canvas.width, y: Math.random() * canvas.height,
        r: Math.random() * 1.5 + 0.3, alpha: Math.random(),
        speed: Math.random() * 0.02 + 0.005, twinkle: Math.random() * Math.PI * 2});
    }
  }
  resize(); window.addEventListener('resize', resize);
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const time = Date.now() * 0.001;
    for (const s of stars) {
      const a = 0.3 + 0.7 * Math.abs(Math.sin(time * s.speed + s.twinkle));
      ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${a})`; ctx.fill();
    }
    if (Math.random() < 0.012) {
      shootingStars.push({x: Math.random() * canvas.width * 0.5, y: Math.random() * canvas.height * 0.4,
        vx: Math.random() * 300 + 200, vy: Math.random() * 150 + 80, life: 1, decay: Math.random() * 0.5 + 0.5});
    }
    for (let i = shootingStars.length - 1; i >= 0; i--) {
      const ss = shootingStars[i];
      ss.x += ss.vx * 0.016; ss.y += ss.vy * 0.016; ss.life -= ss.decay * 0.016;
      if (ss.life <= 0) { shootingStars.splice(i, 1); continue; }
      const grad = ctx.createLinearGradient(ss.x, ss.y, ss.x - ss.vx * 0.08, ss.y - ss.vy * 0.08);
      grad.addColorStop(0, `rgba(255,255,255,${ss.life})`); grad.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.beginPath(); ctx.moveTo(ss.x, ss.y); ctx.lineTo(ss.x - ss.vx * 0.08, ss.y - ss.vy * 0.08);
      ctx.strokeStyle = grad; ctx.lineWidth = 1.5; ctx.stroke();
    }
    requestAnimationFrame(draw);
  }
  draw();
}

function initNetworkGraph() {
  const canvas = document.getElementById('network-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  function resize() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr; canvas.height = rect.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize(); window.addEventListener('resize', resize);
  const nodeCount = 40;
  const nodes = [];
  for (let i = 0; i < nodeCount; i++) {
    nodes.push({id: i, x: Math.random() * canvas.width / dpr, y: Math.random() * canvas.height / dpr,
      vx: 0, vy: 0, r: i < 5 ? 8 : (i < 15 ? 5 : 3),
      type: i < 3 ? 'root' : (i < 10 ? 'shell' : (i < 20 ? 'bank' : 'individual')), label: i < 3 ? 'HUB'+(i+1) : ('N'+i)});
  }
  const links = [];
  for (let i = 0; i < nodeCount; i++) {
    const lc = Math.floor(Math.random() * 3) + 1;
    for (let j = 0; j < lc; j++) { const t = Math.floor(Math.random() * nodeCount); if (t !== i) links.push({source: i, target: t}); }
  }
  let draggedNode = null;
  function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX !== undefined ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
    const cy = e.clientY !== undefined ? e.clientY : (e.touches && e.touches[0] ? e.touches[0].clientY : 0);
    return {x: cx - rect.left, y: cy - rect.top};
  }
  function onDown(e) { const p = getMousePos(e); for (const n of nodes) { const dx = p.x - n.x, dy = p.y - n.y; if (dx*dx + dy*dy < (n.r + 8)**2) draggedNode = n; } }
  function onMove(e) { if (!draggedNode) return; const p = getMousePos(e); draggedNode.x = p.x; draggedNode.y = p.y; e.preventDefault && e.preventDefault(); }
  function onUp() { draggedNode = null; }
  canvas.addEventListener('mousedown', onDown);
  canvas.addEventListener('mousemove', onMove);
  canvas.addEventListener('mouseup', onUp);
  canvas.addEventListener('touchstart', onDown, {passive: false});
  canvas.addEventListener('touchmove', onMove, {passive: false});
  canvas.addEventListener('touchend', onUp);

  function simulate() {
    const w = canvas.width / dpr, h = canvas.height / dpr;
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[j].x - nodes[i].x, dy = nodes[j].y - nodes[i].y;
        const dist = Math.sqrt(dx*dx + dy*dy) || 1;
        const force = 2000 / (dist * dist);
        const fx = (dx / dist) * force, fy = (dy / dist) * force;
        if (nodes[i] !== draggedNode) { nodes[i].vx -= fx; nodes[i].vy -= fy; }
        if (nodes[j] !== draggedNode) { nodes[j].vx += fx; nodes[j].vy += fy; }
      }
    }
    for (const l of links) {
      const a = nodes[l.source], b = nodes[l.target];
      const dx = b.x - a.x, dy = b.y - a.y;
      const dist = Math.sqrt(dx*dx + dy*dy) || 1;
      const force = (dist - 60) * 0.001;
      const fx = (dx / dist) * force, fy = (dy / dist) * force;
      if (a !== draggedNode) { a.vx += fx; a.vy += fy; }
      if (b !== draggedNode) { b.vx -= fx; b.vy -= fy; }
    }
    for (const n of nodes) {
      if (n === draggedNode) continue;
      n.vx += (w/2 - n.x) * 0.0003; n.vy += (h/2 - n.y) * 0.0003;
      n.vx *= 0.92; n.vy *= 0.92;
      n.x += n.vx; n.y += n.vy;
      n.x = Math.max(n.r, Math.min(w - n.r, n.x));
      n.y = Math.max(n.r, Math.min(h - n.r, n.y));
    }
  }
  function draw() {
    const w = canvas.width / dpr, h = canvas.height / dpr;
    ctx.clearRect(0, 0, w, h);
    for (const l of links) {
      const a = nodes[l.source], b = nodes[l.target];
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = 'rgba(212,175,55,0.12)'; ctx.lineWidth = 1; ctx.stroke();
    }
    for (const n of nodes) {
      ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      const colors = {root: '#c41e3a', shell: '#ff9800', bank: '#4a90d9', individual: '#7a8ab0'};
      ctx.fillStyle = colors[n.type] || '#7a8ab0'; ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.25)'; ctx.lineWidth = 1; ctx.stroke();
      if (n.r > 4) { ctx.fillStyle = '#e0e6f0'; ctx.font = '9px monospace'; ctx.textAlign = 'center'; ctx.fillText(n.label, n.x, n.y + n.r + 10); }
    }
    simulate(); requestAnimationFrame(draw);
  }
  draw();
}

function animateOdometer() {
  const target = 47291;
  const digits = document.querySelectorAll('.odigit');
  let current = 0;
  const step = Math.ceil(target / 120);
  function update() {
    current = Math.min(current + step, target);
    const s = String(current).padStart(7, '0');
    digits.forEach((d, i) => d.textContent = s[i] || '0');
    if (current < target) requestAnimationFrame(update);
  }
  setTimeout(update, 2000);
}

function updateGauge() {
  const needle = document.getElementById('gauge-needle');
  if (!needle) return;
  setInterval(() => {
    const angle = -90 + Math.random() * 140;
    needle.setAttribute('transform', `rotate(${angle} 70 70)`);
    const pct = Math.round((angle + 90) / 180 * 100);
    document.getElementById('gauge-val').textContent = pct + '%';
    const score = document.getElementById('contagion-score');
    if (pct > 80) { score.textContent = 'CRITICAL'; score.style.color = 'var(--red)'; }
    else if (pct > 60) { score.textContent = 'ELEVATED'; score.style.color = '#ff9800'; }
    else { score.textContent = 'MODERATE'; score.style.color = '#4caf50'; }
  }, 5000);
}

function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent = now.toUTCString().slice(17, 25) + ' UTC';
}

function simulateLiveData() {
  const rc = 47 + Math.floor(Math.random() * 8 - 4);
  const rh = 312 + Math.floor(Math.random() * 20 - 10);
  document.getElementById('risk-critical-count').textContent = rc;
  document.getElementById('risk-high-count').textContent = rh;
  document.getElementById('risk-total').textContent = (rc + rh + 891 + 1597).toLocaleString();
  const sp = 4847 + Math.floor(Math.random() * 40 - 20);
  document.getElementById('sp500').textContent = sp.toLocaleString();
  const synth = 47291 + Math.floor(Math.random() * 20 - 5);
  const s = String(synth).padStart(7, '0');
  document.querySelectorAll('.odigit').forEach((d, i) => d.textContent = s[i]);
}

function runIntro() {
  initStarfield(); initNetworkGraph(); updateGauge(); animateOdometer(); updateClock();
  setTimeout(() => {
    document.getElementById('intro-overlay').classList.add('hidden');
    document.getElementById('dashboard').classList.add('visible');
    setInterval(simulateLiveData, REFRESH_INTERVAL);
    showToast('Dashboard activated — all systems nominal', 'success');
  }, 4500);
}

window.toggleTheme = function() {
  document.body.classList.toggle('light-mode');
  showToast(document.body.classList.contains('light-mode') ? 'Light mode enabled' : 'Dark mode enabled', 'info');
};

window.lockTargets = function() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
  osc.frequency.value = 800; osc.type = 'square';
  gain.gain.value = 0.1;
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);
  osc.connect(gain); gain.connect(audioCtx.destination);
  osc.start(); osc.stop(audioCtx.currentTime + 0.3);
  showToast('Targets locked — tracking engaged', 'info');
};

window.fireSeizurePayload = function() { document.getElementById('confirm-dialog').classList.add('active'); };

window.confirmSeizure = function() {
  document.getElementById('confirm-dialog').classList.remove('active');
  document.getElementById('genius-status').textContent = 'FIRED';
  document.getElementById('genius-status').style.color = 'var(--red)';
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  for (let i = 0; i < 3; i++) {
    const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
    osc.frequency.value = 1200; osc.type = 'sawtooth'; gain.gain.value = 0.08;
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15 + i * 0.2);
    osc.connect(gain); gain.connect(audioCtx.destination);
    osc.start(audioCtx.currentTime + i * 0.15); osc.stop(audioCtx.currentTime + 0.15 + i * 0.2);
  }
  showToast('GENIUS Act seizure payload FIRED — $2.47B across 14 jurisdictions', 'error');
};

const entityData = {
  critical: '<h3 style="color:#ff6b6b">CRITICAL Risk Entities (47)</h3><p>Entities flagged for immediate GENIUS Act action. Cross-referenced with OFAC SDN, Interpol Red Notices, FinCEN 314(a).</p><ul><li>ShellCo BVI-2847 — $420M exposure</li><li>TrustNet Cayman-892 — $310M</li><li>GlobalHoldings Panama-441 — $280M</li></ul>',
  high: '<h3 style="color:#ff9800">HIGH Risk Entities (312)</h3><ul><li>94 shell corporations with circular ownership</li><li>78 crypto wallets linked to mixing</li><li>67 individuals with cross-border litigation</li><li>48 patent trolls with NPE history</li><li>25 banks with AML gaps</li></ul>',
  medium: '<h3 style="color:#ffeb3b">MEDIUM Risk Entities (891)</h3><p>Standard monitoring regime. Quarterly review.</p><ul><li>342 dormant companies with asset movement</li><li>289 IP holding companies with licensing irregularities</li></ul>',
  low: '<h3 style="color:#4caf50">LOW Risk Entities (1,597)</h3><p>Minimal risk profile. Annual review cycle.</p>'
};
window.showEntityDetail = function(level) {
  document.getElementById('modal-title').textContent = level.toUpperCase() + ' Risk Entities';
  document.getElementById('modal-body').innerHTML = entityData[level] || 'No data.';
  document.getElementById('modal-overlay').classList.add('active');
};

window.exportReport = function(format) {
  const data = {timestamp: new Date().toISOString(), platform: 'ARGUS-PANTHER ULTIMA', version: '2026.1.0',
    entities: {critical: 47, high: 312, medium: 891, low: 1597},
    patents: {total: 12456, active: 8234, disputed: 423},
    blockchain: {transactions_traced: '2.4M', value_traced_usd: '$1.2B', value_frozen: '$340M'},
    macro: {us_gdp: '+2.1%', eu_gdp: '+0.8%', cn_gdp: '+4.8%', inflation: '4.2%', sp500: 4847},
    seizure_payload: {status: 'ARMED', value_usd: '$2.47B', jurisdictions: 14}};
  if (format === 'json') {
    const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
    const url = URL.createObjectURL(blob); const a = document.createElement('a');
    a.href = url; a.download = `argus-report-${new Date().toISOString().slice(0,10)}.json`; a.click(); URL.revokeObjectURL(url);
    showToast('JSON report exported', 'success');
  } else {
    const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>ARGUS Report</title><style>body{font-family:Arial,sans-serif;padding:40px;color:#1a2a6a}h1{color:#d4af37}h2{color:#1a2a6a;border-bottom:2px solid #d4af37;padding-bottom:5px}table{border-collapse:collapse;width:100%;margin:15px 0}th,td{border:1px solid #ccc;padding:8px;text-align:left}th{background:#1a2a6a;color:#fff}</style></head><body><h1>ARGUS-PANTHER ULTIMA Forensic Report</h1><p><strong>Generated:</strong> ${new Date().toUTCString()}</p><h2>Risk Matrix</h2><table><tr><th>Level</th><th>Count</th></tr><tr><td>CRITICAL</td><td>47</td></tr><tr><td>HIGH</td><td>312</td></tr><tr><td>MEDIUM</td><td>891</td></tr><tr><td>LOW</td><td>1,597</td></tr></table><h2>Patent Analysis</h2><table><tr><th>Category</th><th>Count</th></tr><tr><td>Total Families</td><td>12,456</td></tr><tr><td>Active</td><td>8,234</td></tr><tr><td>Disputed</td><td>423</td></tr></table><h2>Blockchain Tracing</h2><table><tr><th>Metric</th><th>Value</th></tr><tr><td>Transactions</td><td>2.4M</td></tr><tr><td>Value Traced</td><td>$1.2B</td></tr><tr><td>Value Frozen</td><td>$340M</td></tr></table><h2>Seizure Payload</h2><p><strong>Status:</strong> ARMED | <strong>Value:</strong> $2.47B | <strong>Jurisdictions:</strong> 14</p><p style="margin-top:40px;font-size:0.8rem;color:#666">Generated automatically by ARGUS-PANTHER ULTIMA. CONFIDENTIAL.</p></body></html>`;
    const blob = new Blob([html], {type:'text/html'});
    const url = URL.createObjectURL(blob); const a = document.createElement('a');
    a.href = url; a.download = `argus-report-${new Date().toISOString().slice(0,10)}.html`; a.click(); URL.revokeObjectURL(url);
    showToast('Report exported (HTML)', 'success');
  }
};

function showToast(message, type) {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`; toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => { toast.classList.add('fade-out'); setTimeout(() => toast.remove(), 300); }, 4000);
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { document.getElementById('modal-overlay').classList.remove('active'); document.getElementById('confirm-dialog').classList.remove('active'); }
  if (e.key === 'l' || e.key === 'L') lockTargets();
  if (e.key === 't' || e.key === 'T') toggleTheme();
});

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', runIntro);
else runIntro();
})();
</script>
</body>
</html>
"""
