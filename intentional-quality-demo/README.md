# Intentional Quality: SoftCon 2026 demo

A live demo for *Three Frameworks: An Empirical Study of Agentic AI Architectures for QA Intelligence*.

It takes a small checkout module from a Philippine online shop, with a test suite that has **100% line coverage and all tests green**, and shows that the suite still lets bugs through. Then agents fix it:

| Step | Who | What happens |
|---|---|---|
| 0 | LangGraph | Baseline: 100% coverage, 8/8 tests green |
| 1 | LangGraph | Generate 7 mutants (one deliberate change each) |
| 2 | LangGraph | Run the tests against every mutant: **4 survive, mutation score 43%** |
| 3 | AutoGen | Debate each survivor: real gap or equivalent mutant? **3 real gaps, 1 equivalent** (score becomes 3/6 = 50%) |
| 4 | VRTQ | Rank the real gaps: discount at PHP 1,000 (P1), free shipping at PHP 1,500 (P1), discount at PHP 0 (P2) |
| 5 | CrewAI | Write one test per gap. A test is accepted only if it passes on the original and fails on the mutant |
| 6 | LangGraph | Re-run every mutant: all real gaps killed |
| 7 | Result | Coverage 100% → 100%. **Mutation score 43% → 50% → 100%.** 8 A2A messages exchanged |

Every number is computed live by the code. Nothing on screen is pre-written except the agents' phrasing in offline mode.

## Setup (do this the night before)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install rich langgraph pytest  # enough for the stage demo
```

Python 3.10 to 3.13. Check it works:

```bash
python demo.py --fast              # runs straight through in a few seconds
pytest -q test_pricing.py          # optional: the team's suite, 8 passed
```

## On stage

```bash
python demo.py --stage
```

It pauses after every step. Press **Enter** to continue. Make the terminal font large (at least 20 pt) and the window wide (about 120 columns).

## If the demo fails

Open **`backup.html`** in any browser. It's a recording of the same run and works with no internet. Say "here's the same run from this morning" and keep going. Don't apologise.

## Offline vs live agents

**Offline (default).** No network and no API key. It's deterministic, so it's safe on stage.
- The **AutoGen step** is an "equivalence court". The evidence comes from differential testing: the original and the mutant are run on about 20,000 inputs. The Gap Hunter, Equivalence Advocate and Judge roles then state that evidence.
- The **CrewAI step** is a deterministic Test Writer. It takes the Judge's counterexample and asks the original code for the expected answer.

**Live (`--live`).** Real LLM agents:
- **AutoGen AgentChat:** a `RoundRobinGroupChat` of three `AssistantAgent`s.
- **CrewAI:** a `Test Writer` agent.

```bash
pip install uv                      # pip can take a very long time resolving CrewAI; uv takes about a minute
uv pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # or: export DEMO_PROVIDER=openai OPENAI_API_KEY=...
export DEMO_MODEL=claude-sonnet-5-5 # any model id your key can use
python demo.py --live --stage
```

Guardrails apply in both modes, and they are the point of the talk:
- **Evidence overrules the debate.** If the agents call a mutant equivalent but a counterexample exists, the screen says so and the evidence wins.
- **No unverified tests.** A test the agent drafts is rejected unless it is green on the original and red on the mutant. The deterministic writer then takes over.
- **Failing safe.** If the LLM call fails (no network, no key), the demo falls back to offline mode for that step and shows a note.

Rehearse `--live` at least once on the conference Wi-Fi before deciding to use it. **The offline mode is the recommended stage default.**

What has been tested: the complete live pipeline (AutoGen group chat, CrewAI Test Writer, guardrails, fallbacks) ran end to end against a stubbed Claude API, and falls back cleanly with no network. What has not: a real Claude response, and whether `DEMO_MODEL` is a model id your key can use. That's what your rehearsal checks.

Why `iq/llm_client.py` exists: AutoGen's bundled Anthropic client (autogen-ext 0.7.5) sends a `temperature` argument that the current Anthropic SDK rejects, so the debate uses a small client that calls the Messages API directly. CrewAI's own Anthropic integration works as is.

## About the A2A handoffs

Each agent has an A2A Agent Card (`iq/a2a.py`). Work moves between agents as JSON-RPC 2.0 `message/send` requests carrying a data part, which is the A2A message shape. The first handoff prints the full JSON so the audience can see it.

In this demo the transport is **in-process**, so it runs offline. That means the payloads follow the A2A format, but there are no separate A2A servers over HTTP. If someone asks, say so plainly: "the messages are A2A-shaped; in production each agent would sit behind its own A2A endpoint."

## Files

```
demo.py            entry point (--stage, --live, --fast, --record)
pricing.py         the code under test
test_pricing.py    the team's suite: 100% coverage, all green
iq/mutator.py      AST mutation operators (relational, arithmetic, if/else swap)
iq/runner.py       in-process test runner and line coverage
iq/pipeline.py     LangGraph StateGraph: the nodes and the routing
iq/debate.py       AutoGen step: differential evidence, offline court, live AgentChat
iq/vrtq.py         VRTQ weights (0.30 / 0.35 / 0.20 / 0.15) and P1/P2/P3 tiers
iq/writer.py       CrewAI step: deterministic writer, live Test Writer, validation
iq/a2a.py          Agent Cards and A2A-shaped messages
iq/llm_client.py   minimal AutoGen model client for Claude (live mode only)
backup.html        recorded run (open in a browser)
STAGE_SCRIPT.md    what to say, step by step, in 8 minutes
```

Recreate the backup after any change:

```bash
python demo.py --record backup.html
```
