"""
图表验证器和修复器的测试用例。

运行测试：
    python -m pytest ReportEngine/utils/test_chart_validator.py -v
"""

import pytest
from engines.ReportEngine.utils.chart_validator import (
    ChartValidator,
    ChartRepairer,
    ValidationResult,
    RepairResult,
    create_chart_validator,
    create_chart_repairer
)


class TestChartValidator:
    """测试ChartValidator类"""

    def setup_method(self):
        """每个测试前初始化"""
        self.validator = create_chart_validator()

    def test_valid_bar_chart(self):
        """测试有效的柱状图"""
        widget_block = {
            "type": "widget",
            "widgetType": "chart.js/bar",
            "widgetId": "chart-001",
            "props": {
                "type": "bar",
                "title": "销售数据"
            },
            "data": {
                "labels": ["一月", "二月", "三月"],
                "datasets": [
                    {
                        "label": "销售额",
                        "data": [100, 200, 150]
                    }
                ]
            }
        }

        result = self.validator.validate(widget_block)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valid_line_chart(self):
        """测试有效的折线图"""
        widget_block = {
            "type": "widget",
            "widgetType": "chart.js/line",
            "widgetId": "chart-002",
            "props": {
                "type": "line"
            },
            "data": {
                "labels": ["周一", "周二", "周三"],
                "datasets": [
                    {
                        "label": "访问量",
                        "data": [50, 75, 60]
                    }
                ]
            }
        }

        result = self.validator.validate(widget_block)
        assert result.is_valid

    def test_valid_pie_chart(self):
        """测试有效的饼图"""
        widget_block = {
            "widgetType": "chart.js/pie",
            "props": {"type": "pie"},
            "data": {
                "labels": ["A", "B", "C"],
                "datasets": [
                    {
                        "data": [30, 40, 30]
                    }
                ]
            }
        }

        result = self.validator.validate(widget_block)
        assert result.is_valid

    def test_missing_widgetType(self):
        """测试缺少widgetType"""
        widget_block = {
            "props": {},
            "data": {}
        }

        result = self.validator.validate(widget_block)
        assert not result.is_valid
        assert "widgetType" in result.errors[0]

    def test_missing_data_field(self):
        """测试缺少data字段"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"}
        }

        result = self.validator.validate(widget_block)
        assert not result.is_valid
        assert "data" in result.errors[0]

    def test_missing_datasets(self):
        """测试缺少datasets"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B"]
            }
        }

        result = self.validator.validate(widget_block)
        assert not result.is_valid
        assert "datasets" in result.errors[0]

    def test_empty_datasets(self):
        """测试空datasets"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B"],
                "datasets": []
            }
        }

        result = self.validator.validate(widget_block)
        assert not result.is_valid
        assert "空" in result.errors[0]

    def test_missing_labels_for_bar_chart(self):
        """测试柱状图缺少labels"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "datasets": [
                    {
                        "label": "系列1",
                        "data": [10, 20, 30]
                    }
                ]
            }
        }

        result = self.validator.validate(widget_block)
        assert not result.is_valid
        assert "labels" in result.errors[0]

    def test_invalid_data_type(self):
        """测试数据类型错误"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B"],
                "datasets": [
                    {
                        "label": "系列1",
                        "data": ["abc", "def"]  # 应该是数值
                    }
                ]
            }
        }

        result = self.validator.validate(widget_block)
        assert not result.is_valid
        assert "数值类型" in result.errors[0]

    def test_data_length_mismatch_warning(self):
        """测试数据长度不匹配（警告）"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B", "C"],
                "datasets": [
                    {
                        "label": "系列1",
                        "data": [10, 20]  # 长度不匹配
                    }
                ]
            }
        }

        result = self.validator.validate(widget_block)
        # 长度不匹配是警告，不是错误
        assert len(result.warnings) > 0
        assert "不匹配" in result.warnings[0]

    def test_scatter_chart(self):
        """测试散点图（特殊数据格式）"""
        widget_block = {
            "widgetType": "chart.js/scatter",
            "props": {"type": "scatter"},
            "data": {
                "datasets": [
                    {
                        "label": "数据点",
                        "data": [
                            {"x": 10, "y": 20},
                            {"x": 15, "y": 25}
                        ]
                    }
                ]
            }
        }

        result = self.validator.validate(widget_block)
        assert result.is_valid

    def test_non_chart_widget(self):
        """测试非图表类型的widget（应该跳过验证）"""
        widget_block = {
            "widgetType": "custom/widget",
            "props": {},
            "data": {}
        }

        result = self.validator.validate(widget_block)
        # 非chart.js类型，跳过验证，返回valid
        assert result.is_valid


