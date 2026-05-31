"""
表格验证和修复工具。

提供对 IR 表格数据的验证和修复能力：
1. 验证表格数据格式是否符合 IR schema 要求
2. 检测嵌套 cells 结构问题
3. 验证 rows/cells 基本格式
4. 检查数据完整性
5. 本地规则修复常见问题
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class TableValidationResult:
    """表格验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    nested_cells_detected: bool = False
    empty_cells_count: int = 0
    total_cells_count: int = 0

    def has_critical_errors(self) -> bool:
        """是否有严重错误（会导致渲染失败）"""
        return not self.is_valid and len(self.errors) > 0


@dataclass
class TableRepairResult:
    """表格修复结果"""
    success: bool
    repaired_block: Optional[Dict[str, Any]]
    changes: List[str]

    def has_changes(self) -> bool:
        """是否有修改"""
        return len(self.changes) > 0


class TableValidator:
    """
    表格验证器 - 验证 IR 表格数据格式是否正确。

    验证规则：
    1. 基本结构验证：type, rows 字段
    2. 行结构验证：每行必须有 cells 数组
    3. 单元格结构验证：每个 cell 必须有 blocks 数组
    4. 嵌套 cells 检测：检测错误的嵌套 cells 结构
    5. 数据完整性验证：检查空单元格和缺失数据
    """

    def __init__(self):
        """初始化验证器"""
        pass

    def validate(self, table_block: Dict[str, Any]) -> TableValidationResult:
        """
        验证表格格式。

        Args:
            table_block: table 类型的 block，包含 type, rows 等字段

        Returns:
            TableValidationResult: 验证结果
        """
        errors: List[str] = []
        warnings: List[str] = []
        nested_cells_detected = False
        empty_cells_count = 0
        total_cells_count = 0

        # 1. 基本结构验证
        if not isinstance(table_block, dict):
            errors.append("table_block 必须是字典类型")
            return TableValidationResult(
                False, errors, warnings, nested_cells_detected,
                empty_cells_count, total_cells_count
            )

        # 2. 检查 type
        block_type = table_block.get('type')
        if block_type != 'table':
            errors.append(f"block type 应为 'table'，实际为 '{block_type}'")

        # 3. 验证 rows 字段
        rows = table_block.get('rows')
        if rows is None:
            errors.append("缺少 rows 字段")
            return TableValidationResult(
                False, errors, warnings, nested_cells_detected,
                empty_cells_count, total_cells_count
            )

        if not isinstance(rows, list):
            errors.append("rows 必须是数组类型")
            return TableValidationResult(
                False, errors, warnings, nested_cells_detected,
                empty_cells_count, total_cells_count
            )

        if len(rows) == 0:
            warnings.append("rows 数组为空，表格可能无法正常显示")

        # 4. 验证每一行
        for row_idx, row in enumerate(rows):
            row_result = self._validate_row(row, row_idx)
            errors.extend(row_result['errors'])
            warnings.extend(row_result['warnings'])
            if row_result['nested_cells_detected']:
                nested_cells_detected = True
            empty_cells_count += row_result['empty_cells_count']
            total_cells_count += row_result['total_cells_count']

        # 5. 检查列数一致性
        column_counts = []
        for row in rows:
            if isinstance(row, dict):
                cells = row.get('cells', [])
                if isinstance(cells, list):
                    col_count = 0
                    for cell in cells:
                        if isinstance(cell, dict):
                            col_count += int(cell.get('colspan', 1))
                        else:
                            col_count += 1
                    column_counts.append(col_count)

        if column_counts and len(set(column_counts)) > 1:
            warnings.append(
                f"各行列数不一致: {column_counts}，可能导致渲染问题"
            )

        # 6. 空单元格警告
        if total_cells_count > 0 and empty_cells_count > total_cells_count * 0.5:
            warnings.append(
                f"超过50%的单元格为空 ({empty_cells_count}/{total_cells_count})，"
                "表格可能缺少数据"
            )

        is_valid = len(errors) == 0
        return TableValidationResult(
            is_valid, errors, warnings, nested_cells_detected,
            empty_cells_count, total_cells_count
        )

    def _validate_row(self, row: Any, row_idx: int) -> Dict[str, Any]:
        """验证单行"""
        result = {
            'errors': [],
            'warnings': [],
            'nested_cells_detected': False,
            'empty_cells_count': 0,
            'total_cells_count': 0,
        }

        if not isinstance(row, dict):
            result['errors'].append(f"rows[{row_idx}] 必须是对象类型")
            return result

        cells = row.get('cells')
        if cells is None:
            result['errors'].append(f"rows[{row_idx}] 缺少 cells 字段")
            return result

        if not isinstance(cells, list):
            result['errors'].append(f"rows[{row_idx}].cells 必须是数组类型")
            return result

        if len(cells) == 0:
            result['warnings'].append(f"rows[{row_idx}].cells 数组为空")

        # 验证每个单元格
        for cell_idx, cell in enumerate(cells):
            cell_result = self._validate_cell(cell, row_idx, cell_idx)
            result['errors'].extend(cell_result['errors'])
            result['warnings'].extend(cell_result['warnings'])
            if cell_result['nested_cells_detected']:
                result['nested_cells_detected'] = True
            if cell_result['is_empty']:
                result['empty_cells_count'] += 1
            result['total_cells_count'] += 1

        return result

    def _validate_cell(self, cell: Any, row_idx: int, cell_idx: int) -> Dict[str, Any]:
        """验证单个单元格"""
        result = {
            'errors': [],
            'warnings': [],
            'nested_cells_detected': False,
            'is_empty': False,
        }

        if not isinstance(cell, dict):
            result['errors'].append(
                f"rows[{row_idx}].cells[{cell_idx}] 必须是对象类型"
            )
            return result

        # 检测嵌套 cells 结构（这是常见的 LLM 错误）
        if 'cells' in cell and 'blocks' not in cell:
            result['nested_cells_detected'] = True
            result['errors'].append(
                f"rows[{row_idx}].cells[{cell_idx}] 检测到错误的嵌套 cells 结构，"
                "应该是 blocks 而不是 cells"
            )
            return result

        # 验证 blocks 字段
        blocks = cell.get('blocks')
        if blocks is None:
            result['errors'].append(
                f"rows[{row_idx}].cells[{cell_idx}] 缺少 blocks 字段"
            )
            return result

        if not isinstance(blocks, list):
            result['errors'].append(
                f"rows[{row_idx}].cells[{cell_idx}].blocks 必须是数组类型"
            )
            return result

        # 检查是否为空
        if len(blocks) == 0:
            result['is_empty'] = True
        else:
            # 检查 blocks 内容是否有效
            has_content = False
            for block in blocks:
                if isinstance(block, dict):
                    # 检查 paragraph 的 inlines
                    if block.get('type') == 'paragraph':
                        inlines = block.get('inlines', [])
                        for inline in inlines:
                            if isinstance(inline, dict):
                                text = inline.get('text', '')
                                if text and text.strip():
                                    has_content = True
                                    break
                    # 检查其他类型的 text/content
                    elif block.get('text') or block.get('content'):
                        has_content = True
                        break
                if has_content:
                    break

            if not has_content:
                result['is_empty'] = True

        # 验证 colspan/rowspan
        colspan = cell.get('colspan')
        if colspan is not None:
            if not isinstance(colspan, int) or colspan < 1:
                result['warnings'].append(
                    f"rows[{row_idx}].cells[{cell_idx}].colspan 值无效: {colspan}"
                )

        rowspan = cell.get('rowspan')
        if rowspan is not None:
            if not isinstance(rowspan, int) or rowspan < 1:
                result['warnings'].append(
                    f"rows[{row_idx}].cells[{cell_idx}].rowspan 值无效: {rowspan}"
                )

        return result

    def can_render(self, table_block: Dict[str, Any]) -> bool:
        """
        判断表格是否能正常渲染（快速检查）。

        Args:
            table_block: table 类型的 block

        Returns:
            bool: 是否能正常渲染
        """
        result = self.validate(table_block)
        return result.is_valid

    def has_nested_cells(self, table_block: Dict[str, Any]) -> bool:
        """
        检测表格是否包含嵌套 cells 结构。

        Args:
            table_block: table 类型的 block

        Returns:
            bool: 是否包含嵌套 cells
        """
        result = self.validate(table_block)
        return result.nested_cells_detected


