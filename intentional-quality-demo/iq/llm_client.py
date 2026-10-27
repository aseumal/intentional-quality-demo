"""A minimal AutoGen model client that calls the Anthropic Messages API directly.

AutoGen's bundled Anthropic client (autogen-ext 0.7.x) sends a `temperature`
argument that current versions of the Anthropic SDK no longer accept, so it
fails before reaching the API. This client sends only what the API takes:
model, max_tokens, system and messages. Text only; no tools, no streaming.
"""
import os
from typing import Any, Mapping, Optional, Sequence

from autogen_core import CancellationToken
from autogen_core.models import (AssistantMessage, ChatCompletionClient, CreateResult, LLMMessage,
                                 ModelInfo, RequestUsage, SystemMessage, UserMessage)


def _text(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(str(c) for c in content if isinstance(c, str))


class ClaudeClient(ChatCompletionClient):
    def __init__(self, model: str, max_tokens: int = 400):
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self._model, self._max_tokens = model, max_tokens
        self._usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._info = ModelInfo(vision=False, function_calling=False, json_output=False,
                               family="unknown", structured_output=False, multiple_system_messages=True)

    def _to_api(self, messages: Sequence[LLMMessage]):
        system, turns = [], []
        for m in messages:
            if isinstance(m, SystemMessage):
                system.append(m.content)
                continue
            role = "assistant" if isinstance(m, AssistantMessage) else "user"
            text = _text(m.content)
            if isinstance(m, UserMessage) and m.source not in ("user", None):
                text = f"[{m.source}] {text}"  # who said it, in a group chat
            if turns and turns[-1]["role"] == role:
                turns[-1]["content"] += "\n\n" + text  # the API wants alternating roles
            else:
                turns.append({"role": role, "content": text})
        if not turns or turns[0]["role"] != "user":
            turns.insert(0, {"role": "user", "content": "Begin."})
        return "\n\n".join(system), turns

    async def create(self, messages: Sequence[LLMMessage], *, tools=(), tool_choice="auto", json_output=None,
                     extra_create_args: Mapping[str, Any] = {}, cancellation_token: Optional[CancellationToken] = None
                     ) -> CreateResult:
        system, turns = self._to_api(messages)
        resp = await self._client.messages.create(model=self._model, max_tokens=self._max_tokens,
                                                  system=system or None, messages=turns)
        text = "".join(getattr(b, "text", "") for b in resp.content)
        usage = RequestUsage(prompt_tokens=getattr(resp.usage, "input_tokens", 0),
                             completion_tokens=getattr(resp.usage, "output_tokens", 0))
        self._usage = RequestUsage(prompt_tokens=self._usage.prompt_tokens + usage.prompt_tokens,
                                   completion_tokens=self._usage.completion_tokens + usage.completion_tokens)
        return CreateResult(finish_reason="stop", content=text, usage=usage, cached=False)

    async def create_stream(self, messages, **kwargs):
        yield await self.create(messages, **kwargs)

    async def close(self):
        await self._client.close()

    def actual_usage(self) -> RequestUsage:
        return self._usage

    def total_usage(self) -> RequestUsage:
        return self._usage

    def count_tokens(self, messages, *, tools=()) -> int:
        return sum(len(_text(getattr(m, "content", ""))) // 4 for m in messages)

    def remaining_tokens(self, messages, *, tools=()) -> int:
        return 100_000 - self.count_tokens(messages)

    @property
    def capabilities(self):
        return self._info

    @property
    def model_info(self) -> ModelInfo:
        return self._info
