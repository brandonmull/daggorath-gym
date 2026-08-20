# Plans — Structure and Conversation Extraction

Each plan folder holds two documents side by side: the plan and the conversation that led to it.

## Structure

- `plan.md` — the design spec: *what* we're building.
- `conversation.md` — the reasoning: *why*, in our own words.

## Conversation format

A `conversation.md` is organized into threads — one per distinct design question or insight, each headed `## <concept>`:

1. **`**From the conversation:**`** — the verbatim exchange, with the antecedents that make each statement read as a reply.
2. **The crux** — the single statement that frames the concept best, boxed off:
   ```
   > ### The Crux
   >
   > **Cline:** "…"
   ```
3. **`**Resolution:**`** — a one-line outcome.

## Rules — and the pushbacks that produced them

- **Quote in full; no ellipses, no paraphrasing.** An early draft trimmed statements to their punchlines and the record felt *"too under-representative"* — the middle statements are where the reasoning lives. The exact wording is what we return to later.
- **The perfect statement is the crown jewel; the reasoning is its setting.** We keep *"particular statements that frame concepts in just the right way"* most of all — but a statement is only perceived appropriately in the context of the reasoning that led up to it, so capture both. Nothing said should be lost: *"I don't want to lose that."*
- **Evidence-backed.** A clean synthesis is not enough on its own — *"the overall record needs to be evidence-backed by the exact conversation itself."* Ground every claim in the verbatim exchange, or it reads as paraphrase.
- **Antecedents, not summaries.** A statement is always a reply to something earlier: *"my statements are also in response to something that happened earlier."* A one-line note ("I had laid out the potentials and left strength out") *"helps minimally"* — show the actual prior exchange it was responding to.
- **The crux gets a box.** The most significant statement *"deserves visual emphasis somehow"* — a large `### The Crux` heading inside its own blockquote, load-bearing terms bolded.
- **Speaker attribution everywhere, including the crux** — on the statement itself (`**Cline:** "…"`), never in the crux heading.

## Extracting a conversation

When a plan predates this format, extract its `conversation.md` from the saved sessions:

1. **Read the saved conversation** for the module.
2. **Identify the threads** — the distinct questions and insights that shaped the plan.
3. **Trace each thread's chain** — who said what, in response to what.
4. **Write it** in the format above — quoting in full, marking the crux per thread.

## Status

| Module | Conversation |
|--------|-------------|
| reward, creatures, objects, sound, navigation, events | Extracted |
| state | Partial — the strength controversy only; the module's own design predates the conversation |
| commands | Extracted — factored action space and the invalid-command argument |
| screen | Missing — predates the conversation; extraction pending |
| perception | Started — act-first, line-of-sight gate, no-memory, and modal-perception threads recorded |
| curriculum | Not started — items gathered, structure pending |
| deployment | Extracted |

