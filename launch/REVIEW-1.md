# Review 1 (maintainer, from rendered frames)

Fix these, then re-run `npx --yes hyperframes@0.9.28 check --json` in each changed project and
append a `## Review 1` section to NOTES.md. Same rules as BRIEF.md: FACTS.md is the only text,
edit only `launch/`, no render, no commit.

1. **hero: empty terminal at the start.** Frames 0–23 show a blank dark pane, which reads as a
   broken GIF on first view. Frame 0 must already show content in the terminal: start typing
   `provider jev` at 0.2 s (not 1.6 s) and shift the later beats earlier so each provider holds
   about 0.6 s longer. Keep the 12.0 s length and the seamless loop: the last frame must match
   frame 0, so at the loop point the pane shows the same partly typed or empty-prompt state as
   frame 0. If frame 0 must be an empty pane for the loop, show a muted prompt glyph `$` in it
   (a glyph, not words).
2. **social-card: install command wraps mid-word** (`hermes-` / `system-one`). The command must sit
   on one line: shrink its monospace size (not below 22 px) and/or widen the pill so
   `hermes plugins install salismt/hermes-system-one` fits on one line.
3. **social-card: orphan word.** Title line 1 breaks as `One tool for every decision` / `model.`.
   Widen the left column or set the break so it reads `One tool for every` / `decision model.`
   Same for line 2: `Switch the provider.` / `Keep the code.`
4. **how-it-works: vertical balance.** The diagram sits in the top 70% with an empty band below.
   Move the whole diagram (gates, provider list, message card, captions) down so the content is
   vertically centred in the 500 px frame. No other change.
