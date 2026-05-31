"""
根据模板目录与多源报告，生成整本报告的标题/目录/主题设计。
"""

from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger

from ..core import TemplateSection
from ..state import ReportGraphState
from ..prompts import (
    SYSTEM_PROMPT_DOCUMENT_LAYOUT,
    build_document_layout_prompt,
)
from ..utils.json_parser import RobustJSONParser, JSONParseError
from .base_node import BaseNode


class DesignLayoutNode(BaseNode):
    _RETRY_ATTEMPTS = 2

    """
    负责生成全局标题、目录与Hero设计。

    结合模板切片、报告摘要与论坛讨论，指导整本书的视觉与结构基调。
    """

    def __init__(self, ctx):
        """记录上下文与LLM客户端，供BaseNode日志使用"""
        self.ctx = ctx
        super().__init__(ctx.llm_client, "DesignLayoutNode")
        # 初始化鲁棒JSON解析器，启用所有修复策略
        self.json_parser = RobustJSONParser(
            enable_json_repair=True,
            enable_llm_repair=False,  # 可以根据需要启用LLM修复
            max_repair_attempts=3,
        )

    def __call__(self, state: ReportGraphState) -> dict:
        query = state["query"]
        reports = state.get("normalized_reports", {})
        forum_logs = state.get("forum_logs", "")
        sections = state.get("template_sections", [])
        template_text = state.get("template_result", {}).get("template_content", "")
        template_overview = state.get("template_overview", {})

        last_error = None
        for attempt in range(1, self._RETRY_ATTEMPTS + 1):
            try:
                result = self.run(sections, template_text, reports, forum_logs, query, template_overview)
                logger.info(f"文档设计完成: {result.get('title')}")
                return {"layout_design": result}
            except Exception as e:
                last_error = e
                logger.warning(f"文档设计第 {attempt} 次失败: {e}")
        raise last_error

    def run(
        self,
        sections: List[TemplateSection],
        template_markdown: str,
        reports: Dict[str, str],
        forum_logs: str,
        query: str,
        template_overview: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        综合模板+多源内容，生成全书的标题、目录结构与主题色板。

        参数:
            sections: 模板切片后的章节列表。
            template_markdown: 模板原文，用于LLM理解上下文。
            reports: 三个引擎的内容映射。
            forum_logs: 论坛讨论摘要。
            query: 用户查询词。
            template_overview: 预生成的模板概览，可复用以减少提示词长度。

        返回:
            dict: 包含 title/subtitle/toc/hero/themeTokens 等设计信息的字典。
        """
        # 将模板原文、切片结构与多源报告一并喂给LLM，便于其理解层级与素材
        payload = {
            "query": query,
            "template": {
                "raw": template_markdown,
                "sections": [section.to_dict() for section in sections],
            },
            "templateOverview": template_overview
            or {
                "title": sections[0].title if sections else "",
                "chapters": [section.to_dict() for section in sections],
            },
            "reports": reports,
            "forumLogs": forum_logs,
        }

        user_message = build_document_layout_prompt(payload)
        response = self.llm_client.stream_invoke_to_string(
            SYSTEM_PROMPT_DOCUMENT_LAYOUT,
            user_message,
            temperature=0.3,
            top_p=0.9,
        )
        design = self._parse_response(response)
        logger.info("文档标题/目录设计已生成")
        return design

    def _parse_response(self, raw: str) -> Dict[str, Any]:
        """
        解析LLM返回的JSON文本，若失败则抛出友好错误。

        使用鲁棒JSON解析器进行多重修复尝试：
        1. 清理markdown标记和思考内容
        2. 本地语法修复（括号平衡、逗号补全、控制字符转义等）
        3. 使用json_repair库进行高级修复
        4. 可选的LLM辅助修复

        参数:
            raw: LLM原始返回字符串，允许带```包裹、思考内容等。

        返回:
            dict: 结构化的设计稿。

        异常:
            ValueError: 当响应为空或JSON解析失败时抛出。
        """
        try:
            result = self.json_parser.parse(
                raw,
                context_name="文档设计",
                # 目录字段已更名为 tocPlan，这里跟随最新Schema校验
                expected_keys=["title", "tocPlan", "hero"],
            )
            # 验证关键字段的类型
            if not isinstance(result.get("title"), str):
                logger.warning("文档设计缺少title字段或类型错误，使用默认值")
                result.setdefault("title", "未命名报告")

            # 处理tocPlan字段
            toc_plan = result.get("tocPlan", [])
            if not isinstance(toc_plan, list):
                logger.warning("文档设计缺少tocPlan字段或类型错误，使用空列表")
                result["tocPlan"] = []
            else:
                # 清理tocPlan中的description字段
                result["tocPlan"] = self._clean_toc_plan_descriptions(toc_plan)

            if not isinstance(result.get("hero"), dict):
                logger.warning("文档设计缺少hero字段或类型错误，使用空对象")
                result.setdefault("hero", {})

            return result
        except JSONParseError as exc:
            # 转换为原有的异常类型以保持向后兼容
            raise ValueError(f"文档设计JSON解析失败: {exc}") from exc

    def _clean_toc_plan_descriptions(self, toc_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        清理tocPlan中每个条目的description字段，移除可能的JSON片段。

        参数:
            toc_plan: 原始的目录计划列表

        返回:
            List[Dict[str, Any]]: 清理后的目录计划列表
        """
        import re

        def clean_text(text: Any) -> str:
            """清理文本中的JSON片段"""
            if not text or not isinstance(text, str):
                return ""

            cleaned = text

            # 移除以逗号+空白+{开头的不完整JSON对象
            cleaned = re.sub(r',\s*\{[^}]*$', '', cleaned)

            # 移除以逗号+空白+[开头的不完整JSON数组
            cleaned = re.sub(r',\s*\[[^\]]*$', '', cleaned)

            # 移除孤立的 { 加上后续内容（如果没有匹配的 }）
            open_brace_pos = cleaned.rfind('{')
            if open_brace_pos != -1:
                close_brace_pos = cleaned.rfind('}')
                if close_brace_pos < open_brace_pos:
                    cleaned = cleaned[:open_brace_pos].rstrip(',，、 \t\n')

            # 移除孤立的 [ 加上后续内容（如果没有匹配的 ]）
            open_bracket_pos = cleaned.rfind('[')
            if open_bracket_pos != -1:
                close_bracket_pos = cleaned.rfind(']')
                if close_bracket_pos < open_bracket_pos:
                    cleaned = cleaned[:open_bracket_pos].rstrip(',，、 \t\n')

            # 移除看起来像JSON键值对的片段
            cleaned = re.sub(r',?\s*"[^"]+"\s*:\s*"[^"]*$', '', cleaned)
            cleaned = re.sub(r',?\s*"[^"]+"\s*:\s*[^,}\]]*$', '', cleaned)

            # 清理末尾的逗号和空白
            cleaned = cleaned.rstrip(',，、 \t\n')

            return cleaned.strip()

        cleaned_plan = []
        for entry in toc_plan:
            if not isinstance(entry, dict):
                continue

            # 清理description字段
            if "description" in entry:
                original_desc = entry["description"]
                cleaned_desc = clean_text(original_desc)

                if cleaned_desc != original_desc:
                    logger.warning(
                        f"清理目录项 '{entry.get('display', 'unknown')}' 的description字段中的JSON片段:\n"
                        f"  原文: {original_desc[:100]}...\n"
                        f"  清理后: {cleaned_desc[:100]}..."
                    )
                    entry["description"] = cleaned_desc

            cleaned_plan.append(entry)

        return cleaned_plan


__all__ = ["DesignLayoutNode"]
