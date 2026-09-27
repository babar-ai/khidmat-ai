"""
Centralized OpenAI Service for Khidmat AI.

Single point of control for all OpenAI API interactions:
  - Client initialization and lifecycle
  - Structured JSON completion handling
  - Standard chat completions
  - Unified error logging and timeout handling
"""

import json
import logging
from typing import Any

from openai import OpenAI

from core.config import settings

logger = logging.getLogger(__name__)



class OpenAIService:
    """
    Service wrapper around the OpenAI API.
    Provides standardized methods for structured outputs and conversational calls.
    """


    def __init__(self, api_key: str | None = None, default_model: str = "gpt-4o"):

        self.api_key = api_key or settings.OPENAI_API_KEY
        self.default_model = default_model
        self._client: OpenAI | None = None


    # @property allows me to expose the client as an attribute instead of requiring a method call.
    @property
    def client(self) -> OpenAI:

        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        
        return self._client


    def extract_structured_json(
        self,
        system_prompt: str,
        user_content: str,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:

        """
        Sends system and user prompts to OpenAI with JSON mode enabled,
        parsing and returning the resulting JSON object as a Python dict.
        """
        target_model = model or self.default_model
        logger.debug("Requesting structured JSON completion from model '%s'", target_model)

        response = self.client.chat.completions.create(
            model=target_model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_content},
            ],
        )
    
        content = response.choices[0].message.content or "{}"

        logger.info("content: %s", content)
        try:
            logger.info("content: %s", content)
            return json.loads(content)

        except json.JSONDecodeError as err:
            logger.error("Failed to parse JSON response from OpenAI: %s. Raw: %s", err, content)
            raise ValueError(f"Malformed JSON returned by model: {err}") from err


    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """
        General-purpose chat completion returning raw string content.
        """
        target_model = model or self.default_model
        response = self.client.chat.completions.create(
            model=target_model,
            temperature=temperature,
            messages=messages,  # type: ignore[arg-type]
        )
        return response.choices[0].message.content or ""


# Shared singleton instance for application-wide use
openai_service = OpenAIService()
