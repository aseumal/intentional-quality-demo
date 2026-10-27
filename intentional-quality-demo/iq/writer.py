"""CrewAI's job: write the test that kills a real-gap mutant.

offline (default) - a deterministic Test Writer: it takes the Judge's counterexample,
                    asks the ORIGINAL code for the expected answer, and writes the assert.
live              - a CrewAI Test Writer agent drafts the test with a real LLM.

Either way, a drafted test is only accepted if it passes on the original code and
fails on the mutant. Otherwise it is rejected and the deterministic writer is used.
"""
import os
import re

from .runner import load_module, run_suite


def _name(mutant, args):
    parts = []
    for a in args:
        if isinstance(a, bool):
            parts.append("metro" if a else "province")
        else:
            parts.append(str(a).replace(".", "_").replace("-", "neg"))
    return f"test_{mutant.function}_at_{'_'.join(parts)}"


def offline_test(original_src, mutant, ev):
    args = ev["input"]
    expected = getattr(load_module(original_src), mutant.function)(*args)
    call = f"{mutant.function}({', '.join(repr(a) for a in args)})"
    return (f"from pricing import {mutant.function}\n\n\n"
            f"def {_name(mutant, args)}():\n"
            f"    assert {call} == {expected!r}\n")


def validate(test_src, original_src, mutant, existing_tests):
    """A test is accepted only if it is green on the original and red on the mutant."""
    try:
        on_original = run_suite(original_src, [test_src])
        on_mutant = run_suite(mutant.source, [test_src])
    except Exception as e:
        return False, f"does not run ({type(e).__name__})"
    if not on_original.passed or on_original.failed:
        return False, "fails on the original code"
    if not on_mutant.failed:
        return False, "does not kill the mutant"
    return True, "green on original, red on mutant"


def live_test(original_src, mutant, ev):
    import logging
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    for name in ("crewai", "LiteLLM", "httpx", "anthropic"):
        logging.getLogger(name).setLevel(logging.ERROR)  # keep warnings off the stage screen
    from crewai import Agent, Crew, LLM, Task

    provider = os.environ.get("DEMO_PROVIDER", "anthropic").lower()
    model = os.environ.get("DEMO_MODEL", "claude-sonnet-5-5" if provider == "anthropic" else "gpt-4o")
    llm = LLM(model=f"{provider}/{model}")  # no temperature: current Anthropic API rejects it
    writer = Agent(
        role="Test Writer",
        goal="Write one small Python unit test that kills a surviving mutant",
        backstory="A meticulous QA engineer from Manila who writes the boundary tests other people forget.",
        llm=llm, allow_delegation=False, verbose=False)
    call = f"{mutant.function}({', '.join(repr(a) for a in ev['input'])})"
    task = Task(
        description=(
            f"Function `{mutant.function}` is imported with `from pricing import {mutant.function}`.\n"
            f"Original line: `{mutant.original_line}`. Mutated line: `{mutant.mutated_line}`.\n"
            f"Counterexample from the Judge: at {call} the original {ev['original']} and the mutant {ev['mutant']}.\n"
            f"Start with `from pricing import {mutant.function}`, then write ONE test function named "
            "test_<something> using a plain assert. No markdown fences."),
        expected_output="Only the Python source of one test function.",
        agent=writer)
    out = str(Crew(agents=[writer], tasks=[task], verbose=False).kickoff())
    code = re.sub(r"^```(?:python)?|```$", "", out.strip(), flags=re.M).strip() + "\n"
    if f"import {mutant.function}" not in code:
        code = f"from pricing import {mutant.function}\n\n\n" + code
    return code


def write_test(original_src, mutant, ev, existing_tests, live=False):
    """Return (test_source, accepted_note, used_live)."""
    if live:
        try:
            draft = live_test(original_src, mutant, ev)
            ok, why = validate(draft, original_src, mutant, existing_tests)
            if ok:
                return draft, why, True
            fallback = offline_test(original_src, mutant, ev)
            return fallback, f"Guardrail: agent's draft rejected ({why}); deterministic writer used", False
        except Exception as e:
            fallback = offline_test(original_src, mutant, ev)
            return fallback, f"live writer unavailable ({type(e).__name__}); deterministic writer used", False
    draft = offline_test(original_src, mutant, ev)
    ok, why = validate(draft, original_src, mutant, existing_tests)
    return draft, why, False
