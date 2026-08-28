# Debate protocol

Read this when tuning how a council runs — assigning stances, choosing round counts, or
deciding whether a council is the right tool at all.

## What the script does

**Round 1.** Every member answers the topic independently, with no knowledge of the others.
Each is asked for a plain answer, the reasons behind it, the strongest counter-argument,
and a falsifier. Independence matters: if they saw each other first, you would measure
conformity rather than judgement.

**Round 2+.** Each member sees the others' latest statements, anonymised as "Member A/B/C",
and must name the best point they missed, the point they think is wrong, and their position
now. Anonymising suppresses brand deference — models are noticeably more willing to
contradict "Member B" than "GPT-5".

**Synthesis.** Not done by the script. The orchestrating agent reads the transcript and
writes it, which is both cheaper and better: it has the full transcript and can add its own
view as a labelled participant.

## Round counts

- **1 round** — you want independent samples, not a debate. Good for "is there an angle
  I've missed", brainstorming, or checking whether a claim is contested at all.
- **2 rounds** (default) — the useful case. One critique pass is where positions actually
  move.
- **3+ rounds** — for genuinely contested questions. Watch for the failure mode: rounds 3
  and 4 often produce politeness convergence rather than new argument. If round 3 adds no
  new reasoning, say so instead of padding the synthesis with it.

## Assigning stances

By default every member answers freely. For a decision where you want the case for each
option argued properly, use `--role-file` with a JSON map:

```json
{
  "gpt-5": "Argue for staying on the current architecture. Steelman it; do not concede early.",
  "gemini-2.5-pro": "Argue for the migration. Focus on what breaks if we don't.",
  "deepseek-chat": "You are the sceptic. Attack the assumptions both sides share.",
  "claude-sonnet-4-6": "You are the operator. Judge purely on what this costs to run at 3am."
}
```

Assigned stances produce sharper arguments but not honest positions — an adversarial
council tells you how strong each case *can* be made, not which one is right. Say which
mode was used in the synthesis; readers will otherwise mistake advocacy for belief.

The "shared assumption" role is the highest-value one. Frontier models are trained on
overlapping data and often agree because they share a premise, not because the premise is
sound. Assigning one member to attack the premise is the cheapest way to surface that.

## Reading the transcript

Signals worth reporting:

- **Position changed under a specific argument** — the most informative outcome in the
  whole exercise. Name the argument.
- **Held position and explained what the others failed to establish** — nearly as good.
- **Agreement on the answer, disagreement on the reasoning** — usually means the question
  was underspecified, not that it's settled.
- **Immediate unanimity in round 1** — either genuinely settled, or the topic invited a
  consensus answer. Check whether any member offered a real falsifier; if none did, treat
  the agreement as weak evidence.
- **Convergence only after round 2** — check whether it was argument or accommodation.
  Models drift toward agreement when shown peer text, which is a known bias, not a finding.

## When not to convene a council

- Purely factual questions with a checkable answer — search instead.
- Questions about the user's own private context that the other models can't see. Anything
  useful they say is guesswork.
- Anything where confidential material would go into the prompt. The topic and context are
  sent to every configured provider. If the material shouldn't leave the building, don't
  convene — say why.
- Cases where the user has already decided and wants agreement. A council will supply it,
  which makes it worse than useless.
