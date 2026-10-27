# Stage script: the 8-minute demo (slide 29)

Run: `python demo.py --stage`. Each step below ends with a pause. Press Enter when you're done talking.
Your backup is `backup.html`. If anything stalls for more than 10 seconds, switch to it.

---

## Before you press Enter (0:00 to 0:30)

> "Everything you're about to see is computed live. Three frameworks, one pipeline, handing work to each other in A2A messages. Let's start with a test suite any of us would be proud of."

## Step 0: The suite our team trusts (0:30 to 1:30)

The screen shows `pricing.py`, then **100% coverage, 8 of 8 tests passing**.

> "A Philippine online shop. Three rules: 10% off from 1,000 pesos, free shipping from 1,500, loyalty points capped at 50. Coverage is 100%, everything's green. Hands up if you'd approve this pull request."

Wait for hands. Press Enter.

## Steps 1 and 2: Plant bugs, run the tests (1:30 to 3:00)

The screen shows 7 mutants. **4 SURVIVED. Mutation score 43%.**

> "LangGraph runs the process. It planted seven bugs on purpose, one tiny change each, and ran our suite against every one. Four of them survived. Same tests, same 100% coverage. Those four are bugs we would have shipped."

Point at mutant #2, `>=` to `>` on 1,000:

> "Remember the bug hunt? There it is: the customer at exactly 1,000 pesos."

Press Enter.

## Step 3: The debate (3:00 to 5:00), the centrepiece

The screen shows the A2A JSON once, then four short debates.

> "Now the hard part of mutation testing, the part that made teams give up: is a survivor a real gap, or an equivalent mutant that no test could ever catch? That's a judgment call, so it's AutoGen's job. The agents argue."

At the first JSON block:

> "This is what travels between frameworks: an A2A message. LangGraph doesn't need to know AutoGen exists. It just sends a task to an Agent Card."

At mutant #7 (loyalty points, `>` to `>=`), slow down:

> "Here the advocate wins. When points equals 50, one version skips the assignment and the other sets it to 50. Same answer either way. The judge tried twenty thousand inputs and found no difference: an equivalent mutant. So it comes out of the score."

Point at **50%**:

> "Honest mutation score: 3 out of 6. Not 43%. Being intentional includes not punishing your tests for something no test can catch."

Press Enter.

## Step 4: VRTQ ranks the gaps (5:00 to 5:45)

The screen shows the table. Discount at 1,000 scores **9.00 P1**, shipping at 1,500 scores **8.40 P1**, discount at 0 scores **6.05 P2**.

> "Three gaps, but they don't matter equally. VRTQ, the formula from Lie #2, ranks them: value, risk, time, quality. The 1,000-peso discount is P1: it's money, and it's a boundary. A zero-peso order is real but rare: P2. Humans set those weights, on purpose."

Press Enter.

## Step 5: CrewAI writes the tests (5:45 to 6:45)

The screen shows three small tests, each **accepted: green on original, red on mutant**.

> "CrewAI's Test Writer takes each counterexample and writes the test, highest priority first. And here's the guardrail: a test is only accepted if it passes on the real code and fails on the mutant. No agent gets to merge a test that proves nothing."

Press Enter.

## Steps 6 and 7: Verify and result (6:45 to 8:00)

Everything is KILLED except the one equivalent. The result reads **coverage 100% → 100%, mutation score 43% → 50% → 100%, 8 A2A messages.**

> "Look at coverage: it never moved. 100% before, 100% after. If coverage was our only number, we'd think nothing changed. The mutation score went from 43 to 100. Three frameworks, each doing one job, talking through one protocol, inside limits we set. That's intentional quality."

Go back to the slides (slide 30).

---

## If someone asks

**"Were the agents real LLMs?"**
"On stage I run the offline mode, so it can't fail on Wi-Fi. The evidence is computed by differential testing and the roles state it. The same pipeline runs with live AutoGen and CrewAI agents using `--live`, and the guardrails are identical: evidence overrules the debate."

Only say the live part if you've rehearsed it.

**"Is that real A2A?"**
"The messages follow the A2A format: Agent Cards and JSON-RPC `message/send`. Here they travel in-process so the demo runs offline. In production, each agent sits behind its own A2A endpoint."

**"Why not use mutmut or PIT?"**
"In a real project, do. I wrote a tiny mutator so you can see every mutant on one screen. The idea is the same."

**"20,000 inputs proves equivalence?"**
"No, it's strong evidence, not proof. Equivalence is undecidable in general. That's exactly why it's a judgment call, and why we need the debate and a human-set limit."
