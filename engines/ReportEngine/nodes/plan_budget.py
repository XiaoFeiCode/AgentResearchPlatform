"""
章节篇幅规划节点。
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from ..core import TemplateSection
from ..state import ReportGraphState
from ..prompts import (
    SYSTEM_PROMPT_WORD_BUDGET,
    build_word_budget_prompt,
)
from ..utils.json_parser import RobustJSONParser, JSONParseError
from .base_node import BaseNode


class PlanBudgetNode(BaseNode):
    _RETRY_ATTEMPTS = 2

    """
    规划各章节字数与重点。

    输出总字数、全局写作准则以及每章/小节的 target/min/max 字数约束。
    """

    def __init__(self, ctx):
        """记录上下文与LLM客户端，方便run阶段发起请求"""
        self.ctx = ctx
        super().__init__(ctx.llm_client, "PlanBudgetNode")
        # 初始化鲁棒JSON解析器，启用所有修复策略
        self.json_parser = RobustJSONParser(
            enable_json_repair=True,
            enable_llm_repair=False,  # 可以根据需要启用LLM修复
            max_repair_attempts=3,
        )

    def __call__(self, state: ReportGraphState) -> dict:
        sections = state.get("template_sections", [])
        layout = state.get("layout_design", {})
        reports = state.get("normalized_reports", {})
        forum_logs = state.get("forum_logs", "")
        query = state["query"]
        template_overview = state.get("template_overview", {})

        last_error = None
        for attempt in range(1, self._RETRY_ATTEMPTS + 1):
            try:
                result = self.run(sections, layout, reports, forum_logs, query, template_overview)
                result = _normalize(result)
                logger.info(f"篇幅规划完成: {len(result.get('chapters', []))} 章节")
                return {"word_plan": result}
            except Exception as e:
                last_error = e
                logger.warning(f"篇幅规划第 {attempt} 次失败: {e}")
        raise last_error

    def run(
        self,
        sections: List[TemplateSection],
        design: Dict[str, Any],
        reports: Dict[str, str],
        forum_logs: str,
        query: str,
        template_overview: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        根据设计稿和所有素材规划章节字数，让LLM写作时有明确篇幅目标。

        参数:
            sections: 模板章节列表。
            design: 布局节点返回的设计稿（title/toc/hero等）。
            reports: 三引擎报告映射。
            forum_logs: 论坛日志原文。
            query: 用户查询词。
            template_overview: 可选的模板概览，含章节元信息。

        返回:
            dict: 章节篇幅规划结果，包含 `totalWords`、`globalGuidelines` 与逐章 `chapters`。
        """
        # 输入中除了章节骨架外，还包含布局节点输出，方便约束篇幅时参考视觉主次
        payload = {
            "query": query,
            "design": design,
            "sections": [section.to_dict() for section in sections],
            "templateOverview": template_overview
            or {
                "title": sections[0].title if sections else "",
                "chapters": [section.to_dict() for section in sections],
            },
            "reports": reports,
            "forumLogs": forum_logs,
        }
        user = build_word_budget_prompt(payload)
        response = self.llm_client.stream_invoke_to_string(
            SYSTEM_PROMPT_WORD_BUDGET,
            user,
            temperature=0.25,
            top_p=0.85,
        )
        plan = self._parse_response(response)
        logger.info("章节字数规划已生成")
        return plan

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """
        将LLM输出的JSON文本转为字典，失败时提示规划异常。

        使用鲁棒JSON解析器进行多重修复尝试：
        1. 清理markdown标记和思考内容
        2. 本地语法修复（括号平衡、逗号补全、控制字符转义等）
        3. 使用json_repair库进行高级修复
        4. 可选的LLM辅助修复

        参数:
            raw: LLM返回值，可能包含```包裹、思考内容等。

        返回:
            dict: 合法的篇幅规划JSON。

        异常:
            ValueError: 当响应为空或JSON解析失败时抛出。
        """
        try:
            result = self.json_parser.parse(
                raw,
                context_name="篇幅规划",
                expected_keys=["totalWords", "globalGuidelines", "chapters"],
            )
            # 验证关键字段的类型
            if not isinstance(result.get("totalWords"), (int, float)):
                logger.warning("篇幅规划缺少totalWords字段或类型错误，使用默认值")
                result.setdefault("totalWords", 10000)
            if not isinstance(result.get("globalGuidelines"), list):
                logger.warning("篇幅规划缺少globalGuidelines字段或类型错误，使用空列表")
                result.setdefault("globalGuidelines", [])
            if not isinstance(result.get("chapters"), (list, dict)):
                logger.warning("篇幅规划缺少chapters字段或类型错误，使用空列表")
                result.setdefault("chapters", [])
            return result
        except JSONParseError as exc:
            # 转换为原有的异常类型以保持向后兼容
            raise ValueError(f"篇幅规划JSON解析失败: {exc}") from exc



def _normalize(wp: dict) -> dict:
    chapters = wp.get("chapters", [])
    if isinstance(chapters, dict):
        chapters = list(chapters.values())
    if isinstance(chapters, list):
        wp["chapters"] = [c for c in chapters if isinstance(c, dict)]
    g = wp.get("globalGuidelines")
    if not isinstance(g, list):
        wp["globalGuidelines"] = [g] if g else []
    if not isinstance(wp.get("totalWords"), (int, float)):
        wp["totalWords"] = 10000
    return wp


__all__ = ["PlanBudgetNode"]
