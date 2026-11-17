"""Pastel look for the UI, with matching light and dark modes.

Pastels are used for backgrounds, badges and buttons. Text on them stays dark (light mode)
or light (dark mode) so it keeps enough contrast to read.
"""
import gradio as gr

# Light: warm off-white with powder blue, sage and sand. Dark: deep slate with the same pastels as accents.
LIGHT = {
    "bg": "#f6f8f6", "surface": "#ffffff", "subtle": "#ecf3f2", "border": "#dfe7e4",
    "text": "#1c2b2d", "muted": "#5a6a6b", "accent": "#2b7a78",
}
DARK = {
    "bg": "#101517", "surface": "#182023", "subtle": "#212a2e", "border": "#2e3a3f",
    "text": "#ecf3f2", "muted": "#a8b7b6", "accent": "#a7d3e8",
}
BUTTON_GRADIENT = "linear-gradient(120deg, #a7d3e8 0%, #b8e0cb 55%, #e6dcbc 100%)"
BUTTON_GRADIENT_HOVER = "linear-gradient(120deg, #93c7e0 0%, #a5d6bc 55%, #ddd0a8 100%)"

theme = gr.themes.Base(
    primary_hue="sky",
    secondary_hue="emerald",
    neutral_hue="slate",
    radius_size="lg",
    font=[gr.themes.GoogleFont("Plus Jakarta Sans"), gr.themes.GoogleFont("Space Grotesk"), "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
).set(
    body_background_fill=LIGHT["bg"],
    body_background_fill_dark=DARK["bg"],
    body_text_color=LIGHT["text"],
    body_text_color_dark=DARK["text"],
    body_text_color_subdued=LIGHT["muted"],
    body_text_color_subdued_dark=DARK["muted"],
    background_fill_primary=LIGHT["surface"],
    background_fill_primary_dark=DARK["surface"],
    background_fill_secondary=LIGHT["subtle"],
    background_fill_secondary_dark=DARK["subtle"],
    border_color_primary=LIGHT["border"],
    border_color_primary_dark=DARK["border"],
    color_accent=LIGHT["accent"],
    color_accent_soft="#ddeef5",
    color_accent_soft_dark="#1f3440",
    link_text_color=LIGHT["accent"],
    link_text_color_dark=DARK["accent"],
    block_background_fill=LIGHT["surface"],
    block_background_fill_dark=DARK["surface"],
    block_border_color=LIGHT["border"],
    block_border_color_dark=DARK["border"],
    block_radius="20px",
    block_shadow="0 6px 24px -12px rgba(30, 70, 80, 0.16)",
    block_shadow_dark="0 6px 24px -12px rgba(0, 0, 0, 0.6)",
    block_label_text_color=LIGHT["muted"],
    block_label_text_color_dark=DARK["muted"],
    block_title_text_color=LIGHT["text"],
    block_title_text_color_dark=DARK["text"],
    input_background_fill=LIGHT["surface"],
    input_background_fill_dark=DARK["subtle"],
    input_border_color=LIGHT["border"],
    input_border_color_dark=DARK["border"],
    input_border_color_focus="#7fb8d4",
    input_border_color_focus_dark="#a7d3e8",
    input_shadow_focus="0 0 0 4px rgba(127, 184, 212, 0.4)",
    input_shadow_focus_dark="0 0 0 4px rgba(127, 184, 212, 0.25)",
    input_radius="14px",
    input_placeholder_color="#95a5a6",
    input_placeholder_color_dark="#6f8082",
    button_large_radius="999px",
    button_medium_radius="999px",
    button_small_radius="999px",
    button_primary_background_fill=BUTTON_GRADIENT,
    button_primary_background_fill_dark=BUTTON_GRADIENT,
    button_primary_background_fill_hover=BUTTON_GRADIENT_HOVER,
    button_primary_background_fill_hover_dark=BUTTON_GRADIENT_HOVER,
    button_primary_text_color="#1c2b2d",
    button_primary_text_color_dark="#13201f",
    button_primary_border_color="transparent",
    button_primary_border_color_dark="transparent",
    button_primary_shadow="0 8px 20px -8px rgba(80, 150, 170, 0.45)",
    button_secondary_background_fill=LIGHT["subtle"],
    button_secondary_background_fill_dark=DARK["subtle"],
    button_secondary_background_fill_hover="#e3ece9",
    button_secondary_background_fill_hover_dark="#28333a",
    button_secondary_text_color=LIGHT["text"],
    button_secondary_text_color_dark=DARK["text"],
    button_secondary_border_color=LIGHT["border"],
    button_secondary_border_color_dark=DARK["border"],
    button_transform_hover="translateY(-1px)",
    loader_color="#a7d3e8",
    code_background_fill=LIGHT["subtle"],
    code_background_fill_dark="#0d1214",
)

# Switches light and dark mode and remembers the choice in this browser
TOGGLE_THEME = """() => {
  const dark = document.body.classList.toggle('dark');
  try { localStorage.setItem('cs-theme', dark ? 'dark' : 'light'); } catch (e) {}
}"""

# Applies the saved choice when the page opens; without one, Gradio follows the system setting
RESTORE_THEME = """() => {
  let saved = null;
  try { saved = localStorage.getItem('cs-theme'); } catch (e) {}
  if (saved) document.body.classList.toggle('dark', saved === 'dark');
}"""

custom_css = """
:root, .light {
  --cs-surface: #ffffff; --cs-subtle: #ecf3f2; --cs-border: #dfe7e4;
  --cs-text: #1c2b2d; --cs-muted: #5a6a6b; --cs-accent: #2b7a78;
  --cs-glass: rgba(255, 255, 255, 0.72);
  --cs-title: linear-gradient(100deg, #1f6f9c 0%, #2b7a78 50%, #4f7f35 100%);
  --cs-blue: #ddeef5; --cs-blue-ink: #1f5a80;
  --cs-clay: #f5e3da; --cs-clay-ink: #8f3d22;
  --cs-mint: #dcefe3; --cs-mint-ink: #2c6b45;
  --cs-sand: #f2ead6; --cs-sand-ink: #77591d;
  --cs-sky: #e0eef0; --cs-sky-ink: #2a6266;
  --cs-mist: #e8ecec; --cs-mist-ink: #4d5a5c;
  --cs-mesh: radial-gradient(at 8% 0%, #e3f0f7 0, transparent 45%),
             radial-gradient(at 95% 5%, #e6f2e8 0, transparent 40%),
             radial-gradient(at 90% 95%, #f1ecdc 0, transparent 45%),
             radial-gradient(at 5% 90%, #e2f1f0 0, transparent 40%);
}
.dark {
  --cs-surface: #182023; --cs-subtle: #212a2e; --cs-border: #2e3a3f;
  --cs-text: #ecf3f2; --cs-muted: #a8b7b6; --cs-accent: #a7d3e8;
  --cs-glass: rgba(24, 32, 35, 0.72);
  --cs-title: linear-gradient(100deg, #a7d3e8 0%, #9ed8d0 50%, #c9e4b4 100%);
  --cs-blue: #1b3346; --cs-blue-ink: #bfe0f5;
  --cs-clay: #3b2620; --cs-clay-ink: #f2c3ad;
  --cs-mint: #1b3628; --cs-mint-ink: #b9e6c9;
  --cs-sand: #383020; --cs-sand-ink: #ecdcae;
  --cs-sky: #193536; --cs-sky-ink: #a9e0da;
  --cs-mist: #252d30; --cs-mist-ink: #c6d0d1;
  --cs-mesh: radial-gradient(at 8% 0%, rgba(56, 140, 190, 0.18) 0, transparent 45%),
             radial-gradient(at 95% 5%, rgba(80, 160, 120, 0.14) 0, transparent 40%),
             radial-gradient(at 90% 95%, rgba(190, 160, 90, 0.10) 0, transparent 45%),
             radial-gradient(at 5% 90%, rgba(40, 150, 150, 0.12) 0, transparent 40%);
}

body { background-image: var(--cs-mesh) !important; background-attachment: fixed !important; }
.gradio-container { max-width: 1000px !important; margin: 0 auto !important; background: transparent !important; }
footer { opacity: .6; }

/* --- Header --- */
.cs-topbar { position: relative; gap: 0 !important; margin-top: 18px; }
.cs-topbar .html-container { padding: 0 !important; }
.cs-header { position: relative; overflow: hidden; padding: 26px 28px; border-radius: 28px;
  background: var(--cs-glass); border: 1px solid var(--cs-border); backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px); }
.cs-header::after { content: ""; position: absolute; width: 220px; height: 220px; right: -60px; top: -90px;
  border-radius: 50%; background: radial-gradient(circle, #b8e0cb 0%, #a7d3e8 45%, transparent 70%);
  opacity: .45; filter: blur(8px); pointer-events: none; }
.dark .cs-header::after { opacity: .16; }
.cs-logo { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 13px;
  font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--cs-muted); }
.cs-logo-mark { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 9px;
  background: linear-gradient(135deg, #a7d3e8, #b8e0cb); color: #1c2b2d; font-size: 14px; }
.cs-header h1 { margin: 0; font-family: "Space Grotesk", sans-serif; font-size: 44px; line-height: 1.05;
  font-weight: 700; letter-spacing: -0.03em; background-image: var(--cs-title) !important;
  -webkit-background-clip: text !important; background-clip: text !important; color: transparent !important; }
.cs-header p { margin: 8px 0 0; font-size: 17px; color: var(--cs-muted); max-width: 560px; }
.cs-logo { padding-right: 56px; }
.cs-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.cs-chip { padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: 600; }
.cs-chip-blue { background: var(--cs-blue); color: var(--cs-blue-ink); }
.cs-chip-mint { background: var(--cs-mint); color: var(--cs-mint-ink); }
.cs-chip-sand { background: var(--cs-sand); color: var(--cs-sand-ink); }

/* Theme toggle: a round button with a sun or moon in the header's corner; its text stays for screen readers */
#cs-theme-toggle { position: absolute !important; top: 16px; right: 16px; z-index: 2; width: 46px !important;
  min-width: 46px !important; height: 46px; padding: 0 !important; border-radius: 50% !important; font-size: 0 !important;
  background: var(--cs-glass) !important; border: 1px solid var(--cs-border) !important;
  box-shadow: 0 6px 20px -10px rgba(30, 70, 80, .35); transition: transform .2s ease; }
#cs-theme-toggle::before { content: "🌙"; font-size: 22px; line-height: 1; }
.dark #cs-theme-toggle::before { content: "☀️"; }
#cs-theme-toggle:hover { transform: rotate(-12deg) scale(1.05); }

/* --- Tabs as a pill switcher --- */
.cs-tabs > .tab-wrapper, .cs-tabs .tab-container { border: none !important; }
.cs-tabs .tab-container { display: inline-flex; gap: 4px; padding: 5px; margin: 6px 0 14px; border-radius: 999px;
  background: var(--cs-glass); border: 1px solid var(--cs-border) !important; backdrop-filter: blur(10px);
  height: auto !important; }
.cs-tabs .tab-container::after { display: none !important; }
.cs-tabs button[role="tab"] { border: none !important; border-radius: 999px !important; padding: 9px 18px !important;
  font-weight: 600; color: var(--cs-muted) !important; background: transparent !important; transition: all .2s ease; }
.cs-tabs button[role="tab"]:hover { color: var(--cs-text) !important; background: var(--cs-subtle) !important; }
.cs-tabs button[role="tab"][aria-selected="true"] { color: #1c2b2d !important;
  background: linear-gradient(120deg, #d3e9f3, #d6ecdf) !important; box-shadow: 0 4px 14px -6px rgba(90, 150, 160, .45); }
.cs-tabs button[role="tab"][aria-selected="true"]::after { display: none !important; }

.cs-intro { display: flex; align-items: center; gap: 10px; margin: 2px 0 6px; color: var(--cs-muted); font-size: 15px; }
.cs-intro-emoji { font-size: 22px; }
.cs-muted { color: var(--cs-muted); font-size: 14px; }

button.lg, button.md { font-weight: 700 !important; transition: transform .15s ease, box-shadow .15s ease !important; }

/* --- Messages and empty state --- */
.cs-empty { position: relative; padding: 44px 24px; text-align: center; border-radius: 24px;
  border: 2px dashed var(--cs-border); background: var(--cs-glass); }
.cs-empty-art { font-size: 40px; margin-bottom: 8px; }
.cs-empty h3 { margin: 0 0 6px; font-family: "Space Grotesk", sans-serif; font-size: 22px; color: var(--cs-text); }
.cs-empty p { margin: 0 auto; max-width: 440px; color: var(--cs-muted); }
.cs-message { padding: 14px 16px; border-radius: 16px; background: var(--cs-sky); color: var(--cs-sky-ink); font-weight: 500; }
.cs-message-error { background: var(--cs-clay); color: var(--cs-clay-ink); }
.cs-message-error::before { content: "⚠️ "; }

/* --- Progress --- */
.cs-progress { padding: 20px 22px; border-radius: 24px; background: var(--cs-glass); border: 1px solid var(--cs-border); }
.cs-stages { list-style: none; margin: 0 0 8px; padding: 0; }
.cs-stage { display: flex; align-items: center; gap: 12px; padding: 8px 0; color: var(--cs-muted); }
.cs-stage-mark { width: 30px; height: 30px; flex: none; display: grid; place-items: center; border-radius: 50%;
  font-size: 13px; font-weight: 700; background: var(--cs-mist); color: var(--cs-mist-ink); }
.cs-stage-active { color: var(--cs-text); font-weight: 700; }
.cs-stage-active .cs-stage-mark { background: linear-gradient(135deg, #a7d3e8, #b8e0cb); color: #1c2b2d;
  animation: cs-pulse 1.6s ease-in-out infinite; }
.cs-stage-done .cs-stage-mark { background: var(--cs-mint); color: var(--cs-mint-ink); }
@keyframes cs-pulse { 50% { transform: scale(.9); opacity: .7; } }

/* --- Report --- */
.cs-report { color: var(--cs-text); }
.cs-report h2 { margin: 6px 0; font-family: "Space Grotesk", sans-serif; font-size: 30px; letter-spacing: -0.02em; }
.cs-report h3 { margin: 30px 0 12px; font-family: "Space Grotesk", sans-serif; font-size: 20px; }
.cs-summary { line-height: 1.65; margin: 0 0 18px; color: var(--cs-text); }
.cs-state { display: inline-block; margin: 0 0 8px; padding: 6px 12px; border-radius: 999px; font-size: 13px;
  font-weight: 700; background: var(--cs-sand); color: var(--cs-sand-ink); }
.cs-state::before { content: "📝 "; }
.cs-state-approved { background: var(--cs-mint); color: var(--cs-mint-ink); }
.cs-state-approved::before { content: "🎉 "; }

.cs-stats { display: grid; grid-template-columns: 1.6fr 1fr 1fr 1fr; gap: 12px; }
.cs-stat { display: flex; flex-direction: column; gap: 2px; padding: 16px 18px; border-radius: 20px;
  font-size: 13px; font-weight: 600; background: var(--cs-mist); color: var(--cs-mist-ink); }
.cs-stat-value { font-family: "Space Grotesk", sans-serif; font-size: 30px; font-weight: 700; line-height: 1.1; }
.cs-stat:nth-child(1) { background: var(--cs-blue); color: var(--cs-blue-ink); }
.cs-stat:nth-child(2) { background: var(--cs-mint); color: var(--cs-mint-ink); }
.cs-stat:nth-child(3) { background: var(--cs-sand); color: var(--cs-sand-ink); }
.cs-stat:nth-child(4) { background: var(--cs-clay); color: var(--cs-clay-ink); }

.cs-skill { border: 1px solid var(--cs-border); border-radius: 20px; margin-bottom: 10px; background: var(--cs-surface);
  transition: transform .15s ease, box-shadow .15s ease; }
.cs-skill:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -14px rgba(30, 90, 100, .35); }
.cs-skill summary { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 14px 18px; cursor: pointer;
  list-style: none; }
.cs-skill summary::-webkit-details-marker { display: none; }
.cs-skill summary::before { content: "›"; display: inline-block; width: 14px; font-size: 20px; line-height: 1;
  color: var(--cs-muted); transition: transform .2s ease; }
.cs-skill[open] summary::before { transform: rotate(90deg); }
.cs-skill-name { font-weight: 700; }
.cs-tag { padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 600;
  background: var(--cs-sky); color: var(--cs-sky-ink); }
.cs-confidence { padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 700;
  background: var(--cs-mist); color: var(--cs-mist-ink); }
.cs-count { font-size: 12px; color: var(--cs-muted); margin-left: auto; }
.cs-badge { padding: 4px 11px; border-radius: 999px; font-size: 12px; font-weight: 700; white-space: nowrap; }
.cs-count:empty + .cs-badge { margin-left: auto; }
.cs-badge-strong { background: var(--cs-mint); color: var(--cs-mint-ink); }
.cs-badge-strong::before { content: "✓ "; }
.cs-badge-partial { background: var(--cs-sand); color: var(--cs-sand-ink); }
.cs-badge-partial::before { content: "◐ "; }
.cs-badge-none { background: var(--cs-mist); color: var(--cs-mist-ink); }
.cs-badge-none::before { content: "○ "; }
.cs-skill-body { padding: 0 18px 14px; }
.cs-skill-body:empty { display: none; }
.cs-citations { list-style: none; margin: 0; padding: 0; }
.cs-citation { padding: 12px 0; border-top: 1px dashed var(--cs-border); }
.cs-citation p { margin: 0 0 4px; }
.cs-source { font-size: 13px; overflow-wrap: anywhere; }
.cs-source a { color: var(--cs-accent); font-weight: 600; text-decoration: none; }
.cs-source a::before { content: "🔗 "; }
.cs-source a:hover { text-decoration: underline; }
.cs-citation pre { margin: 8px 0 0; padding: 12px 14px; border-radius: 14px; background: var(--cs-subtle);
  border: 1px solid var(--cs-border); font-size: 13px; overflow-x: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
.cs-gaps { padding-top: 10px; border-top: 1px dashed var(--cs-border); }
.cs-gaps h5 { margin: 0 0 4px; font-size: 13px; color: var(--cs-muted); }
.cs-gaps ul { margin: 0; padding-left: 18px; font-size: 14px; }

.cs-actions { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.cs-actions li { display: flex; gap: 14px; padding: 14px 16px; border-radius: 18px; background: var(--cs-surface);
  border: 1px solid var(--cs-border); }
.cs-actions p { margin: 2px 0 0; color: var(--cs-muted); }
.cs-priority { flex: none; align-self: flex-start; min-width: 64px; text-align: center; padding: 3px 8px; border-radius: 999px;
  font-size: 12px; font-weight: 700; text-transform: capitalize; background: var(--cs-mist); color: var(--cs-mist-ink); }
.cs-priority-high { background: var(--cs-clay); color: var(--cs-clay-ink); }
.cs-priority-medium { background: var(--cs-sand); color: var(--cs-sand-ink); }

/* --- Profile --- */
.cs-profiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.cs-profile { padding: 18px; border-radius: 20px; background: var(--cs-surface); border: 1px solid var(--cs-border); }
.cs-profile:nth-child(odd) h4 { background: var(--cs-blue); color: var(--cs-blue-ink); }
.cs-profile:nth-child(even) h4 { background: var(--cs-mint); color: var(--cs-mint-ink); }
.cs-profile h4 { display: inline-block; margin: 0 0 10px; padding: 4px 12px; border-radius: 999px; font-size: 14px; }
.cs-profile dl { margin: 0; }
.cs-profile dl div { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; font-size: 14px;
  border-bottom: 1px dashed var(--cs-border); }
.cs-profile dl div:last-child { border-bottom: none; }
.cs-profile dt { color: var(--cs-muted); }
.cs-profile dd { margin: 0; font-weight: 700; color: var(--cs-text); }

@media (prefers-reduced-motion: reduce) {
  .cs-stage-active .cs-stage-mark { animation: none; }
  .cs-skill, #cs-theme-toggle, button { transition: none !important; }
  .cs-skill:hover { transform: none; }
}

@media (max-width: 640px) {
  .gradio-container { padding: 0 16px !important; box-sizing: border-box; }
  .cs-header { padding: 20px; border-radius: 22px; }
  .cs-header h1 { font-size: 32px; }
  .cs-header p { font-size: 15px; }
  #cs-theme-toggle { top: 12px; right: 12px; width: 42px !important; min-width: 42px !important; height: 42px; }
  .cs-tabs .tab-container { display: flex; overflow-x: auto; scrollbar-width: none; }
  .cs-tabs button[role="tab"] { padding: 8px 14px !important; flex: none; }
  .cs-stats { grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .cs-stat { padding: 12px; }
  .cs-stat:nth-child(1) { grid-column: 1 / -1; }
  .cs-stat-value { font-size: 24px; }
  .cs-count { margin-left: 0; }
  .cs-actions li { flex-direction: column; gap: 8px; }
}
"""
