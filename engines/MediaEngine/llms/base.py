"""
Unified OpenAI-compatible LLM client for the Media Engine.
Re-exports the shared LLMClient from engines/common.
"""

from common.llm_client import LLMClient as _LLMClient


class LLMClient(_LLMClient):
    """Minimal wrapper around the OpenAI-compatible chat completion API."""

    def __init__(self, api_key: str, model_name: str, base_url=None):
        super().__init__(api_key, model_name, base_url, engine_name="MediaEngine")
