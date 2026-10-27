# Intentional Quality: SoftCon 2026 demo

Live demo from my SoftCon 2026 talk, *Three Frameworks: An Empirical Study of Agentic AI Architectures for QA Intelligence*.

A checkout module with 100% line coverage and all tests green still lets bugs through. Mutation testing finds the gaps. LangGraph, AutoGen and CrewAI agents close them. VRTQ ranks them by risk, and A2A-shaped messages connect the agents.

Mutation score: 43% → 50% → 100%. Coverage stays at 100% throughout.

**Code, setup and run instructions:** [intentional-quality-demo/](intentional-quality-demo/)

```bash
cd intentional-quality-demo
pip install rich langgraph pytest
python demo.py --stage
```

No API key needed: offline mode is the default. Use `--live` for real LLM agents (see the folder's README).

Anthony Seumal · [LinkedIn](https://www.linkedin.com/in/anthonyseumal) · [Medium](https://medium.com/@qualityinmind)
