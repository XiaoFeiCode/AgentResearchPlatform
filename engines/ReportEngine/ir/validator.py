"""
章节级JSON结构校验器。

LLM按章节生成IR后，需要在落盘与装订前经过严格校验，以避免
渲染期的结构性崩溃。本模块实现轻量级的Python校验逻辑，
无需依赖jsonschema库即可快速定位错误。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .schema import (
    ALLOWED_BLOCK_TYPES,
    ALLOWED_INLINE_MARKS,
    ENGINE_AGENT_TITLES,
    IR_VERSION,
)


class IRValidator:
    """
    章节IR结构校验器。

    说明：
        - validate_chapter返回(是否通过, 错误列表)
        - 错误定位采用path语法，便于快速追踪
        - 内置对heading/paragraph/list/table等所有区块的细粒度校验
    """

    def __init__(self, schema_version: str = IR_VERSION):
        """记录当前Schema版本，便于未来多版本并存"""
        self.schema_version = schema_version

    # ======== 对外接口 ========

    def validate_chapter(self, chapter: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """校验单个章节对象的必填字段与block结构"""
        errors: List[str] = []
        if not isinstance(chapter, dict):
            return False, ["chapter必须是对象"]

        for field in ("chapterId", "title", "anchor", "order", "blocks"):
            if field not in chapter:
                errors.append(f"missing chapter.{field}")

        if not isinstance(chapter.get("blocks"), list) or not chapter.get("blocks"):
            errors.append("chapter.blocks必须是非空数组")
            return False, errors

        blocks = chapter.get("blocks", [])
        for idx, block in enumerate(blocks):
            self._validate_block(block, f"blocks[{idx}]", errors)

        return len(errors) == 0, errors

    # ======== 内部工具 ========

    def _validate_block(self, block: Any, path: str, errors: List[str]):
        """根据block类型调用不同的校验器"""
        if not isinstance(block, dict):
            errors.append(f"{path} 必须是对象")
            return

        block_type = block.get("type")
        if block_type not in ALLOWED_BLOCK_TYPES:
            errors.append(f"{path}.type 不被支持: {block_type}")
            return

        validator = getattr(self, f"_validate_{block_type}_block", None)
        if validator:
            validator(block, path, errors)

    def _validate_heading_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """heading必须有level/text/anchor"""
        if "level" not in block or not isinstance(block["level"], int):
            errors.append(f"{path}.level 必须是整数")
        if "text" not in block:
            errors.append(f"{path}.text 缺失")
        if "anchor" not in block:
            errors.append(f"{path}.anchor 缺失")

    def _validate_paragraph_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """paragraph需要非空inlines，并逐条校验"""
        inlines = block.get("inlines")
        if not isinstance(inlines, list) or not inlines:
            errors.append(f"{path}.inlines 必须是非空数组")
            return
        for idx, run in enumerate(inlines):
            self._validate_inline_run(run, f"{path}.inlines[{idx}]", errors)

    def _validate_list_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """列表需要声明listType且每个item都是block数组"""
        if block.get("listType") not in {"ordered", "bullet", "task"}:
            errors.append(f"{path}.listType 取值非法")
        items = block.get("items")
        if not isinstance(items, list) or not items:
            errors.append(f"{path}.items 必须是非空列表")
            return
        for i, item in enumerate(items):
            if not isinstance(item, list):
                errors.append(f"{path}.items[{i}] 必须是区块数组")
                continue
            for j, sub_block in enumerate(item):
                self._validate_block(sub_block, f"{path}.items[{i}][{j}]", errors)

    def _validate_table_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """表格需提供rows/cells/blocks，递归校验单元格内容"""
        rows = block.get("rows")
        if not isinstance(rows, list) or not rows:
            errors.append(f"{path}.rows 必须是非空数组")
            return
        for r_idx, row in enumerate(rows):
            cells = row.get("cells") if isinstance(row, dict) else None
            if not isinstance(cells, list) or not cells:
                errors.append(f"{path}.rows[{r_idx}].cells 必须是非空数组")
                continue
            for c_idx, cell in enumerate(cells):
                if not isinstance(cell, dict):
                    errors.append(f"{path}.rows[{r_idx}].cells[{c_idx}] 必须是对象")
                    continue
                blocks = cell.get("blocks")
                if not isinstance(blocks, list) or not blocks:
                    errors.append(
                        f"{path}.rows[{r_idx}].cells[{c_idx}].blocks 必须是非空数组"
                    )
                    continue
                for b_idx, sub_block in enumerate(blocks):
                    self._validate_block(
                        sub_block,
                        f"{path}.rows[{r_idx}].cells[{c_idx}].blocks[{b_idx}]",
                        errors,
                    )

    def _validate_swotTable_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """SWOT表至少提供四象限之一，每象限为条目数组"""
        quadrants = ("strengths", "weaknesses", "opportunities", "threats")
        if not any(block.get(name) is not None for name in quadrants):
            errors.append(f"{path} 需要至少包含 strengths/weaknesses/opportunities/threats 之一")
        for name in quadrants:
            entries = block.get(name)
            if entries is None:
                continue
            if not isinstance(entries, list):
                errors.append(f"{path}.{name} 必须是数组")
                continue
            for idx, entry in enumerate(entries):
                self._validate_swot_item(entry, f"{path}.{name}[{idx}]", errors)

    # SWOT impact 字段允许的评级值
    ALLOWED_IMPACT_VALUES = {"低", "中低", "中", "中高", "高", "极高"}

    def _validate_swot_item(self, item: Any, path: str, errors: List[str]):
        """单个SWOT条目支持字符串或带字段的对象"""
        if isinstance(item, str):
            if not item.strip():
                errors.append(f"{path} 不能为空字符串")
            return
        if not isinstance(item, dict):
            errors.append(f"{path} 必须是字符串或对象")
            return
        title = None
        for key in ("title", "label", "text", "detail", "description"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                title = value
                break
        if title is None:
            errors.append(f"{path} 缺少 title/label/text/description 等文字字段")

        # 校验 impact 字段：只允许评级值
        impact = item.get("impact")
        if impact is not None:
            if not isinstance(impact, str) or impact not in self.ALLOWED_IMPACT_VALUES:
                errors.append(
                    f"{path}.impact 只允许填写影响评级（低/中低/中/中高/高/极高），"
                    f"当前值: {impact}；如需详细说明请写入 detail 字段"
                )

        # # 校验 score 字段：只允许 0-10 的数字（已禁用）
        # score = item.get("score")
        # if score is not None:
        #     valid_score = False
        #     if isinstance(score, (int, float)):
        #         valid_score = 0 <= score <= 10
        #     elif isinstance(score, str):
        #         # 兼容字符串形式的数字
        #         try:
        #             numeric_score = float(score)
        #             valid_score = 0 <= numeric_score <= 10
        #         except ValueError:
        #             valid_score = False
        #     if not valid_score:
        #         errors.append(
        #             f"{path}.score 只允许填写 0-10 的数字，当前值: {score}"
        #         )

    def _validate_blockquote_block(
        self, block: Dict[str, Any], path: str, errors: List[str]
    ):
        """引用块内部需要至少一个子block"""
        inner = block.get("blocks")
        if not isinstance(inner, list) or not inner:
            errors.append(f"{path}.blocks 必须是非空数组")
            return
        for idx, sub_block in enumerate(inner):
            self._validate_block(sub_block, f"{path}.blocks[{idx}]", errors)

    def _validate_engineQuote_block(
        self, block: Dict[str, Any], path: str, errors: List[str]
    ):
        """单引擎发言块需标注engine并包含子blocks"""
        engine_raw = block.get("engine")
        engine = engine_raw.lower() if isinstance(engine_raw, str) else None
        if engine not in {"insight", "media", "query"}:
            errors.append(f"{path}.engine 取值非法: {engine_raw}")
        title = block.get("title")
        expected_title = ENGINE_AGENT_TITLES.get(engine) if engine else None
        if title is None:
            errors.append(f"{path}.title 缺失")
        elif not isinstance(title, str):
            errors.append(f"{path}.title 必须是字符串")
        elif expected_title and title != expected_title:
            errors.append(
                f"{path}.title 必须与engine一致，使用对应Agent名称: {expected_title}"
            )
        inner = block.get("blocks")
        if not isinstance(inner, list) or not inner:
            errors.append(f"{path}.blocks 必须是非空数组")
            return
        for idx, sub_block in enumerate(inner):
            sub_path = f"{path}.blocks[{idx}]"
            if not isinstance(sub_block, dict):
                errors.append(f"{sub_path} 必须是对象")
                continue
            if sub_block.get("type") != "paragraph":
                errors.append(f"{sub_path}.type 仅允许 paragraph")
                continue
            # 复用 paragraph 结构校验，但限制 marks
            inlines = sub_block.get("inlines")
            if not isinstance(inlines, list) or not inlines:
                errors.append(f"{sub_path}.inlines 必须是非空数组")
                continue
            for ridx, run in enumerate(inlines):
                self._validate_inline_run(run, f"{sub_path}.inlines[{ridx}]", errors)
                if not isinstance(run, dict):
                    continue
                marks = run.get("marks") or []
                if not isinstance(marks, list):
                    errors.append(f"{sub_path}.inlines[{ridx}].marks 必须是数组")
                    continue
                for midx, mark in enumerate(marks):
                    mark_type = mark.get("type") if isinstance(mark, dict) else None
                    if mark_type not in {"bold", "italic"}:
                        errors.append(
                            f"{sub_path}.inlines[{ridx}].marks[{midx}].type 仅允许 bold/italic"
                        )

    def _validate_callout_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """callout需声明tone，并至少有一个子block"""
        tone = block.get("tone")
        if tone not in {"info", "warning", "success", "danger"}:
            errors.append(f"{path}.tone 取值非法: {tone}")
        blocks = block.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            errors.append(f"{path}.blocks 必须是非空数组")
            return
        for idx, sub_block in enumerate(blocks):
            self._validate_block(sub_block, f"{path}.blocks[{idx}]", errors)

    def _validate_kpiGrid_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """KPI卡需要非空items，每项包含label/value"""
        items = block.get("items")
        if not isinstance(items, list) or not items:
            errors.append(f"{path}.items 必须是非空数组")
            return
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{path}.items[{idx}] 必须是对象")
                continue
            if "label" not in item or "value" not in item:
                errors.append(f"{path}.items[{idx}] 需要label与value")

    def _validate_widget_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """widget必须声明widgetId/type，并提供数据或数据引用"""
        if "widgetId" not in block:
            errors.append(f"{path}.widgetId 缺失")
        if "widgetType" not in block:
            errors.append(f"{path}.widgetType 缺失")
        if "data" not in block and "dataRef" not in block:
            errors.append(f"{path} 需要 data 或 dataRef 其一")

    def _validate_code_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """code block至少要有content"""
        if "content" not in block:
            errors.append(f"{path}.content 缺失")

    def _validate_math_block(self, block: Dict[str, Any], path: str, errors: List[str]):
        """数学块要求latex字段"""
        if "latex" not in block:
            errors.append(f"{path}.latex 缺失")

    def _validate_figure_block(
        self, block: Dict[str, Any], path: str, errors: List[str]
    ):
        """figure需要img对象且至少带src"""
        img = block.get("img")
        if not isinstance(img, dict):
            errors.append(f"{path}.img 必须是对象")
            return
        if "src" not in img:
            errors.append(f"{path}.img.src 缺失")

    def _validate_inline_run(
        self, run: Any, path: str, errors: List[str]
    ):
        """校验paragraph中的inline run与marks合法性"""
        if not isinstance(run, dict):
            errors.append(f"{path} 必须是对象")
            return
        if "text" not in run:
            errors.append(f"{path}.text 缺失")
        marks = run.get("marks", [])
        if marks is None:
            return
        if not isinstance(marks, list):
            errors.append(f"{path}.marks 必须是数组")
            return
        for m_idx, mark in enumerate(marks):
            if not isinstance(mark, dict):
                errors.append(f"{path}.marks[{m_idx}] 必须是对象")
                continue
            m_type = mark.get("type")
            if m_type not in ALLOWED_INLINE_MARKS:
                errors.append(f"{path}.marks[{m_idx}].type 不被支持: {m_type}")


__all__ = ["IRValidator"]
