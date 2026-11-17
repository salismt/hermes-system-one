# Hero specification

GOAL: Show one unchanged request, three provider settings, and the same answer contract.
OUTPUT: Silent seamless GIF source, 1200×600, 15 fps, 180 frames. No export in this task.
TIME: 12.0 seconds; frame 179 matches frame 0.
LOOK: #F4F5F2 ground, #17191C ink, #5F636A muted; #16181B terminal, #E6E8E3 text, #9AA0A6 muted terminal. #1D9E75 answer dots only. Inter 600 titles, IBM Plex Mono 400 terminal. Minimum 22px text; 40px pitch. Request occupies 420px; terminal 620px. No shadows.
OBJECTS: Fixed request card; one terminal with a muted $ prompt at the loop seam; three answer blocks that compact into rows; one command per provider; probability bars; bottom pitch and measurement caption. All copy from ../FACTS.md.
MOTION: Commands reveal one character per 0.025s. Output lines print whole. Answer blocks compact upward as one object over 0.5s, secondary details clear during compaction, billing shifts into the model row. Bars grow once over 0.4s. Reset completes by frame 178.
SHOTS (inclusive frame ranges, zero based):
- 0–2: unchanged request and muted terminal prompt.
- 3–53: provider jev; measured output and bar.
- 54–104: compact jev; provider liquid and output.
- 105–149: compact liquid; provider ollama and output; pitch appears at frame 144.
- 150–167: compact ollama; compare three rows; pitch and measurement caption hold.
- 168–179: clear terminal content and bottom pitch; restore the muted prompt by frame 177. Request and terminal shell stay fixed.
BANNED: Dark void, floating cards, glow, particles, gradients, 3D tilt, generic slide-up fades, three side-by-side cards, corner logo, empty prompt typing opener, provider logos, audio, invented copy, runtime clocks, render, snapshot, preview, commit.
