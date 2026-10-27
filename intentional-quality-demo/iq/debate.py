"""AutoGen's job: decide whether a surviving mutant is a real gap or an equivalent mutant.

Two modes:
  offline (default) - a deterministic "equivalence court": the evidence comes from
                      differential testing (original vs mutant over thousands of inputs),
                      and the three roles state that evidence. No LLM, no network.
  live              - three AutoGen AgentChat agents (Gap Hunter, Equivalence Advocate,
                      Judge) argue over the same evidence with a real LLM.

In both modes the evidence has the last word: an agent cannot declare a mutant
equivalent when a concrete counterexample exists. Agents decide, within limits we set.
"""
import ast
import inspect
import os

from .runner import load_module

ROLES = ("Gap Hunter", "Equivalence Advocate", "Judge")


def _constants(fn_source):
    nums = set()
    for node in ast.walk(ast.parse(fn_source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            nums.add(node.value)
    return nums


def _call(fn, args):
    try:
        return ("ok", fn(*args))
    except Exception as e:
        return ("raises", type(e).__name__)


def differential_search(original_src, mutant):
    """Compare original vs mutant on many inputs. Return evidence for the debate."""
    orig_mod, mut_mod = load_module(original_src), load_module(mutant.source)
    f_orig, f_mut = getattr(orig_mod, mutant.function), getattr(mut_mod, mutant.function)
    n_params = len(inspect.signature(f_orig).parameters)
    fn_node = next(n for n in ast.parse(original_src).body
                   if isinstance(n, ast.FunctionDef) and n.name == mutant.function)
    consts = _constants(ast.get_source_segment(original_src, fn_node))
    numeric = set(range(-5, 20001))
    for c in consts:
        for k in (1, 100):
            for d in (-0.01, 0, 0.01):
                numeric.add(round(c * k + d, 2))
    extras = [(True,), (False,)] if n_params == 2 else [()]
    diffs, searched = [], 0
    for x in sorted(numeric):
        for e in extras:
            args = (x, *e)
            searched += 1
            a, b = _call(f_orig, args), _call(f_mut, args)
            if a != b:
                diffs.append((args, a, b))
    if not diffs:
        return {"verdict": "EQUIVALENT", "searched": searched, "counterexample": False,
                "input": None, "original": None, "mutant": None}

    # prefer the input sitting exactly on a boundary constant: that's the test a human would write
    def closeness(d):
        x = d[0][0]
        return min([abs(x - c) for c in consts] + [abs(x - c * 100) for c in consts] + [abs(x)])
    args, a, b = sorted(diffs, key=lambda d: (closeness(d), abs(d[0][0])))[0]
    return {"verdict": "REAL_GAP", "searched": searched, "counterexample": True, "input": args,
            "original": _fmt(a), "mutant": _fmt(b), "n_diffs": len(diffs)}


def _fmt(r):
    kind, v = r
    return f"returns {v!r}" if kind == "ok" else f"raises {v}"


def call_str(mutant, args):
    return f"{mutant.function}({', '.join(repr(a) for a in args)})"


def offline_transcript(mutant, ev):
    """The three roles, stating the computed evidence."""
    where = f"line {mutant.line}: `{mutant.original_line}`  became  `{mutant.mutated_line}`"
    if ev["verdict"] == "REAL_GAP":
        call = call_str(mutant, ev["input"])
        return [
            ("Gap Hunter", f"The mutant changes {where}. At {call} the original {ev['original']} "
                           f"but the mutant {ev['mutant']}. Our suite never checks that input. That's a real gap."),
            ("Equivalence Advocate", f"I looked for a reason they're the same. There isn't one: they differ on "
                                     f"{ev['n_diffs']} input(s) out of {ev['searched']:,} tried. I concede."),
            ("Judge", f"VERDICT: REAL_GAP. Counterexample {call}. Send it to the Test Writer."),
        ]
    return [
        ("Gap Hunter", f"The mutant changes {where}. Boundaries are where bugs live, so I suspect a gap."),
        ("Equivalence Advocate", "Look at what the branch does. When the compared value equals the boundary, "
                                 "the original skips the assignment and the mutant performs it, but both leave the same value. "
                                 "No input can tell them apart."),
        ("Judge", f"VERDICT: EQUIVALENT. Searched {ev['searched']:,} inputs, found no difference. "
                  "Exclude it from the score; no test can kill it."),
    ]


# ------------------------------------------------------------------ live mode (AutoGen + LLM)

def _model_client():
    provider = os.environ.get("DEMO_PROVIDER", "anthropic").lower()
    model = os.environ.get("DEMO_MODEL", "claude-sonnet-5-5" if provider == "anthropic" else "gpt-4o")
    info = {"vision": False, "function_calling": True, "json_output": False,
            "family": "unknown", "structured_output": False}
    if provider == "openai":
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        return OpenAIChatCompletionClient(model=model, model_info=info)
    from .llm_client import ClaudeClient  # see llm_client.py for why not autogen-ext's client
    return ClaudeClient(model=model)


async def live_transcript(mutant, ev):
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
    from autogen_agentchat.teams import RoundRobinGroupChat

    client = _model_client()
    style = "Reply in at most 2 short sentences. Plain text, no markdown."
    hunter = AssistantAgent("Gap_Hunter", client, system_message=
        "You argue that a surviving mutant reveals a real gap in the test suite. Cite concrete inputs. " + style)
    advocate = AssistantAgent("Equivalence_Advocate", client, system_message=
        "You argue the mutant may be equivalent (no input can distinguish it), but you concede honestly "
        "when the evidence shows a concrete differing input. " + style)
    judge = AssistantAgent("Judge", client, system_message=
        "You decide. End with exactly 'VERDICT: REAL_GAP' or 'VERDICT: EQUIVALENT'. "
        "If a concrete counterexample exists, the mutant cannot be equivalent. " + style)
    evidence = (f"Counterexample: at {call_str(mutant, ev['input'])} the original {ev['original']}, the mutant {ev['mutant']}."
                if ev["counterexample"] else
                f"Differential testing found no differing input across {ev['searched']:,} inputs.")
    task = (f"Function `{mutant.function}`, line {mutant.line}. Original: `{mutant.original_line}`. "
            f"Mutant: `{mutant.mutated_line}`. All existing tests still pass on the mutant. {evidence} "
            "Is this a real gap in the tests, or an equivalent mutant?")
    team = RoundRobinGroupChat([hunter, advocate, judge],
                               termination_condition=TextMentionTermination("VERDICT:") | MaxMessageTermination(7))
    try:
        result = await team.run(task=task)
    finally:
        await client.close()
    names = {"Gap_Hunter": "Gap Hunter", "Equivalence_Advocate": "Equivalence Advocate", "Judge": "Judge"}
    return [(names.get(m.source, m.source), str(m.content)) for m in result.messages if m.source != "user"]


def verdict_from(transcript):
    for _, text in reversed(transcript):
        if "VERDICT: EQUIVALENT" in text.upper():
            return "EQUIVALENT"
        if "VERDICT: REAL_GAP" in text.upper() or "VERDICT: REAL GAP" in text.upper():
            return "REAL_GAP"
    return None


def debate(original_src, mutant, live=False):
    """Return (verdict, evidence, transcript, note). The evidence always has the last word."""
    ev = differential_search(original_src, mutant)
    note = ""
    if live:
        import asyncio
        import logging
        for name in ("autogen_core", "autogen_agentchat", "httpx", "anthropic", "asyncio"):
            logging.getLogger(name).setLevel(logging.CRITICAL)  # keep tracebacks off the stage screen
        try:
            transcript = asyncio.run(live_transcript(mutant, ev))
        except Exception as e:
            transcript = offline_transcript(mutant, ev)
            note = f"live debate unavailable ({type(e).__name__}); used offline court"
        llm_verdict = verdict_from(transcript)
        if llm_verdict and llm_verdict != ev["verdict"]:
            note = (f"Guardrail: agents said {llm_verdict}, evidence says {ev['verdict']}. Evidence wins.")
    else:
        transcript = offline_transcript(mutant, ev)
    return ev["verdict"], ev, transcript, note
