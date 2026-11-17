# Launch handoff

Built three silent, editable HyperFrames compositions. All work stays under `launch/`.

- `hero/index.html`: 1200×600, 15 fps, 12 seconds. The request stays fixed while jev, liquid, and ollama print measured answers. Bars grow once. Answer blocks compact upward into a three-row comparison. The terminal content clears before the final frame.
- `how-it-works/index.html`: 1200×500, 15 fps, 8 seconds. One connected gate diagram. The first token passes all gates and returns green. The second stops at model check, turns red, and prints the exact refusal. All seven providers remain listed; ollama uses ink and an underline. The final frames restore the initial token, position, label, and color.
- `social-card/index.html`: 1280×640, 1 second, static throughout. Pitch and install command on the left; three compact result rows on the right. Content respects the requested 40px safe margins. The measurement caption is included because the card shows measured answers.

Each root mounts one editable scene from `compositions/`. Copy, palette, and fonts are declared as composition variables. Timelines are paused, registered after their tweens, and seekable. No runtime clocks, audio, render, snapshot, preview, or commit was used.

## Validation

In each project, ran `npx --yes hyperframes@0.9.28 check --json` in the foreground, with an explicit 55-second subprocess timeout. All commands finished with exit code 0 and `ok: true`. Lint, runtime, layout, motion, and contrast sections report zero errors. Final JSON results are in each project's `check-result.json`; CLI diagnostics are in `check-stderr.log`. These checks do not establish visual approval; the maintainer will render and provide frame feedback. The reports confirm snapshots were disabled and no snapshot files were produced.

Warnings retained:

- Hero: none.
- How it works: one `line_unread` warning. The initial request label returns at 7.85 seconds to complete the seamless loop. The checker treats that 0.14-second tail as a closing title. It is a reset to the opening state, which continues into the next loop.
- Social card: twelve `line_unread` warnings. The checker applies motion-picture reading durations to all text in the requested one-second static composition. The scene is marked `data-no-timeline`; the last frame is the intended still, so its viewing time is controlled by the reader.
- All three report `audio_none` as informational. Silence is required.

The CLI also reports an available version update and an inability to write its optional global history cache outside the permitted workspace. The requested 0.9.28 pin was retained. Local check reports were saved under `launch/`.

## Copy and scope

All required on-screen copy fits. Copy and measured values come only from `FACTS.md`; the state has quotation marks as requested. Labels combine the question ids, types, and values specified in the brief. Commands use the explicitly allowed short forms.

The other FACTS entries are intentionally unused because the brief selects only three runs: alternative models, full config commands, provider subtitles, count line, question prompts/options, spend-cap refusal, and the extraction-state example. No required text was shortened or omitted. The registry terminal and bar examples informed the implementation; unused downloaded component files were removed so their sample copy cannot enter a composition.

No visual review was performed, as requested.

## Review 1

Applied all four maintainer requests inside `launch/`:

- Hero: frame 0 now shows a muted `$` prompt, as permitted by REVIEW-1.md. `provider jev` starts at 0.2 seconds. Provider changes now start at 3.6 and 7.0 seconds, with final compaction at 10.0 seconds. Each provider's expanded answer holds 0.6 seconds longer. The pitch still starts at 9.6 seconds. The 12-second duration remains unchanged. Content clears by 11.8 seconds and the prompt returns then, so frame 179 matches frame 0. Updated `hero/SPEC.md` to match.
- Social card install: kept the 22px monospace size, widened the copy column and pill to 650px, reduced horizontal pill padding to 6px, and used `white-space: nowrap`. The exact install command stays on one line without overflow.
- Social card titles: set both title widths to 420px for `One tool for every` / `decision model.` and `Switch the provider.` / `Keep the code.`. All copy remains unchanged.
- How it works: moved the rail, gates, tokens, provider list, refusal card, and captions down by 10px. Relative positions, copy, and animation timings remain unchanged.

Validation: reran `npx --yes hyperframes@0.9.28 check --json` in each changed project. Each command ran in the foreground with a 55-second subprocess timeout and exited 0 with `ok: true`. All lint, runtime, layout, motion, and contrast sections report zero errors. Layout reports zero warnings. Refreshed each project's `check-result.json` and `check-stderr.log`.

Warnings retained after review:

- Hero: one `line_unread` warning for the `$` prompt returning during the final 0.2 seconds. It is a loop seam glyph, not a closing sentence, and continues into the opening state.
- How it works: the existing single `line_unread` warning for the request label returning at the loop seam.
- Social card: the existing twelve `line_unread` warnings apply film reading durations to the requested one-second still. Readers control its viewing duration.
- All three retain the required-silence `audio_none` informational finding. No required FACTS.md copy was removed or shortened.

The default npm cache was not writable. Checks used a temporary npm cache inside `launch/`, which was removed after validation. The pinned CLI version remains 0.9.28. No render, snapshot, preview, or commit was run. Check reports confirm snapshots were disabled and no snapshot files were produced. Visual approval remains with the maintainer.
