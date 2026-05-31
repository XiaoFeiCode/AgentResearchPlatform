"""
Report Engine default LLM client wrapper.
Re-exports the shared LLMClient from engines/common.
"""

from common.llm_client import LLMClient as _LLMClient


class LLMClient(_LLMClient):
    """针对OpenAI Chat Completion API的轻量封装，统一Report Engine调用入口。"""

    def __init__(self, api_key: str, model_name: str, base_url=None):
        super().__init__(api_key, model_name, base_url, engine_name="ReportEngine")
