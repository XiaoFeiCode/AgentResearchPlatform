"""
Report Engine 配置 — 继承全局 Settings，追加报告专用字段。
"""
from pathlib import Path
from pydantic import Field
from typing import Optional

from app.config import Settings as AppSettings


class Settings(AppSettings):
    """Report Engine 配置（继承全局，追加报告专用字段）。"""
    MAX_CONTENT_LENGTH: int = Field(200000, description="最大内容长度")
    OUTPUT_DIR: str = Field("data/report/final", description="主输出目录")
    CHAPTER_OUTPUT_DIR: str = Field("data/report/chapters", description="章节JSON缓存目录")
    DOCUMENT_IR_OUTPUT_DIR: str = Field("data/report/ir", description="整本IR/Manifest输出目录")
    CHAPTER_JSON_MAX_ATTEMPTS: int = Field(2, description="章节JSON解析失败时的最大尝试次数")
    TEMPLATE_DIR: str = Field(
        default=str(Path(__file__).resolve().parent.parent / "report_template"),
        description="多模板目录",
    )
    API_TIMEOUT: float = Field(900.0, description="单API超时时间（秒）")
    MAX_RETRY_DELAY: float = Field(180.0, description="最大重试间隔（秒）")
    MAX_RETRIES: int = Field(8, description="最大重试次数")
    LOG_FILE: str = Field("logs/report.log", description="日志输出文件")
    ENABLE_PDF_EXPORT: bool = Field(True, description="是否允许导出PDF")
    CHART_STYLE: str = Field("modern", description="图表样式：modern/classic/")
    JSON_ERROR_LOG_DIR: str = Field("logs/json_repair_failures", description="无法修复的JSON块落盘目录")


settings = Settings()


def print_config(config: Settings):
    """将当前配置项按人类可读格式输出到日志。"""
    from loguru import logger
    message = ""
    message += "\n=== Report Engine 配置 ===\n"
    message += f"LLM 模型: {config.REPORT_ENGINE_MODEL_NAME}\n"
    message += f"LLM Base URL: {config.REPORT_ENGINE_BASE_URL or '(默认)'}\n"
    message += f"最大内容长度: {config.MAX_CONTENT_LENGTH}\n"
    message += f"输出目录: {config.OUTPUT_DIR}\n"
    message += f"章节JSON目录: {config.CHAPTER_OUTPUT_DIR}\n"
    message += f"章节JSON最大尝试次数: {config.CHAPTER_JSON_MAX_ATTEMPTS}\n"
    message += f"整本IR目录: {config.DOCUMENT_IR_OUTPUT_DIR}\n"
    message += f"模板目录: {config.TEMPLATE_DIR}\n"
    message += f"API 超时时间: {config.API_TIMEOUT} 秒\n"
    message += f"最大重试间隔: {config.MAX_RETRY_DELAY} 秒\n"
    message += f"最大重试次数: {config.MAX_RETRIES}\n"
    message += f"日志文件: {config.LOG_FILE}\n"
    message += f"PDF 导出: {config.ENABLE_PDF_EXPORT}\n"
    message += f"图表样式: {config.CHART_STYLE}\n"
    message += f"LLM API Key: {'已配置' if config.REPORT_ENGINE_API_KEY else '未配置'}\n"
    message += "=========================\n"
    logger.info(message)
