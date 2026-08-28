# strattonlead skills

Claude Code plugin marketplace.

## Install

```
/plugin marketplace add strattonlead/ai-counsil
/plugin install ai-council@strattonlead
```

If Claude Code reports `Run /reload-plugins to activate.`, run that to make the skill
available in the current session.

## Plugins

### ai-council

Puts a question to several frontier models through one LiteLLM proxy, makes them argue
over multiple rounds, and reports what survived the argument.

After installing, set up the proxy credentials once — run this yourself, the key input is
hidden so it never reaches the model:

```bash
bash ~/.claude/plugins/strattonlead/ai-council/skills/ai-council/scripts/init_config.sh
```

Or just ask Claude to check the council setup; it will locate the script and hand you the
exact command.

Credentials are stored in `~/.ai-council/config.env` (mode 600), outside this repository.
Details in `plugins/ai-council/skills/ai-council/references/setup.md`.

Requires Python 3.9+ (standard library only) and a reachable LiteLLM proxy serving at
least two models.

## Adding another plugin

1. Create `plugins/<name>/` with its own `.claude-plugin/plugin.json` and `skills/<name>/`.
2. Add an entry to `.claude-plugin/marketplace.json` with `"source": "./plugins/<name>"`.
3. Bump that plugin's own `version`; the marketplace name stays `strattonlead`.
