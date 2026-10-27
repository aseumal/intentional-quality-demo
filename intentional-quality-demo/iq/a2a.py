"""A2A-style Agent Cards and messages.

Each agent publishes an Agent Card (what it can do). Work moves between agents as
JSON-RPC 2.0 `message/send` requests carrying a data part, following the shape of
the A2A protocol. In this demo the transport is in-process so it runs offline on
stage; the payloads are what would travel over HTTP between real A2A servers.
"""
import itertools
import json
import uuid

_ids = itertools.count(1)

AGENT_CARDS = {
    "orchestrator": {
        "name": "Mutation Orchestrator", "framework": "LangGraph",
        "description": "Runs the mutation loop: generate mutants, run tests, route survivors.",
        "url": "http://localhost:9001/a2a", "version": "1.0.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["application/json"], "defaultOutputModes": ["application/json"],
        "skills": [{"id": "mutation-loop", "name": "Mutation loop", "tags": ["testing", "mutation"]}],
    },
    "court": {
        "name": "Equivalence Court", "framework": "AutoGen",
        "description": "Debates a surviving mutant: real gap or equivalent?",
        "url": "http://localhost:9002/a2a", "version": "1.0.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["application/json"], "defaultOutputModes": ["application/json"],
        "skills": [{"id": "judge-survivor", "name": "Judge a survivor", "tags": ["equivalence", "debate"]}],
    },
    "ranker": {
        "name": "VRTQ Ranker", "framework": "VRTQ",
        "description": "Ranks real gaps by Value, Risk, Time and Quality.",
        "url": "http://localhost:9003/a2a", "version": "1.0.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["application/json"], "defaultOutputModes": ["application/json"],
        "skills": [{"id": "rank-gaps", "name": "Rank gaps", "tags": ["prioritization", "vrtq"]}],
    },
    "writer": {
        "name": "Test Writer Crew", "framework": "CrewAI",
        "description": "Writes a unit test that kills a real-gap mutant.",
        "url": "http://localhost:9004/a2a", "version": "1.0.0",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["application/json"], "defaultOutputModes": ["text/x-python"],
        "skills": [{"id": "write-killing-test", "name": "Write killing test", "tags": ["testing", "codegen"]}],
    },
}

LOG = []  # every message sent, for the end-of-demo summary


def send(sender: str, recipient: str, data: dict) -> dict:
    """Build an A2A `message/send` request from one agent to another and log it."""
    msg = {
        "jsonrpc": "2.0", "id": next(_ids), "method": "message/send",
        "params": {"message": {
            "role": "user", "messageId": str(uuid.uuid4())[:8],
            "parts": [{"kind": "data", "data": data}],
            "metadata": {"from": AGENT_CARDS[sender]["name"], "to": AGENT_CARDS[recipient]["name"]},
        }},
    }
    LOG.append(msg)
    return msg


def pretty(msg: dict) -> str:
    return json.dumps(msg, indent=2, ensure_ascii=False)
