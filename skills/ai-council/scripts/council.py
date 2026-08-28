#!/usr/bin/env python3
"""Run a multi-round debate across several models behind a LiteLLM proxy.

Round 1  each member states a position on the topic, independently.
Round 2+ each member sees the other positions (anonymised as "Member A/B/C") and
         must engage with them: concede, refute, or sharpen.

The transcript is written to a markdown file. The synthesis is intentionally NOT
produced here — the calling agent writes it from the transcript.

Standard library only. The API key is loaded by _config and redacted from any
error text this script emits.
"""

import argparse
import json
import sys
import textwrap
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402

LETTERS = "ABCDEFGHIJKL"

OPENING = """You are a member of an AI council convened to examine one question rigorously.

Question:
{topic}
{context}
{role}
Give your position in under 350 words:
1. Your answer, stated plainly in the first sentence. No hedging preamble.
2. The two or three reasons that actually drive it.
3. The strongest argument against your own position, and why you still hold it.
4. What evidence or fact would change your mind.

Other members answer the same question independently. You will see their positions
next round. Write to be argued with, not to be agreed with."""

CRITIQUE = """You are a member of an AI council. This is round {round_no} on:

{topic}
{context}
Your position last round:
---
{own}
---

The other members said:
{peers}

In under 350 words:
1. Name the strongest point made by another member that you had missed or underrated.
2. Name the point you think is clearly wrong, and say why.
3. State your position now — unchanged, revised, or reversed. If it changed, say what
   changed it. If it did not, say what the others failed to establish.

Changing your mind on a good argument is the point of the exercise, not a loss.
Do not converge for the sake of appearing agreeable."""


class Member:
    def __init__(self, model: str, letter: str, role: str = ""):
        self.model = model
        self.letter = letter
        self.role = role
        self.rounds = []      # list[str] — one statement per round
        self.errors = []      # list[str]

    @property
    def absent(self) -> bool:
        return not any(self.rounds)

    @property
    def last(self) -> str:
        for text in reversed(self.rounds):
            if text:
                return text
        return ""


def complete(base_url, key, model, prompt, temperature, max_tokens, timeout, retries=2):
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    last_err = ""
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip(), None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            last_err = _config.redact(f"HTTP {exc.code}: {detail}")
            if exc.code in (400, 401, 403, 404):
                break  # not worth retrying
        except Exception as exc:  # noqa: BLE001
            last_err = _config.redact(exc)
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return None, last_err


def run_round(members, prompts, cfg, args):
    """Call every member in parallel for one round."""
    key = cfg["AI_COUNCIL_API_KEY"]
    base = cfg["AI_COUNCIL_BASE_URL"]

    def call(member):
        text, err = complete(
            base,
            key,
            member.model,
            prompts[member.letter],
            args.temperature,
            args.max_tokens,
            args.timeout,
        )
        return member, text, err

    with ThreadPoolExecutor(max_workers=max(1, len(members))) as pool:
        for member, text, err in pool.map(call, members):
            if text:
                member.rounds.append(text)
                print(f"  [{member.letter}] {member.model}: {len(text.split())} words")
            else:
                member.rounds.append("")
                member.errors.append(err or "no response")
                print(f"  [{member.letter}] {member.model}: FAILED — {err}")


def peer_block(members, current):
    parts = []
    for m in members:
        if m is current or not m.last:
            continue
        parts.append(f"### Member {m.letter}\n{m.last}")
    return "\n\n".join(parts) if parts else "(no other member responded)"


