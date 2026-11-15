"""Pastel look for the UI, with matching light and dark modes.

Pastels are used for backgrounds, badges and buttons. Text on them stays dark (light mode)
or light (dark mode) so it keeps enough contrast to read.
"""
import gradio as gr

# Light: cream with lavender, pink and mint. Dark: deep plum with the same pastels as accents.
LIGHT = {
    "bg": "#fbf8ff", "surface": "#ffffff", "subtle": "#f4effe", "border": "#e7defa",
    "text": "#241b3a", "muted": "#675e82", "accent": "#7c3aed",
}
DARK = {
    "bg": "#13111c", "surface": "#1c1929", "subtle": "#252036", "border": "#352e4d",
    "text": "#f4effe", "muted": "#b7adcf", "accent": "#c4b5fd",
}
BUTTON_GRADIENT = "linear-gradient(120deg, #c4b5fd 0%, #f9a8d4 55%, #fcd5b5 100%)"
BUTTON_GRADIENT_HOVER = "linear-gradient(120deg, #b4a2fb 0%, #f692c7 55%, #fbc79f 100%)"

theme = gr.themes.Base(
    primary_hue="violet",
    secondary_hue="pink",
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
    color_accent_soft="#ede4ff",
    color_accent_soft_dark="#2e2645",
    link_text_color=LIGHT["accent"],
    link_text_color_dark=DARK["accent"],
    block_background_fill=LIGHT["surface"],
    block_background_fill_dark=DARK["surface"],
    block_border_color=LIGHT["border"],
    block_border_color_dark=DARK["border"],
    block_radius="20px",
    block_shadow="0 6px 24px -12px rgba(76, 45, 140, 0.18)",
    block_shadow_dark="0 6px 24px -12px rgba(0, 0, 0, 0.6)",
    block_label_text_color=LIGHT["muted"],
    block_label_text_color_dark=DARK["muted"],
    block_title_text_color=LIGHT["text"],
    block_title_text_color_dark=DARK["text"],
    input_background_fill=LIGHT["surface"],
    input_background_fill_dark=DARK["subtle"],
    input_border_color=LIGHT["border"],
    input_border_color_dark=DARK["border"],
    input_border_color_focus="#a78bfa",
    input_border_color_focus_dark="#c4b5fd",
    input_shadow_focus="0 0 0 4px rgba(196, 181, 253, 0.45)",
    input_shadow_focus_dark="0 0 0 4px rgba(196, 181, 253, 0.25)",
    input_radius="14px",
    input_placeholder_color="#a59cc0",
    input_placeholder_color_dark="#7d7499",
    button_large_radius="999px",
    button_medium_radius="999px",
    button_small_radius="999px",
    button_primary_background_fill=BUTTON_GRADIENT,
    button_primary_background_fill_dark=BUTTON_GRADIENT,
    button_primary_background_fill_hover=BUTTON_GRADIENT_HOVER,
    button_primary_background_fill_hover_dark=BUTTON_GRADIENT_HOVER,
    button_primary_text_color="#241b3a",
    button_primary_text_color_dark="#1b1430",
    button_primary_border_color="transparent",
    button_primary_border_color_dark="transparent",
    button_primary_shadow="0 8px 20px -8px rgba(219, 112, 181, 0.55)",
    button_secondary_background_fill=LIGHT["subtle"],
    button_secondary_background_fill_dark=DARK["subtle"],
    button_secondary_background_fill_hover="#ece3fd",
    button_secondary_background_fill_hover_dark="#2e2845",
    button_secondary_text_color=LIGHT["text"],
    button_secondary_text_color_dark=DARK["text"],
    button_secondary_border_color=LIGHT["border"],
    button_secondary_border_color_dark=DARK["border"],
    button_transform_hover="translateY(-1px)",
    loader_color="#c4b5fd",
    code_background_fill=LIGHT["subtle"],
    code_background_fill_dark="#15121f",
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
  --cs-surface: #ffffff; --cs-subtle: #f4effe; --cs-border: #e7defa;
  --cs-text: #241b3a; --cs-muted: #675e82; --cs-accent: #7c3aed;
  --cs-glass: rgba(255, 255, 255, 0.72);
  --cs-title: linear-gradient(100deg, #7c3aed 0%, #db2777 50%, #0f8f7e 100%);
  --cs-lavender: #ede4ff; --cs-lavender-ink: #5b21b6;
  --cs-pink: #ffe1ef; --cs-pink-ink: #9d174d;
  --cs-mint: #d6f5e8; --cs-mint-ink: #0f6b53;
  --cs-butter: #fdf0c4; --cs-butter-ink: #8a5a00;
  --cs-sky: #dcefff; --cs-sky-ink: #1e5a8a;
  --cs-mist: #ece9f3; --cs-mist-ink: #575170;
  --cs-mesh: radial-gradient(at 8% 0%, #efe6ff 0, transparent 45%),
             radial-gradient(at 95% 5%, #ffe6f2 0, transparent 40%),
             radial-gradient(at 90% 95%, #dcf7ec 0, transparent 45%),
             radial-gradient(at 5% 90%, #e2f0ff 0, transparent 40%);
}
.dark {
  --cs-surface: #1c1929; --cs-subtle: #252036; --cs-border: #352e4d;
  --cs-text: #f4effe; --cs-muted: #b7adcf; --cs-accent: #c4b5fd;
  --cs-glass: rgba(28, 25, 41, 0.72);
  --cs-title: linear-gradient(100deg, #c4b5fd 0%, #f9a8d4 50%, #99f6e4 100%);
  --cs-lavender: #2f2650; --cs-lavender-ink: #d8ccff;
  --cs-pink: #43213a; --cs-pink-ink: #fbc4e0;
  --cs-mint: #173a33; --cs-mint-ink: #a7f3d0;
  --cs-butter: #3d3218; --cs-butter-ink: #fde68a;
  --cs-sky: #1a3047; --cs-sky-ink: #bae6fd;
  --cs-mist: #2a2639; --cs-mist-ink: #cdc6e0;
  --cs-mesh: radial-gradient(at 8% 0%, rgba(124, 58, 237, 0.22) 0, transparent 45%),
             radial-gradient(at 95% 5%, rgba(219, 39, 119, 0.16) 0, transparent 40%),
             radial-gradient(at 90% 95%, rgba(13, 148, 136, 0.16) 0, transparent 45%),
             radial-gradient(at 5% 90%, rgba(56, 189, 248, 0.12) 0, transparent 40%);
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
  border-radius: 50%; background: radial-gradient(circle, #f9a8d4 0%, #c4b5fd 45%, transparent 70%);
  opacity: .45; filter: blur(8px); pointer-events: none; }
.cs-logo { display: inline-flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 13px;
  font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--cs-muted); }
.cs-logo-mark { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 9px;
  background: linear-gradient(135deg, #c4b5fd, #f9a8d4); color: #241b3a; font-size: 14px; }
.cs-header h1 { margin: 0; font-family: "Space Grotesk", sans-serif; font-size: 44px; line-height: 1.05;
  font-weight: 700; letter-spacing: -0.03em; background-image: var(--cs-title) !important;
  -webkit-background-clip: text !important; background-clip: text !important; color: transparent !important; }
.cs-header p { margin: 8px 0 0; font-size: 17px; color: var(--cs-muted); max-width: 560px; }
.cs-logo { padding-right: 56px; }
.cs-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.cs-chip { padding: 6px 12px; border-radius: 999px; font-size: 13px; font-weight: 600; }
.cs-chip-lavender { background: var(--cs-lavender); color: var(--cs-lavender-ink); }
.cs-chip-mint { background: var(--cs-mint); color: var(--cs-mint-ink); }
.cs-chip-pink { background: var(--cs-pink); color: var(--cs-pink-ink); }

/* Theme toggle: a round button with a sun or moon in the header's corner; its text stays for screen readers */
#cs-theme-toggle { position: absolute !important; top: 16px; right: 16px; z-index: 2; width: 46px !important;
  min-width: 46px !important; height: 46px; padding: 0 !important; border-radius: 50% !important; font-size: 0 !important;
  background: var(--cs-glass) !important; border: 1px solid var(--cs-border) !important;
  box-shadow: 0 6px 20px -10px rgba(76, 45, 140, .4); transition: transform .2s ease; }
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
.cs-tabs button[role="tab"][aria-selected="true"] { color: #241b3a !important;
  background: linear-gradient(120deg, #ddd0ff, #ffd3e8) !important; box-shadow: 0 4px 14px -6px rgba(196, 120, 200, .6); }
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
.cs-message-error { background: var(--cs-pink); color: var(--cs-pink-ink); }
.cs-message-error::before { content: "⚠️ "; }

/* --- Progress --- */
.cs-progress { padding: 20px 22px; border-radius: 24px; background: var(--cs-glass); border: 1px solid var(--cs-border); }
.cs-stages { list-style: none; margin: 0 0 8px; padding: 0; }
.cs-stage { display: flex; align-items: center; gap: 12px; padding: 8px 0; color: var(--cs-muted); }
.cs-stage-mark { width: 30px; height: 30px; flex: none; display: grid; place-items: center; border-radius: 50%;
  font-size: 13px; font-weight: 700; background: var(--cs-mist); color: var(--cs-mist-ink); }
.cs-stage-active { color: var(--cs-text); font-weight: 700; }
.cs-stage-active .cs-stage-mark { background: linear-gradient(135deg, #c4b5fd, #f9a8d4); color: #241b3a;
  animation: cs-pulse 1.6s ease-in-out infinite; }
.cs-stage-done .cs-stage-mark { background: var(--cs-mint); color: var(--cs-mint-ink); }
@keyframes cs-pulse { 50% { transform: scale(.9); opacity: .7; } }

/* --- Report --- */
.cs-report { color: var(--cs-text); }
.cs-report h2 { margin: 6px 0; font-family: "Space Grotesk", sans-serif; font-size: 30px; letter-spacing: -0.02em; }
.cs-report h3 { margin: 30px 0 12px; font-family: "Space Grotesk", sans-serif; font-size: 20px; }
.cs-summary { line-height: 1.65; margin: 0 0 18px; color: var(--cs-text); }
.cs-state { display: inline-block; margin: 0 0 8px; padding: 6px 12px; border-radius: 999px; font-size: 13px;
  font-weight: 700; background: var(--cs-butter); color: var(--cs-butter-ink); }
.cs-state::before { content: "📝 "; }
.cs-state-approved { background: var(--cs-mint); color: var(--cs-mint-ink); }
.cs-state-approved::before { content: "🎉 "; }

.cs-stats { display: grid; grid-template-columns: 1.6fr 1fr 1fr 1fr; gap: 12px; }
.cs-stat { display: flex; flex-direction: column; gap: 2px; padding: 16px 18px; border-radius: 20px;
  font-size: 13px; font-weight: 600; background: var(--cs-mist); color: var(--cs-mist-ink); }
.cs-stat-value { font-family: "Space Grotesk", sans-serif; font-size: 30px; font-weight: 700; line-height: 1.1; }
.cs-stat:nth-child(1) { background: var(--cs-lavender); color: var(--cs-lavender-ink); }
.cs-stat:nth-child(2) { background: var(--cs-mint); color: var(--cs-mint-ink); }
.cs-stat:nth-child(3) { background: var(--cs-butter); color: var(--cs-butter-ink); }
.cs-stat:nth-child(4) { background: var(--cs-pink); color: var(--cs-pink-ink); }

.cs-skill { border: 1px solid var(--cs-border); border-radius: 20px; margin-bottom: 10px; background: var(--cs-surface);
  transition: transform .15s ease, box-shadow .15s ease; }
.cs-skill:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -14px rgba(124, 58, 237, .45); }
.cs-skill summary { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 14px 18px; cursor: pointer;
  list-style: none; }
.cs-skill summary::-webkit-details-marker { display: none; }
.cs-skill summary::before { content: "›"; display: inline-block; width: 14px; font-size: 20px; line-height: 1;
  color: var(--cs-muted); transition: transform .2s ease; }
.cs-skill[open] summary::before { transform: rotate(90deg); }
.cs-skill-name { font-weight: 700; }
.cs-tag { padding: 2px 9px; border-radius: 999px; font-size: 12px; font-weight: 600;
  background: var(--cs-sky); color: var(--cs-sky-ink); }
.cs-count { font-size: 12px; color: var(--cs-muted); margin-left: auto; }
.cs-badge { padding: 4px 11px; border-radius: 999px; font-size: 12px; font-weight: 700; white-space: nowrap; }
.cs-count:empty + .cs-badge { margin-left: auto; }
.cs-badge-strong { background: var(--cs-mint); color: var(--cs-mint-ink); }
.cs-badge-strong::before { content: "✓ "; }
.cs-badge-partial { background: var(--cs-butter); color: var(--cs-butter-ink); }
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
.cs-priority-high { background: var(--cs-pink); color: var(--cs-pink-ink); }
.cs-priority-medium { background: var(--cs-butter); color: var(--cs-butter-ink); }

/* --- Profile --- */
.cs-profiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.cs-profile { padding: 18px; border-radius: 20px; background: var(--cs-surface); border: 1px solid var(--cs-border); }
.cs-profile:nth-child(odd) h4 { background: var(--cs-lavender); color: var(--cs-lavender-ink); }
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
