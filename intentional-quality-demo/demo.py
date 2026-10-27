"""Intentional Quality: SoftCon 2026 live demo.

  python demo.py --stage           # presenter mode: pauses at every step (press Enter)
  python demo.py                   # runs straight through with gentle pacing
  python demo.py --live --stage    # AutoGen and CrewAI agents use a real LLM (needs an API key)
  python demo.py --record backup.html --fast   # make the recorded backup
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from iq.pipeline import build  # noqa: E402
from iq.ui import UI, ICE, MUTED  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", action="store_true", help="pause at every step (presenter mode)")
    ap.add_argument("--live", action="store_true", help="use real LLM agents for the debate and the test writer")
    ap.add_argument("--fast", action="store_true", help="no pacing delays")
    ap.add_argument("--record", metavar="HTML", help="save the whole run as an HTML backup")
    args = ap.parse_args()

    ui = UI(stage=args.stage and not args.record, record=bool(args.record), speed=0 if (args.fast or args.record) else 1.0)
    with open(os.path.join(HERE, "pricing.py"), encoding="utf-8") as f:
        original = f.read()
    with open(os.path.join(HERE, "test_pricing.py"), encoding="utf-8") as f:
        tests = [f.read()]

    mode = "LIVE agents (LLM)" if args.live else "offline agents (deterministic, no network)"
    ui.console.rule(f"[bold {ICE}]Intentional Quality[/]  [{MUTED}]mutation testing x agents x VRTQ x A2A   |   {mode}[/]",
                    style=ICE)
    graph, sequence, route = build(ui, live=args.live)
    state = {"original": original, "tests": tests}
    if graph is not None:
        ui.say("  Orchestrated by a LangGraph StateGraph: baseline > mutate > run > debate > rank > write > verify > report",
               MUTED)
        graph.invoke(state)
    else:
        ui.say("  (LangGraph not installed: running the same nodes in sequence)", MUTED)
        for node in sequence:
            if node.__name__ == "debate" and route(state) == "report":
                state.update(sequence[-1](state)); break
            state.update(node(state))

    if args.record:
        ui.save_html(args.record, "Intentional Quality demo: recorded run")
        print(f"saved {args.record}")


if __name__ == "__main__":
    main()
