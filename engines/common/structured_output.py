"""
Pydantic models for structured LLM output across all engines.

Used with LLMClient.structured_invoke() to get typed responses
instead of raw JSON strings that need manual parsing.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ── Report structure (generate_structure node) ────────────────────

class ParagraphOutline(BaseModel):
    title: str = Field(description="段落标题")
    content: str = Field(description="段落预期内容描述")


class ReportStructure(BaseModel):
    paragraphs: List[ParagraphOutline] = Field(description="报告段落列表，最多5个")


# ── Search query (initial_search / reflection_search nodes) ───────

class SearchOutput(BaseModel):
    search_query: str = Field(description="搜索查询词")
    search_tool: str = Field(description="搜索工具名称")
    reasoning: str = Field(description="选择理由")
    start_date: Optional[str] = Field(default=None, description="开始日期 YYYY-MM-DD，仅 search_topic_by_date")
    end_date: Optional[str] = Field(default=None, description="结束日期 YYYY-MM-DD，仅 search_topic_by_date")
    platform: Optional[str] = Field(default=None, description="平台名，仅 search_topic_on_platform")
    time_period: Optional[str] = Field(default=None, description="时间范围，仅 search_hot_content")


# ── Initial summary (initial_summary node) ────────────────────────

class InitialSummaryOutput(BaseModel):
    paragraph_latest_state: str = Field(description="基于搜索结果的段落总结，800-1200字")


# ── Reflection summary (reflection_summary node) ──────────────────

class ReflectionSummaryOutput(BaseModel):
    updated_paragraph_latest_state: str = Field(description="融合新搜索数据后的更新段落总结")