class TestChartRepairer:
    """测试ChartRepairer类"""

    def setup_method(self):
        """每个测试前初始化"""
        self.validator = create_chart_validator()
        self.repairer = create_chart_repairer(validator=self.validator)

    def test_repair_missing_props(self):
        """测试修复缺少props字段"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "data": {
                "labels": ["A", "B"],
                "datasets": [
                    {
                        "label": "系列1",
                        "data": [10, 20]
                    }
                ]
            }
        }

        result = self.repairer.repair(widget_block)
        assert result.success
        assert "props" in result.repaired_block
        assert result.method == "local"

    def test_repair_missing_chart_type(self):
        """测试修复缺少图表类型"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {},
            "data": {
                "labels": ["A", "B"],
                "datasets": [
                    {
                        "label": "系列1",
                        "data": [10, 20]
                    }
                ]
            }
        }

        result = self.repairer.repair(widget_block)
        assert result.success
        assert result.repaired_block["props"]["type"] == "bar"
        assert "图表类型" in str(result.changes)

    def test_repair_missing_datasets(self):
        """测试修复缺少datasets"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B"]
            }
        }

        result = self.repairer.repair(widget_block)
        assert result.success
        assert "datasets" in result.repaired_block["data"]
        assert isinstance(result.repaired_block["data"]["datasets"], list)

    def test_repair_missing_labels(self):
        """测试修复缺少labels"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "datasets": [
                    {
                        "label": "系列1",
                        "data": [10, 20, 30]
                    }
                ]
            }
        }

        result = self.repairer.repair(widget_block)
        assert result.success
        assert "labels" in result.repaired_block["data"]
        assert len(result.repaired_block["data"]["labels"]) == 3

    def test_repair_data_length_mismatch(self):
        """测试修复数据长度不匹配"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B", "C", "D"],
                "datasets": [
                    {
                        "label": "系列1",
                        "data": [10, 20]  # 长度不足
                    }
                ]
            }
        }

        result = self.repairer.repair(widget_block)
        assert result.success
        # 应该补充到4个元素
        assert len(result.repaired_block["data"]["datasets"][0]["data"]) == 4

    def test_repair_string_to_number(self):
        """测试修复字符串类型的数值"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B"],
                "datasets": [
                    {
                        "label": "系列1",
                        "data": ["10", "20"]  # 字符串数值
                    }
                ]
            }
        }

        result = self.repairer.repair(widget_block)
        assert result.success
        # 应该转换为数值
        assert isinstance(result.repaired_block["data"]["datasets"][0]["data"][0], float)

    def test_repair_construct_datasets_from_values(self):
        """测试从values字段构造datasets"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B"],
                "values": [10, 20]  # 使用values而不是datasets
            }
        }

        result = self.repairer.repair(widget_block)
        assert result.success
        assert "datasets" in result.repaired_block["data"]
        assert len(result.repaired_block["data"]["datasets"]) > 0

    def test_no_repair_needed(self):
        """测试不需要修复的情况"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B"],
                "datasets": [
                    {
                        "label": "系列1",
                        "data": [10, 20]
                    }
                ]
            }
        }

        result = self.repairer.repair(widget_block)
        assert result.success
        assert result.method == "none"
        assert len(result.changes) == 0

    def test_repair_adds_default_label(self):
        """测试修复添加默认label"""
        widget_block = {
            "widgetType": "chart.js/bar",
            "props": {"type": "bar"},
            "data": {
                "labels": ["A", "B"],
                "datasets": [
                    {
                        # 缺少label
                        "data": [10, 20]
                    }
                ]
            }
        }

        result = self.repairer.repair(widget_block)
        assert result.success
        assert "label" in result.repaired_block["data"]["datasets"][0]


class TestValidatorIntegration:
    """集成测试"""

    def test_full_validation_and_repair_workflow(self):
        """测试完整的验证和修复流程"""
        validator = create_chart_validator()
        repairer = create_chart_repairer(validator=validator)

        # 一个有多个问题的图表
        widget_block = {
            "widgetType": "chart.js/bar",
            "data": {
                "datasets": [
                    {
                        "data": ["10", "20", "30"]  # 字符串数值
                    }
                ]
            }
        }

        # 1. 验证（应该失败）
        validation = validator.validate(widget_block)
        assert not validation.is_valid

        # 2. 修复
        repair_result = repairer.repair(widget_block, validation)
        assert repair_result.success

        # 3. 再次验证（应该通过）
        final_validation = validator.validate(repair_result.repaired_block)
        assert final_validation.is_valid


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
