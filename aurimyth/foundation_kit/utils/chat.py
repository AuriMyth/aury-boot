from __future__ import annotations

import json
from typing import Any, Iterable, Optional

from openai import AsyncOpenAI

from aurimyth.config import settings
from aurimyth.foundation_kit.utils.logging import logger


class ChatClient:
    def __init__(self, system_prompt: str = "", history: Optional[list[dict[str, Any]]] = None) -> None:
        self.system_prompt = system_prompt
        self.history = history or []
        if system_prompt and not self.history:
            self.history = [{"role": "system", "content": system_prompt}]
        self.client = AsyncOpenAI(base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY)

    async def chat(
        self,
        message: str,
        *,
        temperature: float = 0.8,
        output_format: str = "json_object",
        use_history: bool = False,
        model: str = "gpt-4o",
        custom_history: Optional[list[dict[str, Any]]] = None,
    ) -> Any:
        history = (self.history + custom_history) if custom_history else self.history
        completion = await self.client.chat.completions.create(
            model=model,
            messages=history + [{"role": "user", "content": message}],
            temperature=temperature,
            response_format={"type": "json_object" if output_format in {"json_object", "json_list"} else "text"},
            timeout=300,
        )

        content = completion.choices[0].message.content
        logger.info(content)

        if use_history:
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": content})

        if output_format == "json_object":
            return json.loads(content)
        return content

    async def stream_chat(
        self,
        message: str,
        *,
        temperature: float = 0.8,
        use_history: bool = False,
        model: str = "gpt-4o",
        custom_history: Optional[list[dict[str, Any]]] = None,
    ) -> Iterable[str]:
        history = (self.history + custom_history) if custom_history else self.history
        stream = await self.client.chat.completions.create(
            model=model,
            messages=history + [{"role": "user", "content": message}],
            temperature=temperature,
            stream=True,
        )

        full_content = ""
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_content += content
                yield content

        if use_history:
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": full_content})

    async def embeddings(self, text: str, model: str = "text-embedding-3-small") -> list[float]:
        result = await self.client.embeddings.create(input=text, model=model)
        return result.data[0].embedding
