import gradio as gr

theme = gr.themes.Soft(
    primary_hue="teal",
    secondary_hue="teal",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
)

custom_css = """
:root {
  --cs-surface: #ffffff; --cs-subtle: #f1f5f9; --cs-border: #e2e8f0;
  --cs-text: #0f172a; --cs-muted: #526077; --cs-accent: #0f766e;
  --cs-good: #166534; --cs-good-bg: #dcfce7;
  --cs-mid: #92400e; --cs-mid-bg: #fef3c7;
  --cs-low: #475569; --cs-low-bg: #e2e8f0;
  --cs-bad: #991b1b; --cs-bad-bg: #fee2e2;
}
.dark {
  --cs-surface: #1e293b; --cs-subtle: #0f172a; --cs-border: #334155;
  --cs-text: #f1f5f9; --cs-muted: #a3b1c6; --cs-accent: #5eead4;
  --cs-good: #86efac; --cs-good-bg: #14532d;
  --cs-mid: #fcd34d; --cs-mid-bg: #78350f;
  --cs-low: #cbd5e1; --cs-low-bg: #334155;
  --cs-bad: #fca5a5; --cs-bad-bg: #7f1d1d;
}
.gradio-container { max-width: 960px !important; margin: 0 auto !important; }
.cs-header { padding: 20px 0 8px; }
.cs-header h1 { font-size: 30px; font-weight: 700; margin: 0; color: var(--cs-text); }
.cs-header p { margin: 4px 0 0; font-size: 16px; color: var(--cs-muted); }
.cs-intro { color: var(--cs-muted); margin: 4px 0; }
.cs-muted { color: var(--cs-muted); font-size: 14px; }

.cs-empty { padding: 36px 20px; text-align: center; border: 1px dashed var(--cs-border); border-radius: 12px; }
.cs-empty h3 { margin: 0 0 6px; color: var(--cs-text); }
.cs-empty p { margin: 0; color: var(--cs-muted); }
.cs-message { padding: 12px 14px; border-radius: 10px; background: var(--cs-subtle); color: var(--cs-text); }
.cs-message-error { background: var(--cs-bad-bg); color: var(--cs-bad); }

.cs-stages { list-style: none; margin: 8px 0; padding: 0; }
.cs-stage { display: flex; align-items: center; gap: 10px; padding: 7px 0; color: var(--cs-muted); }
.cs-stage-mark { width: 26px; height: 26px; flex: none; display: grid; place-items: center; border-radius: 50%;
  font-size: 13px; font-weight: 600; background: var(--cs-subtle); border: 1px solid var(--cs-border); }
.cs-stage-active { color: var(--cs-text); font-weight: 600; }
.cs-stage-active .cs-stage-mark { background: var(--cs-accent); color: var(--cs-surface); border-color: var(--cs-accent);
  animation: cs-pulse 1.6s ease-in-out infinite; }
.cs-stage-done .cs-stage-mark { background: var(--cs-good-bg); color: var(--cs-good); border-color: transparent; }
@keyframes cs-pulse { 50% { opacity: .55; } }
@media (prefers-reduced-motion: reduce) { .cs-stage-active .cs-stage-mark { animation: none; } }

.cs-report { color: var(--cs-text); }
.cs-report h2 { font-size: 24px; margin: 6px 0; }
.cs-report h3 { font-size: 18px; margin: 26px 0 10px; }
.cs-summary { line-height: 1.6; margin: 0 0 16px; }
.cs-state { display: inline-block; margin: 0 0 8px; padding: 4px 10px; border-radius: 999px; font-size: 13px;
  font-weight: 600; background: var(--cs-mid-bg); color: var(--cs-mid); }
.cs-state-approved { background: var(--cs-good-bg); color: var(--cs-good); }

.cs-stats { display: grid; grid-template-columns: 1.6fr 1fr 1fr 1fr; gap: 10px; }
.cs-stat { display: flex; flex-direction: column; padding: 12px 14px; border: 1px solid var(--cs-border);
  border-radius: 10px; background: var(--cs-surface); font-size: 13px; color: var(--cs-muted); }
.cs-stat-value { font-size: 24px; font-weight: 700; color: var(--cs-text); }
.cs-stat-main .cs-stat-value { color: var(--cs-accent); }

.cs-skill { border: 1px solid var(--cs-border); border-radius: 10px; margin-bottom: 8px; background: var(--cs-surface); }
.cs-skill summary { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 12px 14px; cursor: pointer; }
.cs-skill-name { font-weight: 600; }
.cs-tag { font-size: 12px; color: var(--cs-muted); }
.cs-count { font-size: 12px; color: var(--cs-muted); margin-left: auto; }
.cs-badge { padding: 3px 9px; border-radius: 999px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.cs-count:empty + .cs-badge { margin-left: auto; }
.cs-badge-strong { background: var(--cs-good-bg); color: var(--cs-good); }
.cs-badge-partial { background: var(--cs-mid-bg); color: var(--cs-mid); }
.cs-badge-none { background: var(--cs-low-bg); color: var(--cs-low); }
.cs-skill-body { padding: 0 14px 12px; }
.cs-skill-body:empty { display: none; }
.cs-citations { list-style: none; margin: 0; padding: 0; }
.cs-citation { padding: 10px 0; border-top: 1px solid var(--cs-border); }
.cs-citation p { margin: 0 0 4px; }
.cs-source { font-size: 13px; overflow-wrap: anywhere; }
.cs-source a { color: var(--cs-accent); }
.cs-citation pre { margin: 6px 0 0; padding: 10px; border-radius: 8px; background: var(--cs-subtle);
  font-size: 13px; overflow-x: auto; white-space: pre-wrap; overflow-wrap: anywhere; }
.cs-gaps { padding-top: 8px; border-top: 1px solid var(--cs-border); }
.cs-gaps h5 { margin: 0 0 4px; font-size: 13px; color: var(--cs-muted); }
.cs-gaps ul { margin: 0; padding-left: 18px; font-size: 14px; }

.cs-actions { list-style: none; margin: 0; padding: 0; }
.cs-actions li { display: flex; gap: 12px; padding: 10px 0; border-top: 1px solid var(--cs-border); }
.cs-actions p { margin: 2px 0 0; }
.cs-priority { flex: none; align-self: flex-start; width: 62px; text-align: center; padding: 2px 0; border-radius: 6px;
  font-size: 12px; font-weight: 600; background: var(--cs-low-bg); color: var(--cs-low); }
.cs-priority-high { background: var(--cs-bad-bg); color: var(--cs-bad); }
.cs-priority-medium { background: var(--cs-mid-bg); color: var(--cs-mid); }

.cs-profiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }
.cs-profile { padding: 14px; border: 1px solid var(--cs-border); border-radius: 10px; background: var(--cs-surface); }
.cs-profile h4 { margin: 0 0 8px; color: var(--cs-text); }
.cs-profile dl { margin: 0; }
.cs-profile dl div { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; font-size: 14px; }
.cs-profile dt { color: var(--cs-muted); }
.cs-profile dd { margin: 0; font-weight: 600; color: var(--cs-text); }

@media (max-width: 640px) {
  .gradio-container { padding: 0 16px !important; box-sizing: border-box; }
  .gradio-container .tab-container { overflow-x: auto; scrollbar-width: none; }
  .gradio-container .tab-container button { padding-left: 8px; padding-right: 8px; font-size: 14px; flex: none; }
  .cs-header h1 { font-size: 26px; }
  .cs-state { border-radius: 10px; }
  .cs-stats { grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .cs-stat { padding: 10px; }
  .cs-stat-main { grid-column: 1 / -1; }
  .cs-count { margin-left: 0; }
  .cs-actions li { flex-direction: column; gap: 6px; }
}
"""
