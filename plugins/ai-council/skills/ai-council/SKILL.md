---
name: ai-council
description: Convene an "AI Council" — put a question to several frontier models (GPT, Gemini, DeepSeek, Claude and others) through a LiteLLM proxy, let them debate it over multiple rounds, then synthesize where they agree and where they genuinely disagree. Use this skill whenever the user wants a second (or third, or fourth) opinion from other models, asks to "ask the council", "ask the other models", "run a panel/debate/roundtable", wants cross-model consensus on a decision, or wants to know whether a claim holds up outside one model's perspective — even if they never say the word "council". Also use it when setting up, configuring, or troubleshooting the LiteLLM endpoint and credentials this skill depends on.
---

# AI Council

Ask a question to several frontier models at once, make them argue with each other,
and report what survived the argument.

Single-model answers hide their own blind spots. A council is useful precisely when the
question is contested, when one model's confidence is suspicious, or when the cost of a
wrong call is high enough to justify paying for four opinions instead of one.

## Architecture

All models are reached through **one LiteLLM proxy** speaking the OpenAI-compatible
`/v1/chat/completions` API. The skill never talks to OpenAI, Google or DeepSeek directly —
it only knows a base URL, an API key, and a list of model names the proxy routes.

```
skill  →  scripts/council.py  →  LiteLLM proxy  →  {gpt-*, gemini-*, deepseek-*, claude-*}
```

The debate is orchestrated by the script; **the final synthesis is written by you**, in the
conversation, from the transcript. Don't spend another API call on the summary.

## Credentials — read this before anything else

The base URL and API key live in a config file the user owns:

```
~/.ai-council/config.env      (mode 600)
```

**Never read, print, echo, cat, grep, or otherwise pull the contents of that file into the
conversation.** The whole point of the setup flow is that the key reaches the proxy without
ever entering a model's context — yours included. If it lands in the transcript, it is
burned and has to be rotated.

Concretely:
- To check configuration, run `scripts/check_setup.py`. It reports presence, host and a
  short non-reversible fingerprint. It never prints the key.
- To create or change the config, tell the user to run `scripts/init_config.sh`
  **themselves, in their own terminal**. It reads the key with a hidden prompt. Do not run
  it for them and do not offer to take the key in chat.
- If a user pastes a key into the conversation anyway, say plainly that it is now exposed
  and should be rotated, then continue with the file-based flow.
- `council.py` redacts the key from its own error output. Don't defeat that by adding
  `set -x`, `curl -v`, or by dumping environment variables.

## Workflow

### 0. Locate the scripts

The working directory is the user's project, not this skill, so relative paths will not
resolve. Determine the skill directory once at the start of a session and reuse it:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:-}/skills/ai-council" \
         "$PWD/.claude/skills/ai-council" \
         "$HOME/.claude/skills/ai-council"; do
  [ -f "$d/SKILL.md" ] && { echo "SKILL_DIR=$d"; break; }
done
```

Every `scripts/...` path below is relative to that directory. Use it explicitly:
`python3 "$SKILL_DIR/scripts/check_setup.py"`.

### 1. Check setup (always, before the first call in a session)

```bash
python3 "$SKILL_DIR/scripts/check_setup.py"
```

Possible outcomes:
- **Ready** — it lists the configured models and confirms the proxy answered. Proceed.
- **Not configured** — stop here. Do not run `council.py`, do not ask for the key, do not
  improvise a workaround. Tell the user the council isn't initialised yet and give them
  exactly this, with `$SKILL_DIR` expanded to the real path:

  > Run this in your own terminal — it asks for your LiteLLM URL and key, and the key
  > input is hidden so it never reaches me:
  >
  > ```bash
  > bash <SKILL_DIR>/scripts/init_config.sh
  > ```
  >
  > Tell me when it's done and I'll verify the connection.

  Then wait. When they confirm, re-run `check_setup.py`. Full details and the manual
  alternative are in `references/setup.md`.
- **Configured but unreachable** — see the troubleshooting table in `references/setup.md`.
  Common causes are a stopped proxy, a wrong port, or an expired key.

### 2. Sharpen the question

A council debating a vague prompt produces four vague essays. Before spending the calls,
make sure the topic is something models can actually disagree about: a decision, a trade-off,
a claim, an architecture choice, a strategy. If the user's question is purely factual
("what year did X happen"), say so — a council adds cost and no signal there.

Keep the topic to a few sentences. If there is context the models need (a code snippet, a
constraint, a spec), pass it with `--context-file`; don't cram it into the topic string.

### 3. Run the debate

```bash
python3 "$SKILL_DIR/scripts/council.py" \
  --topic "Should we migrate the TMS event pipeline from Postgres LISTEN/NOTIFY to Kafka?" \
  --rounds 2 \
  --out /tmp/council-tms.md
```

Useful flags:
- `--models gpt-5,gemini-2.5-pro,deepseek-chat` — override the configured roster.
- `--rounds N` — 1 = opening statements only, 2 = one critique round (default), 3+ for
  genuinely contested questions. Cost scales as models × rounds.
- `--context-file path` — extra material every member sees.
- `--role-file path` — assign specific stances (see `references/protocol.md`).
- `--temperature`, `--max-tokens`, `--timeout` — per-call tuning.
- `--json` — also write a machine-readable transcript next to the markdown.

The script prints progress per member and writes the full transcript to `--out`.
A member that errors or times out is marked as absent rather than failing the whole run —
say so in the synthesis rather than quietly dropping it.

### 4. Synthesize

Read the transcript and write the answer yourself. Use this structure:

```markdown
## Verdict
[2-4 sentences: what the council converged on, or that it didn't]

## Where they agreed
[Only genuine agreement. Two models restating the same platitude is not a finding.]

## Where they split
[The actual disagreement, with who held which position and the reasoning behind it.
This is the most valuable part of the output — do not smooth it over.]

## What changed between rounds
[Who updated, on what argument. A model that abandoned its position under pressure is
informative; so is one that didn't budge.]

## My read
[Your own assessment, explicitly labelled as yours. You are a council member with the
advantage of having read everyone. Disagree with the majority if you think it's wrong.]
```

Two failure modes to avoid:
- **False consensus.** Models trained on overlapping data agree for reasons that have
  nothing to do with the question being settled. Say when agreement is cheap.
- **Laundering.** Don't present the council's confidence as your own. Attribute positions.

## Cost and honesty

n models × r rounds means n×r completions, each carrying the previous round's text. A
4-model, 3-round debate on a long context is not cheap. Mention it before running anything
above the default, and don't run a council when a single answer would do.
