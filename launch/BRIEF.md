# Brief for Codex: system-one README motion graphics (HyperFrames)

You are building three short, silent pieces for the system-one README: two GIF loops and one
still image. No voice, no music. Keep the compositions simple and finish in one pass.

## Read first (in this order)

1. `~/.agents/skills/hyperframes/SKILL.md` and the references it points to for this job (at least
   `references/format.md`, `references/motion.md`, `references/look.md`). Follow its contract
   exactly (timeline registration, `data-*` attributes, seekable animation, no runtime clocks).
2. `FACTS.md` in this folder: the ONLY text allowed on screen. Copy strings verbatim; shorten with
   "…" only. If a label you want isn't in FACTS.md, leave it out.

The projects are already initialised: `hero/`, `how-it-works/`, `social-card/` (HyperFrames
0.9.28, pinned in each `package.json`). Edit their `index.html` (add `compositions/` scenes only if
the skill asks for them). Set each root's size as below (`data-width`, `data-height`, viewport meta
and CSS). Write `SPEC.md` in `hero/` before building it: GOAL, OUTPUT, TIME, LOOK, OBJECTS, MOTION,
SHOTS (frame ranges), BANNED.

## Shared look

- Ground: cool off-white `#F4F5F2`; ink `#17191C`; muted `#5F636A`. Terminal panes: `#16181B` with
  text `#E6E8E3`, muted terminal text `#9AA0A6`.
- Colour carries meaning only: green `#1D9E75` = an answer came back; red `#E24B4A` = refused
  before sending. The chosen option's probability bar uses ink (light ground) or `#E6E8E3`
  (terminal). No other accents.
- Type: a bundled sans for titles and a bundled monospace for terminal text (see
  `references/format.md` for the bundled names). Titles weight 600, at most 6 words a line.
- Readability: shown in a GitHub README at about 880 px wide. At 1200 px source width, no text
  below 22 px; terminal text 22–24 px; titles 40–56 px.
- Banned: dark void with floating cards, glow, particles, gradients, 3D tilt, everything sliding up
  and fading, three cards in a row, a logo docked in a corner, typing into an empty prompt box as
  the opener, provider logos (we have no rights to them; names as text only).
- Motion: terminal lines appear whole, the way a terminal prints them; commands may type at about
  40 chars/s. Panels move as whole objects with 0.4–0.6 s eases. Every element holds still once it
  lands. Probability bars grow once to their value (0.4 s) and then hold.

## 1. `hero/`: same request, switch the provider. 1200×600, 15 fps, 12.0 s, seamless loop

The story: the request never changes; one setting does; the answer shape stays the same.

- **0.0–1.6** Frame 0 is already the request card on the left (about 40% width): the state in
  quotes, then the three question ids with their type (`department · choice`, `is_urgent · noul`,
  `frustration · score`). It stays on screen, unchanged, for the whole piece.
- **1.6–4.4** Right side: one terminal pane. Command `provider jev` types; then the answer block
  prints: model line `jev · jev-1.14.0`, a `billing 0.87` bar, `is_urgent 0.94`, and the meta line
  `1.6 s · $0.0000169` with a small green dot.
- **4.4–7.2** The answer block slides up as one object (it becomes a compact one-line summary row
  above), the command `provider liquid` types, and the next answer block prints:
  `liquid · d1.2-ultra`, `billing 0.91`, `is_urgent 0.92`, `486 ms · $0.00000559`.
- **7.2–9.6** Same move. `provider ollama`, then `ollama · laya`, `billing 0.84`, `is_urgent 0.74`,
  `68 ms · $0 · on your machine`.
- **9.6–11.2** The three compact rows hold as a stack (jev, liquid, ollama) so the viewer can
  compare. Across the bottom: the pitch `Switch the provider. Keep the code.` and below it, small,
  `One request, measured once per model. Not a benchmark.`
- **11.2–12.0** The terminal clears back to frame-0 state so the GIF loops without a jump (the
  request card never moved).

## 2. `how-it-works/`: one call through the gates. 1200×500, 15 fps, 8.0 s, seamless loop

One frame that rebuilds (no cuts). Left to right, connected by one line: `system_one tool` →
`model check` → `spend cap` → `provider` → `answers`. Under `provider`, the seven provider names
from FACTS.md as a small vertical list with `ollama` highlighted (ink).

- **0.0–3.6 pass:** a request token (labelled `department · is_urgent · frustration`) travels the
  line; each gate ticks as it passes; at `answers` the token turns green and the caption
  `checked, sent, answered` appears.
- **3.6–7.4 fail:** a second token labelled `invoice · text` travels from `system_one tool`, stops
  at `model check` in red, and a message card under the gate shows, in monospace, the exact
  unsupported-type message from FACTS.md, then the caption `refused before sending · nothing billed`.
  The token never reaches `provider`.
- **7.4–8.0** Reset to frame 0.

## 3. `social-card/`: repo social preview. 1280×640, a still

One composition, 1 s long, designed as a still (the last frame is the image). Left 55%: wordmark
`system-one` above the two pitch lines as the title, the sub-pitch below, then the install command
in a small monospace pill. Right 45%: a static miniature of the hero's final stack: three compact
rows (`jev · jev-1.14.0 · billing 0.87`, `liquid · d1.2-ultra · billing 0.91`,
`ollama · laya · billing 0.84 · $0`). Keep 40 px safe margins (GitHub crops social images).

## Done means

- In each project: `npx hyperframes check --json` (use the pinned version: `npx --yes
  hyperframes@0.9.28 check --json`) reports no errors. Fix every error; weigh warnings.
- Write `NOTES.md` in `launch/`: what you built, any check warnings you left and why, and anything
  in FACTS.md you could not fit.
- Do NOT render, snapshot or preview. The maintainer renders and sends you frame feedback.
- Do not edit anything outside `launch/`. Do not commit.
- Run every check in the foreground with a timeout, read its output, fix, repeat.