class TableRepairer:
    """
    表格修复器 - 尝试修复表格数据。

    修复策略：
    1. 展平嵌套 cells 结构
    2. 补充缺失的 blocks 字段
    3. 规范化单元格结构
    4. 验证修复结果
    """

    def __init__(self, validator: Optional[TableValidator] = None):
        """
        初始化修复器。

        Args:
            validator: 表格验证器实例
        """
        self.validator = validator or TableValidator()

    def repair(
        self,
        table_block: Dict[str, Any],
        validation_result: Optional[TableValidationResult] = None
    ) -> TableRepairResult:
        """
        尝试修复表格数据。

        Args:
            table_block: table 类型的 block
            validation_result: 验证结果（可选，如果没有会先进行验证）

        Returns:
            TableRepairResult: 修复结果
        """
        # 1. 如果没有验证结果，先验证
        if validation_result is None:
            validation_result = self.validator.validate(table_block)

        # 2. 如果已经有效，返回原数据
        if validation_result.is_valid and not validation_result.nested_cells_detected:
            return TableRepairResult(True, table_block, [])

        # 3. 尝试修复
        repaired = copy.deepcopy(table_block)
        changes: List[str] = []

        # 确保基本结构
        if 'type' not in repaired:
            repaired['type'] = 'table'
            changes.append("添加缺失的 type 字段")

        if 'rows' not in repaired or not isinstance(repaired.get('rows'), list):
            repaired['rows'] = []
            changes.append("添加缺失的 rows 字段")

        # 修复每一行
        repaired_rows: List[Dict[str, Any]] = []
        for row_idx, row in enumerate(repaired.get('rows', [])):
            repaired_row, row_changes = self._repair_row(row, row_idx)
            repaired_rows.append(repaired_row)
            changes.extend(row_changes)

        repaired['rows'] = repaired_rows

        # 4. 验证修复结果
        repaired_validation = self.validator.validate(repaired)
        success = repaired_validation.is_valid

        if not success:
            logger.warning(
                f"表格修复后仍有问题: {repaired_validation.errors}"
            )

        return TableRepairResult(success, repaired, changes)

    def _repair_row(
        self, row: Any, row_idx: int
    ) -> Tuple[Dict[str, Any], List[str]]:
        """修复单行"""
        changes: List[str] = []

        if not isinstance(row, dict):
            return {'cells': [self._default_cell()]}, [
                f"rows[{row_idx}] 类型错误，已重建"
            ]

        repaired_row = dict(row)

        # 确保有 cells 字段
        if 'cells' not in repaired_row or not isinstance(repaired_row.get('cells'), list):
            repaired_row['cells'] = [self._default_cell()]
            changes.append(f"rows[{row_idx}] 添加缺失的 cells 字段")
            return repaired_row, changes

        # 修复每个单元格
        repaired_cells: List[Dict[str, Any]] = []
        for cell_idx, cell in enumerate(repaired_row.get('cells', [])):
            if isinstance(cell, dict) and 'cells' in cell and 'blocks' not in cell:
                # 展平嵌套 cells
                flattened = self._flatten_nested_cells(cell)
                repaired_cells.extend(flattened)
                changes.append(
                    f"rows[{row_idx}].cells[{cell_idx}] 展平嵌套 cells 结构"
                )
            else:
                repaired_cell, cell_changes = self._repair_cell(cell, row_idx, cell_idx)
                repaired_cells.append(repaired_cell)
                changes.extend(cell_changes)

        repaired_row['cells'] = repaired_cells
        return repaired_row, changes

    def _repair_cell(
        self, cell: Any, row_idx: int, cell_idx: int
    ) -> Tuple[Dict[str, Any], List[str]]:
        """修复单个单元格"""
        changes: List[str] = []

        if not isinstance(cell, dict):
            if isinstance(cell, (str, int, float)):
                return {
                    'blocks': [self._text_to_paragraph(str(cell))]
                }, [f"rows[{row_idx}].cells[{cell_idx}] 转换为标准格式"]
            return self._default_cell(), [
                f"rows[{row_idx}].cells[{cell_idx}] 类型错误，已重建"
            ]

        repaired_cell = dict(cell)

        # 确保有 blocks 字段
        if 'blocks' not in repaired_cell:
            # 尝试从其他字段提取内容
            text = ''
            for key in ('text', 'content', 'value'):
                if key in repaired_cell and repaired_cell[key]:
                    text = str(repaired_cell[key])
                    break

            repaired_cell['blocks'] = [self._text_to_paragraph(text or '')]
            changes.append(
                f"rows[{row_idx}].cells[{cell_idx}] 添加缺失的 blocks 字段"
            )
        elif not isinstance(repaired_cell['blocks'], list):
            repaired_cell['blocks'] = [self._text_to_paragraph('')]
            changes.append(
                f"rows[{row_idx}].cells[{cell_idx}].blocks 类型错误，已重建"
            )
        elif len(repaired_cell['blocks']) == 0:
            repaired_cell['blocks'] = [self._text_to_paragraph('')]
            changes.append(
                f"rows[{row_idx}].cells[{cell_idx}].blocks 为空，添加默认内容"
            )

        return repaired_cell, changes

    def _flatten_nested_cells(self, cell: Dict[str, Any]) -> List[Dict[str, Any]]:
        """展平嵌套的 cells 结构"""
        nested_cells = cell.get('cells', [])
        if not isinstance(nested_cells, list):
            return [self._default_cell()]

        result: List[Dict[str, Any]] = []
        for nested in nested_cells:
            if isinstance(nested, dict):
                if 'blocks' in nested and 'cells' not in nested:
                    # 正常的 cell
                    result.append(nested)
                elif 'cells' in nested and 'blocks' not in nested:
                    # 继续递归展平
                    result.extend(self._flatten_nested_cells(nested))
                else:
                    # 尝试修复
                    repaired, _ = self._repair_cell(nested, 0, 0)
                    result.append(repaired)
            elif isinstance(nested, (str, int, float)):
                result.append({
                    'blocks': [self._text_to_paragraph(str(nested))]
                })

        return result if result else [self._default_cell()]

    def _default_cell(self) -> Dict[str, Any]:
        """创建默认单元格"""
        return {
            'blocks': [self._text_to_paragraph('')]
        }

    def _text_to_paragraph(self, text: str) -> Dict[str, Any]:
        """将文本转换为 paragraph block"""
        return {
            'type': 'paragraph',
            'inlines': [{'text': text, 'marks': []}]
        }


def create_table_validator() -> TableValidator:
    """创建表格验证器实例"""
    return TableValidator()


def create_table_repairer(
    validator: Optional[TableValidator] = None
) -> TableRepairer:
    """创建表格修复器实例"""
    return TableRepairer(validator)


__all__ = [
    'TableValidator',
    'TableRepairer',
    'TableValidationResult',
    'TableRepairResult',
    'create_table_validator',
    'create_table_repairer',
]
