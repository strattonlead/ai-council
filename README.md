# ai-council

A Claude Agent Skill that puts a question to several frontier models through one LiteLLM
proxy, makes them argue over multiple rounds, and reports what survived the argument.

Credentials live in `~/.ai-council/config.env` (mode 600) and are never read into the
model's context — see `skills/ai-council/references/setup.md`.

## Install

**Claude Code / Cowork, as a plugin**

```
/plugin marketplace add <your-org>/<this-repo>
/plugin install ai-council@createif-skills
```

**Claude Code, without a repo**

```bash
cp -r skills/ai-council ~/.claude/skills/     # personal, all projects
cp -r skills/ai-council .claude/skills/       # project-scoped, commit with the repo
```

**claude.ai / Claude Desktop**

Zip the `skills/ai-council` folder so that `ai-council/SKILL.md` sits at the archive root,
then upload it under Settings → Capabilities → Skills. Note that the claude.ai skill
sandbox may have no outbound network access, in which case the skill cannot reach your
proxy — it is intended primarily for Claude Code, Cowork, and Desktop.

## Setup

```bash
bash skills/ai-council/scripts/init_config.sh   # run this yourself; key entry is hidden
python3 skills/ai-council/scripts/check_setup.py
```

## Usage

Ask naturally — "get the council's take on whether we should move to Kafka" — or run it
directly:

```bash
python3 skills/ai-council/scripts/council.py \
  --topic "Should we migrate the event pipeline to Kafka?" \
  --rounds 2 --out council.md
```

## Requirements

Python 3.9+, standard library only. A reachable LiteLLM proxy serving at least two models.
