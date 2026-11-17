---
name: system-one
description: >
  Write and debug typed questions for System One decision models (TypeSafe Jev, Liquid d1.2 /
  d1.2-ultra, any compatible endpoint) through the system_one tool. Use when classifying,
  routing, scoring, gating yes/no or extracting from text or images with calibrated probabilities;
  when replacing an LLM prompt-and-parse step, keyword matching or a brittle heuristic with a typed
  question; or when designing state and questions for one of these models.
license: MIT
---

# Build with System One decision models

System One models (also called decision models) answer typed questions about state your
application supplies. State is the text, images, and application data sent with a request. A
model can answer a Choice among options, a Noul (the probability that a statement is true), a
Score on levels you describe, and, depending on the provider, extraction and grounding types.
Each answer comes back as typed data with calibrated probabilities, for your code to use.
Nothing is generated, and only input tokens are billed.

Call them with the `system_one` tool. The provider and model come from the plugin settings, and
every call is checked against the user's spend caps. A `budget_exceeded` or `provider_error`
result is an error to report. Never treat it as an answer, for example as a "no".

The rest of this skill is guidance: patterns that tend to produce reliable integrations. None of
it is absolute. Models change, applications differ, and edge cases exist. When a situation calls
for something else, test the alternative and use your judgment.

Adapted from TypeSafe's `typesafe-ai` skill (MIT, (c) 2026 TypeSafe AI). See LICENSE.

## Judgments from the model, decisions in code

Integrations tend to work best when the model makes the judgments and code decides what to do with
them. Think of each decision as a **truth table**. The model supplies the inputs, such as "Does the
customer sound frustrated?" or "Which product is the message about?". Code holds the logic that
maps those inputs to an action.

A question that asks the model to make the decision, such as "Should this ticket be escalated?" or "What
should the agent do next?", usually means the question is at the wrong layer. Instead, break the
decision into the judgments it depends on, and write the decision itself in code, where it's
visible and testable. Writing out the table often shows gaps in the business logic too. A
combination of judgments with no defined outcome is a design question about the system, and it is
best settled in code.

## Providers and live docs

The `system_one` tool sends every request to the provider set in the plugin settings
(`/system-one` shows which one is active). All providers share one contract:
`POST {base_url}/v1/systemone` with `{"model", "state", "questions"}`. Answers come back as
`{"model", "usage", "answers"}`, with one entry per question id.

