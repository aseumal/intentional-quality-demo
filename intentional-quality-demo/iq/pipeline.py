"""LangGraph's job: run the process. Every step is a node; survivors are routed on purpose."""
from typing import TypedDict

from rich.text import Text

from . import a2a, debate as court, mutator, runner, vrtq, writer
from .ui import AMBER, CORAL, GREEN, ICE, MUTED


class State(TypedDict, total=False):
    original: str
    tests: list
    mutants: list
    gaps: list          # dicts: mutant, evidence, score, test
    equivalents: list
    killed_before: int
    scores: list        # (label, killed, denominator)


def pct(k, d):
    return f"{round(100 * k / d)}%" if d else "n/a"


def build(ui, live=False):
    def baseline(s: State):
        ui.step(0, "The test suite our team trusts", "LangGraph")
        covered, executable = runner.line_coverage(s["original"], s["tests"])
        res = runner.run_suite(s["original"], s["tests"])
        ui.code(s["original"], title="pricing.py")
        ui.wait(0.6)
        ui.big_numbers([("line coverage", pct(len(covered), len(executable)), GREEN),
                        ("tests passing", f"{len(res.passed)} / {len(res.passed) + len(res.failed)}", GREEN)])
        ui.say("  Would you approve this pull request?", f"bold {AMBER}")
        ui.pause()
        return {}

    def mutate(s: State):
        ui.step(1, "Plant bugs on purpose: generate mutants", "LangGraph")
        muts = mutator.generate(s["original"])
        ui.say(f"  {len(muts)} mutants: one small change each, every comparison, operator and branch.", MUTED)
        ui.wait(0.4)
        return {"mutants": muts}

    def run_mutants(s: State):
        ui.step(2, "Run the existing tests against every mutant", "LangGraph")
        table = ui.mutant_row_table()
        killed = 0
        for m in s["mutants"]:
            res = runner.run_suite(m.source, s["tests"])
            if res.failed:
                m.status, m.killed_by = "killed", res.failed[0][0]
                killed += 1
            else:
                m.status = "survived"
            table.add_row(str(m.id), m.function, str(m.line), m.description, m.mutated_line, ui.status_text(m.status))
        ui.console.print(table)
        ui.wait(0.5)
        survivors = [m for m in s["mutants"] if m.status == "survived"]
        total = len(s["mutants"])
        ui.big_numbers([("line coverage", "100%", GREEN),
                        ("mutation score", pct(killed, total), CORAL),
                        ("survivors", str(len(survivors)), CORAL)])
        ui.say("  Same tests. 100% coverage. But these survivors are bugs our suite would ship.", f"bold {CORAL}")
        ui.pause()
        return {"killed_before": killed, "scores": [("before", killed, total)]}

    def route(s: State):
        return "debate" if any(m.status == "survived" for m in s["mutants"]) else "report"

    def debate(s: State):
        ui.step(3, "Real gap, or equivalent mutant? The agents debate", "AutoGen")
        gaps, equivalents = [], []
        first = True
        for m in [x for x in s["mutants"] if x.status == "survived"]:
            msg = a2a.send("orchestrator", "court", {
                "task": "judge-survivor", "mutant_id": m.id, "function": m.function,
                "line": m.line, "original": m.original_line, "mutated": m.mutated_line})
            ui.a2a(msg, show_json=first)
            first = False
            verdict, ev, transcript, note = court.debate(s["original"], m, live=live)
            ui.console.print(Text(f"\n  Mutant #{m.id}  {m.function}  line {m.line}:  {m.original_line}  ->  {m.mutated_line}",
                                  style=f"bold {ICE}"))
            for who, text in transcript:
                ui.wait(0.5)
                ui.speaker(who, text)
            if note:
                ui.say(f"  {note}", f"bold {AMBER}")
            if verdict == "EQUIVALENT":
                m.status = "equivalent"
                equivalents.append(m)
            else:
                gaps.append({"mutant": m, "evidence": ev})
            ui.wait(0.4)
        k = s["killed_before"]
        denom = len(s["mutants"]) - len(equivalents)
        ui.console.print()
        ui.big_numbers([("equivalent (excluded)", str(len(equivalents)), AMBER),
                        ("real gaps", str(len(gaps)), CORAL),
                        ("honest mutation score", pct(k, denom), CORAL)])
        ui.say(f"  Mutation score = killed / (total - equivalent) = {k} / {denom}", MUTED)
        ui.pause()
        return {"gaps": gaps, "equivalents": equivalents, "scores": s["scores"] + [("after debate", k, denom)]}

    def rank(s: State):
        ui.step(4, "Which gap matters most? VRTQ decides", "VRTQ")
        ui.a2a(a2a.send("court", "ranker", {"task": "rank-gaps", "gaps": [g["mutant"].id for g in s["gaps"]]}))
        for g in s["gaps"]:
            g["score"] = vrtq.score_gap(g["mutant"], g["evidence"])
        gaps = sorted(s["gaps"], key=lambda g: -g["score"].total)
        from rich.table import Table
        from rich import box
        t = Table(box=box.SIMPLE_HEAVY, header_style=f"bold {GREEN}")
        for col in ("mutant", "counterexample", "V .30", "R .35", "T .20", "Q .15", "VRTQ", "tier"):
            t.add_column(col)
        for g in gaps:
            sc, m, ev = g["score"], g["mutant"], g["evidence"]
            tier_style = f"bold {CORAL}" if sc.tier == "P1" else f"bold {AMBER}"
            t.add_row(f"#{m.id} {m.function}", court.call_str(m, ev["input"]),
                      str(sc.V), str(sc.R), str(sc.T), str(sc.Q), Text(f"{sc.total:.2f}", style="bold white"),
                      Text(sc.tier, style=tier_style))
        ui.console.print(t)
        ui.say("  VRTQ = 0.30 V + 0.35 R + 0.20 T + 0.15 Q     P1 >= 7.0   P2 >= 4.5", MUTED)
        ui.pause()
        return {"gaps": gaps}

    def write(s: State):
        ui.step(5, "Write the tests that kill the real gaps", "CrewAI")
        new_tests = []
        for g in s["gaps"]:
            m = g["mutant"]
            ui.a2a(a2a.send("ranker", "writer", {"task": "write-killing-test", "mutant_id": m.id,
                                                 "priority": g["score"].tier,
                                                 "counterexample": court.call_str(m, g["evidence"]["input"])}))
            src, why, used_live = writer.write_test(s["original"], m, g["evidence"], s["tests"], live=live)
            g["test"] = src
            new_tests.append(src)
            ui.code(src, title=f"{g['score'].tier}  kills mutant #{m.id}" + ("  (live agent)" if used_live else ""))
            ui.say(f"  accepted: {why}" if "Guardrail" not in why and "unavailable" not in why else f"  {why}",
                   GREEN if "Guardrail" not in why and "unavailable" not in why else AMBER)
            ui.wait(0.5)
        ui.pause()
        return {"tests": s["tests"] + new_tests}

    def verify(s: State):
        ui.step(6, "Run every mutant again, with the new tests", "LangGraph")
        table = ui.mutant_row_table()
        killed = 0
        for m in s["mutants"]:
            if m.status != "equivalent":
                res = runner.run_suite(m.source, s["tests"])
                m.status = "killed" if res.failed else "survived"
                killed += m.status == "killed"
            table.add_row(str(m.id), m.function, str(m.line), m.description, m.mutated_line, ui.status_text(m.status))
        ui.console.print(table)
        denom = len(s["mutants"]) - len(s["equivalents"])
        return {"scores": s["scores"] + [("after new tests", killed, denom)]}

    def report(s: State):
        ui.step(7, "Result", "A2A")
        sc = s["scores"]
        items = [("line coverage", "100%  ->  100%", MUTED)]
        items.append(("mutation score", "  ->  ".join(pct(k, d) for _, k, d in sc), GREEN))
        items.append(("A2A messages", str(len(a2a.LOG)), ICE))
        ui.big_numbers(items)
        ui.say("  Coverage never moved. The mutation score told us the truth, and agents helped us act on it,", "white")
        ui.say("  within limits we set: evidence overrules the debate, and no test is accepted unless it kills its mutant.", "white")
        return {}

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        return None, [baseline, mutate, run_mutants, debate, rank, write, verify, report], route

    g = StateGraph(State)
    for fn in (baseline, mutate, run_mutants, debate, rank, write, verify, report):
        g.add_node(fn.__name__, fn)
    g.add_edge(START, "baseline")
    g.add_edge("baseline", "mutate")
    g.add_edge("mutate", "run_mutants")
    g.add_conditional_edges("run_mutants", route, {"debate": "debate", "report": "report"})
    g.add_edge("debate", "rank")
    g.add_edge("rank", "write")
    g.add_edge("write", "verify")
    g.add_edge("verify", "report")
    g.add_edge("report", END)
    return g.compile(), None, route