def write_markdown(path, topic, members, rounds, context, started):
    lines = [
        "# AI Council transcript",
        "",
        f"- Convened: {started.isoformat(timespec='seconds')}",
        f"- Rounds: {rounds}",
        "- Members:",
    ]
    for m in members:
        state = "absent" if m.absent else "participated"
        lines.append(f"  - Member {m.letter} = `{m.model}` ({state})")
    lines += ["", "## Question", "", topic, ""]
    if context:
        lines += ["## Shared context", "", "```", context.strip(), "```", ""]

    for r in range(rounds):
        lines += [f"## Round {r + 1}" + (" — opening positions" if r == 0 else " — critique"), ""]
        for m in members:
            text = m.rounds[r] if r < len(m.rounds) else ""
            lines += [f"### Member {m.letter} · `{m.model}`", ""]
            lines += [text if text else "_(no response this round)_", ""]

    failed = [(m, m.errors) for m in members if m.errors]
    if failed:
        lines += ["## Incidents", ""]
        for m, errs in failed:
            for e in errs:
                lines.append(f"- Member {m.letter} (`{m.model}`): {e}")
        lines.append("")

    lines += [
        "---",
        "",
        "_Synthesis is not included here by design — it is written by the orchestrating",
        "agent from this transcript._",
        "",
    ]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Convene an AI council over a LiteLLM proxy.")
    p.add_argument("--topic", required=True, help="The question to debate.")
    p.add_argument("--models", help="Comma-separated model names (default: configured roster).")
    p.add_argument("--rounds", type=int, default=2, help="1 = openings only, 2 = one critique round.")
    p.add_argument("--context-file", help="File whose contents every member sees.")
    p.add_argument("--role-file", help="JSON mapping model name -> stance to assign.")
    p.add_argument("--out", default="council-transcript.md", help="Markdown transcript path.")
    p.add_argument("--json", dest="json_out", action="store_true", help="Also write a .json transcript.")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--max-tokens", type=int, default=1200)
    p.add_argument("--timeout", type=float, default=180.0)
    args = p.parse_args()

    try:
        cfg = _config.load()
    except _config.ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _config.register_secret(cfg["AI_COUNCIL_API_KEY"])

    roster = [m.strip() for m in args.models.split(",")] if args.models else _config.models(cfg)
    roster = [m for m in roster if m]
    if len(roster) < 2:
        print("error: a council needs at least 2 models (--models or AI_COUNCIL_MODELS).", file=sys.stderr)
        return 1
    if args.rounds < 1:
        print("error: --rounds must be at least 1.", file=sys.stderr)
        return 1

    roles = {}
    if args.role_file:
        roles = json.loads(Path(args.role_file).read_text(encoding="utf-8"))

    context = ""
    if args.context_file:
        context = Path(args.context_file).read_text(encoding="utf-8")

    members = [Member(m, LETTERS[i], roles.get(m, "")) for i, m in enumerate(roster)]
    started = datetime.now(timezone.utc)
    ctx_block = f"\nShared context:\n---\n{context.strip()}\n---\n" if context else "\n"

    print(f"Convening {len(members)} members for {args.rounds} round(s).")

    print("\nRound 1 — opening positions")
    prompts = {
        m.letter: OPENING.format(
            topic=args.topic.strip(),
            context=ctx_block,
            role=f"\nYour assigned stance: {m.role}\n" if m.role else "",
        )
        for m in members
    }
    run_round(members, prompts, cfg, args)

    if all(m.absent for m in members):
        print("\nerror: no member responded. Run check_setup.py.", file=sys.stderr)
        return 2

    for r in range(2, args.rounds + 1):
        print(f"\nRound {r} — critique")
        prompts = {
            m.letter: CRITIQUE.format(
                round_no=r,
                topic=args.topic.strip(),
                context=ctx_block,
                own=m.last or "(you did not respond last round)",
                peers=peer_block(members, m),
            )
            for m in members
        }
        run_round(members, prompts, cfg, args)

    write_markdown(args.out, args.topic.strip(), members, args.rounds, context, started)
    print(f"\nTranscript written to {args.out}")

    if args.json_out:
        jpath = Path(args.out).with_suffix(".json")
        jpath.write_text(
            json.dumps(
                {
                    "topic": args.topic.strip(),
                    "convened": started.isoformat(),
                    "rounds": args.rounds,
                    "members": [
                        {
                            "letter": m.letter,
                            "model": m.model,
                            "role": m.role,
                            "statements": m.rounds,
                            "errors": m.errors,
                        }
                        for m in members
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"JSON written to {jpath}")

    absent = [m.model for m in members if m.absent]
    if absent:
        print(f"note: absent members (report this in the synthesis): {', '.join(absent)}")
    print(textwrap.dedent("""
        Next: read the transcript and write the synthesis yourself
        (Verdict / Agreed / Split / What changed / My read).
    """).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