| Provider | Models | Docs (source of truth for syntax, types, limits) |
| --- | --- | --- |
| `jev` (TypeSafe) | `jev-1.14.0` | [index](https://docs.typesafe.ai/llms.txt), [primitives](https://docs.typesafe.ai/go/primitives.md), [models](https://docs.typesafe.ai/go/models.md), [jaggedness](https://docs.typesafe.ai/go/jaggedness.md), [cookbooks](https://docs.typesafe.ai/go/cookbooks.md) |
| `liquid` (Liquid AI) | `d1.2-ultra`, `d1.2` | [decisions guide](https://docs.liquid.ai/api/guides/decisions.md), [d1.2 models](https://docs.liquid.ai/lfm/models/d1.md), [index](https://docs.liquid.ai/llms.txt) |
| `upstage` (Upstage Solar Decide) | `solar-decide`, `solar-decide-flash` | [System One API](https://console.upstage.ai/api/systemone.md) |
| `azure` (Microsoft-Decision-1) | your Foundry deployment | [Microsoft Learn](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision) |
| `local` (self-hosted: llama.cpp, laya-serve) | whatever the server runs | [llama.cpp decision models](https://huggingface.co/blog/ggml-org/decision-models-in-llamacpp), [laya-serve](https://github.com/NandhaKishorM/laya/blob/main/docs/http-api.md) |
| `custom` | your own | the endpoint's own docs |

Question types differ by model, and the client refuses a request the chosen model can't take
before sending (tool result kind `unsupported`). Jev takes noul, choice, score and box. Liquid
d1.2 and d1.2-ultra also take text, number, date, spans, boxes and `choice` with `multiple`. In
scripts, build questions with `system_one.noul / choice / score / box / question` rather than an
SDK.

Read the docs page for the question types you use. Providers support different answer types
(text, number, date, spans and box, for example), and their models have different weak spots.
A wording tuned on one model is a hypothesis on another, so re-check it on the cases you care
about after a switch. If you can't reach the live docs, say so and leave out details that depend
on the version instead of guessing.

For running an integration unattended (debounce, monotonic verdicts, label upserts, honest eval,
pairing with an LLM, cost estimates), see [`references/production-lessons.md`](references/production-lessons.md).

## Workflow

1. **Start from the decision logic.** Begin with what the application will show, select, change,
   or hand off. Sketch the truth table or rules that decide it, and list the inputs they need.
   Inputs that need an understanding of language or images make good questions. Arithmetic, dates,
   exact lookups, and policy usually belong in code. Aim for every question to feed the table, and
   give every combination of answers an outcome, including the case where a Noul lands between your
   thresholds. If code alone can already make the decision reliably, tell the user.
2. **Keep all question wording in one place.** Questions, options, criteria, and thresholds are the
   parts of an integration people audit and edit most. Keeping them together in one module makes
   that easier. [Design the state](#design-the-state) and
   [Write the questions](#write-the-questions) describe what tends to work.
3. **Probe the live API**: send test requests as described in
   [Test with the live API](#test-with-the-live-api). Use representative cases, hard cases, and
   negative cases. Keep going until the application behaves as intended.
4. **Integrate.** A few habits help here. Expose or log the exact request payload. When a call to
   the API fails, surface it as an error, not as an answer; for example, don't treat a failed call
   as a "no". Keep API keys on the server.

If the user's request is open-ended, offer the few directions from [Cookbooks](#cookbooks) that
best serve their goal, and recommend one. If the request is concrete, build it.

## Design the state

A useful check for any question is the **human test**: could a smart person, shown only this state
and this question, answer quickly by intuition? When a question fails the test, the fix is usually
in the state, not in the wording.

- **Give what a person would look at.** That means who sent each message, the full thread rather
  than a truncated last line, names rather than raw IDs or @-mention markup, and the item the
  question is about rather than the whole catalogue. State facts your code already knows, such as
  "all messages in `replies` were sent after the refund was issued", rather than leaving the model
  to work them out again.
- **Supply facts the model may lack**, such as what an internal product name or codename refers
  to.
- **Ensure every field in the state is relevant.** Irrelevant detail clutters the context and
  reduces accuracy. A field added for one question can sway the answer to another, and the model
  can read an empty list as a signal.
- **Be mindful when truncating.** Truncate long strings only when you need to, and check that the
  cut doesn't remove context the questions need.
- **Structure with named fields.** JSON objects with descriptive keys work better than a string of
  serialized JSON. They also let a question refer to each part by its path. Stable names such as
  `candidates.refund_policy` are easier to refer to than array positions.
- **Consider leaving out what no person could judge**, such as an unreadable crop or a distinction
  experts dispute. The model's answer there tends to be noise, and code will treat that noise as
  signal.

## Write the questions

Break complex judgments or decisions into their parts, and combine the answers in code with
weighted sums, boolean logic, thresholds, or other heuristics to reach the final decision. For
example, rather than asking "Is this fraud?" or "Is this spam?", ask the set of atomic questions
about what might make something fraud or spam. Each question tends to work best when it asks for
**one judgment** that a person could make at a glance.

- **Ask the concrete, observable thing.** Aim for something a person could point to: "Is a SQL
  query built by string concatenation here?" rather than "Are there SQL injection risks?".
- **One judgment per question; beware the "or".** Two conditions joined by "or" or "and" usually
  work better as two questions. Likewise, a list of rules usually works better as one question per
  rule.
- **Anchor intent to the goal.** When the judgment is about what someone wants, it helps to name
  their goal: "Which of these files does the user want copied?" rather than "Which of these names
  the main input?".
- **Name the subject directly.** "Where is the coffee mug in `photo`?" reads better than "Where is
  `target` in `photo`?" with the target defined somewhere else. Context that only one question
  needs, including an image, usually fits best in that question's instructions (the question text)
  or its criteria (the descriptions of its options, its levels, or what yes and no mean). Context
  that many questions share can go in the state once, and each question can refer to it by its
  exact path in backticks. When you ask the same question about many items, it usually works better
  to put each item into its own question than to give an ID the model has to look up in a shared
  list.
- **Each question is answered on its own.** Questions in a request can't see each other or each
  other's answers. Any context a question relies on belongs in the state or in that question.
- **Write plainly.** A question isn't an LLM prompt. Preambles, "consider X, Y, and Z" lists, and
  output-format instructions add noise. Descriptions of the options belong in the criteria, not in
  the question. Phrase the question so that a true answer means yes. Watch for double negatives,
  and for presuppositions such as "the next step".
- **Name the case that causes confusion.** If answers keep mixing up two outcomes, say in the
  criteria what separates them, using the specific case. For example, for "Is this a refund
  request?", note that a question about the refund policy is not a request. A vague exclusion such
  as "not other kinds of message" helps less, and can draw attention to the wrong answer.

### Criteria

- **Ask about the null case separately.** A Box always returns a location and a Choice always picks
  an option, even when nothing fits. Pair either one with a Noul in the same request that asks
  whether anything fits ("Is there a coffee mug in `photo`?", "Does `message` name any of our
  products?"), so code can tell when nothing does. On current models this companion Noul usually works
  better than a "none of the above" option.
- **Option names are sent to the model; question IDs are not.** Names that describe the content
  (`refund_request`, `shipping_delay`) help the model. Positional names (`A`, `left`, `option_1`)
  give it nothing meaningful to go on and can bias the answer.
- **Keep options distinct and concrete.** Wording that options share with each other, or with the
  input, can pull probability toward those options. An option that covers several meanings is
  often worth splitting, because its probability can't tell code which meaning applied. Direction
  and magnitude usually work better as separate questions, so that the answer to one doesn't get
  mixed into the other.
- **Describe each Score level as a situation.** Each level should make sense when read on its own:
  "The customer mentions a minor inconvenience" rather than "More upset than the previous level".
- **Describe a Noul's `false` criterion as a concrete situation**, such as "the package arrived on
  time", rather than as "not late".
- **Use a Noul per statement when more than one can be true.** A Choice picks one option, so a
  message that is both a refund request and a complaint forces it to split probability between the
  two. Separate Nouls let each one be true on its own.

## Compose requests

**Bundle questions that share state.** A handy heuristic: if two calls would send the same state
with different questions, they can likely be one call. Questions are cheap and run in parallel, and
the state is read and paid for once. See
[parallel questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md).

**Ask speculatively**, meaning ask a question before you know whether you'll need its answer. A
question that only matters in some cases can go in the same request as the question that
identifies the case. Ask "Is `order` a return request?" and "Which item in `order.items` is being
returned?" together, and have code read the second answer only when the first is yes. The second
question doesn't need an "if" clause, because code handles the condition. See
[speculative fan-out](https://docs.typesafe.ai/patterns/fan-out.md).

A second request is usually worth it when:

- code needs an answer to build the next state, fetch evidence, or choose the next options;
- a state field needed for one question measurably misleads another;
- different sets of questions need to be cached or versioned separately.

## Read the answers

### Confidence is rarely the gate

Naive implementations often use an answer's `confidence` as the check that decides whether code
acts. Confidence measures how concentrated an answer's probability distribution is, which is not
the same as how likely the answer is to be correct. Think about what the probabilities should look
like in your use case; another calculation over them may suit it better.

### Probabilities and thresholds

- **A probability is the likelihood that an answer is correct.** The model isn't a calculator for
  probability problems. Ask it for judgments, and do any math on odds or probabilities in code. A
  Noul near 0.5 usually means the state doesn't settle the question.
- **The top answer is a good default**: the Choice's top option, or the Score's position.
- **0.7 and 0.3 make good starting thresholds for a Noul**: above 0.7 reads as yes, below 0.3 as no,
  and the band between means the question isn't settled, which can get its own row in the truth
  table. Adjust them when the application calls for it, and be wary of over-fitting them to a
  handful of test cases.
- **Look at Score distributions.** The Score's position can get pulled toward the middle and hide
  two-peaked answers, so look at the level probabilities before deciding which value your code
  reads.

## Test with the live API

Sending test requests is the best way to check questions against real data. Ask the user first.
Agree on a budget (the plugin caps also apply), say what data will be sent and point out
anything personal or private, and name the provider that will receive it.

- Run `dry_run: true` first for a cost estimate.
- Start with a few representative cases, plus hard ones and some whose answer is "no" or
  "nothing fits".
- Compare wordings by sending each variant as a separate question in one request, over the
  same state.
- Compare providers by sending the same request with `provider` set to each one.
- Read individual answers, not only aggregates.
- Keep the exact request payload for each case so any result can be rerun.
- Check each change against cases you didn't use while tuning.

### When an answer looks wrong

Check these, in this order:

1. the payload as actually sent;
2. the state, against the human test;
3. the options and candidates: is the right answer among them?
4. the scope of the questions: can each one be broken down into smaller judgments?
5. the wording.

If a clear question with complete state still gets an answer you're confident is wrong, check the
known-limitations page for the model you're using (TypeSafe calls it jaggedness). It lists known
weak spots and how to work around them. If the behavior isn't listed, report the example to the
provider. In the meantime, work out an alternative approach with the user that avoids the weak
spot.

### Yellow flags

Typically, a good change is one that makes the definition clearer or improves the state. Check each
change on cases you didn't tune on. Wording written to produce a particular value is **prompt
gymnastics**, and it tends to break on new inputs and on the next model version. Some yellow flags:

- criteria that name specific test items, or that gain a clause for each failing case;
- caveats that explain away a model quirk;
- thresholds fitted to particular cases;
- tests that assert an exact probability;
- code that quietly overrides answers.

The structural fix is usually better state, a separate question, or code.

## Cookbooks

Each of these starting points combines questions to serve one goal. Ideas outside this list are
welcome.

- **Route and fill arguments.** One request identifies what the user is asking for and which
  values go in each argument. Code then calls the handler. See
  [function calling](https://docs.typesafe.ai/cookbooks/function_calling.md) and
  [intent routing](https://docs.typesafe.ai/patterns/intent-routing.md).
- **Select instead of generate.** Code finds candidate values or spans of text, the model picks
  the intended one, and code copies or normalizes it. See
  [value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md),
  [date extraction](https://docs.typesafe.ai/cookbooks/date_extraction_cookbook.md), and
  [structure recovery](https://docs.typesafe.ai/cookbooks/autoformat.md).
- **Find and judge evidence.** Retrieve candidates and ask how relevant each one is. See
  [line-by-line search](https://docs.typesafe.ai/cookbooks/semantic_find.md),
  [re-ranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md), and
  [classifying RAG passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages.md).
- **Turn answers into data.** Score each dimension once, then let code or users change the weights
  and views. If you have labeled outcomes, the answers can become features for a model. See
  [composite scoring](https://docs.typesafe.ai/patterns/composite-scoring.md) and
  [feature discovery](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md).
- **Verify and escalate.** Check claims or fields against their evidence, and send the cases that
  fail to a person or a reasoning model. See
  [citation checks](https://docs.typesafe.ai/cookbooks/citation_check.md) and
  [extraction cascades](https://docs.typesafe.ai/cookbooks/sde_cascade.md).

Providers keep adding cookbooks of tested patterns to their docs. It's a good idea to check the [cookbooks index](https://docs.typesafe.ai/go/cookbooks.md) for one
that fits the problem you're solving.
