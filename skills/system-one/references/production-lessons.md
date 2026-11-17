# Running a System One integration in production

Lessons from a live triage bot built on a decision model (chat alert channel, push-triggered, about 60 alerts over 2 days) and from planning a decision router. Use these when you turn a probed prototype into something that runs unattended.

## Re-runs and state
- **Debounce re-evaluation per item and skip when the state fingerprint is unchanged.** Every thread reply (including other bots') triggers a re-run; one busy thread produced 14 runs in 20 minutes. Hash the exact state you send and store it; same hash = no call.
- **Make verdicts monotonic on evidence.** A concluded verdict changes only when a NEW conclusion appears, never because a later message failed to restate it. Otherwise "concluded" flips back to "needs review" as the thread grows.
- **Self-learned labels upsert, never append.** One label per item, latest wins, human-reviewed labels never overwritten. Appending recorded the same item as both classes when a thread reversed itself minutes later.
- **Attribution judgments ("who did it", "does the owner claim it") are the noisiest** (highest share of answers in the 0.3-0.7 band). Put names, roles and ownership in the state rather than asking the model to infer them from @-mentions.

## Evaluation
- **Report the honest replay number:** evaluate each case using only knowledge that existed before it. Replaying with today's knowledge base inflates accuracy (78% honest vs 98% with hindsight in one build) because repeats of known incidents look like skill.
- Track the per-question mid-band rate (share of Noul answers between the thresholds). A question that rises over time means the state stopped settling it.

## Precedent memory
- Exact lookups in code (same IP, same /24, same account id) plus ONE question per precedent ("does the team's earlier finding explain this item?") outperform asking the model to recall. Carry benign precedents only through the identifier that caused them (a caller IP), not a broader one (a merchant), or one harmless test whitelists real attacks.

## Before building
- **Check whether another bot already owns the workflow.** A second triage bot in a channel where an AI ops bot already posts verdicts is noise; the transferable asset is usually your knowledge base (benign entities, policy rules, labelled false alarms), not your bot.

## Pairing a decision model with an LLM
- The decision model supplies judgments and code decides (class, route, thresholds via a code truth table); the LLM only writes text (drafts, summaries, narrative). Code picks the LLM tier by the decided class (cheap model for routine drafts, stronger model for one-way-door / sensitive items) and caps calls per run.
- Batch all generation for a run into one LLM call. The agent framework's system prompt (tens of thousands of tokens) usually dwarfs the item itself, so per-item calls multiply the overhead.
- A failed LLM or decision-model call is an error line in the output, never a fabricated draft or a default verdict.

## Estimating cost
1. Read current list prices live (the provider's models or pricing page; the LLM vendor's pricing page). Decision models bill input tokens only; questions count as input; state is billed once per request.
2. Measure token sizes from logged payloads (`usage.input_tokens` per request) rather than guessing; average request size is the multiplier.
3. Measure volumes from the real sources (messages per source per week, bot vs human share) and drop what code rules handle before the model.
4. Compute in code: expected, pessimistic (3x volume, 2x LLM calls), and one-off (eval rounds, discovery scans). Always compare against the current baseline measured from logs.
5. Watch tier thresholds (e.g. a model priced higher above a prompt-length limit) and keep batches under them.
