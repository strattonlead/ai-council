# Setup

Read this when `check_setup.py` reports a problem, or when the user is configuring the
council for the first time.

## What the user needs

1. A running LiteLLM proxy that routes to at least two frontier providers.
2. A virtual key issued by that proxy (not the underlying provider keys).
3. Python 3.9+. No third-party packages — the scripts use the standard library only.

## The setup message to give the user

Give them this verbatim; do not run it on their behalf, and do not offer to accept the
key in the conversation.

> Run this in your own terminal:
>
> ```bash
> bash scripts/init_config.sh
> ```
>
> It asks for the proxy URL and your key. The key is entered with a hidden prompt and
> written to `~/.ai-council/config.env` with mode 600, so it never passes through the
> model. When it finishes, tell me and I'll verify the connection.

Then run `python3 scripts/check_setup.py` yourself — it confirms the proxy answers and
prints only a fingerprint of the key.

## Manual alternative

If they prefer to write the file by hand:

```bash
mkdir -p ~/.ai-council && chmod 700 ~/.ai-council
umask 177 && ${EDITOR:-nano} ~/.ai-council/config.env
```

```
AI_COUNCIL_BASE_URL=http://localhost:4000
AI_COUNCIL_API_KEY=sk-...
AI_COUNCIL_MODELS=gpt-5,gemini-2.5-pro,deepseek-chat,claude-sonnet-4-6
AI_COUNCIL_TIMEOUT=180
```

Environment variables of the same names override the file — useful in CI, but note that
anything in the environment can end up in an agent's context if a command prints it.
The file is the safer default.

## Minimal LiteLLM proxy

For a user who doesn't have one yet. `config.yaml`:

```yaml
model_list:
  - model_name: gpt-5
    litellm_params:
      model: openai/gpt-5
      api_key: os.environ/OPENAI_API_KEY
  - model_name: gemini-2.5-pro
    litellm_params:
      model: gemini/gemini-2.5-pro
      api_key: os.environ/GEMINI_API_KEY
  - model_name: deepseek-chat
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
  - model_name: claude-sonnet-4-6
    litellm_params:
      model: anthropic/claude-sonnet-4-6
      api_key: os.environ/ANTHROPIC_API_KEY

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

```bash
pip install 'litellm[proxy]'
litellm --config config.yaml --port 4000
```

Provider keys live in the proxy's environment. The council only ever sees the proxy key,
which is the point: rotating it revokes the skill's access without touching anything else.

Model names in `AI_COUNCIL_MODELS` must match `model_name` in the proxy config, not the
provider's own identifier.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `NOT CONFIGURED` | No config file, no env vars | Run `init_config.sh` |
| Connection refused | Proxy not running, wrong port | Start it; confirm the port |
| `HTTP 401` | Wrong or revoked virtual key | Reissue in LiteLLM, rerun setup |
| `HTTP 404` on a model | Name not in the proxy's `model_list` | Fix `AI_COUNCIL_MODELS` |
| `HTTP 429` | Provider rate limit | Fewer models, or retry later |
| One member always absent | That provider's upstream key is missing or out of credit | Check the proxy's own logs |
| Timeouts on reasoning models | 180s default too low | Raise `--timeout` |

The proxy's logs are the right place to debug provider-level failures. Suggest the user
check them rather than trying to diagnose from the council's error strings, which are
deliberately redacted.

## Security notes worth telling the user

- The protection here is procedural plus script-level redaction, not a hard sandbox. An
  agent with shell access *could* read the config file; the skill instructs it not to, and
  the scripts are built so it never needs to.
- Don't put the key in a shell variable that a later command might echo.
- Use a scoped LiteLLM virtual key with a spend limit rather than the master key.
- If a key is ever pasted into a chat, treat it as compromised and rotate it.
