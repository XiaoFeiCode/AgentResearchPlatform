"""System service — configuration and legacy log helpers."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_KEYS = [
    'HOST', 'PORT',
    'DB_DIALECT', 'DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'DB_CHARSET',
    'INSIGHT_ENGINE_API_KEY', 'INSIGHT_ENGINE_BASE_URL', 'INSIGHT_ENGINE_MODEL_NAME',
    'MEDIA_ENGINE_API_KEY', 'MEDIA_ENGINE_BASE_URL', 'MEDIA_ENGINE_MODEL_NAME',
    'QUERY_ENGINE_API_KEY', 'QUERY_ENGINE_BASE_URL', 'QUERY_ENGINE_MODEL_NAME',
    'REPORT_ENGINE_API_KEY', 'REPORT_ENGINE_BASE_URL', 'REPORT_ENGINE_MODEL_NAME',
    'FORUM_HOST_API_KEY', 'FORUM_HOST_BASE_URL', 'FORUM_HOST_MODEL_NAME',
    'KEYWORD_OPTIMIZER_API_KEY', 'KEYWORD_OPTIMIZER_BASE_URL', 'KEYWORD_OPTIMIZER_MODEL_NAME',
    'SENTINEL_SPIDER_API_KEY', 'SENTINEL_SPIDER_BASE_URL', 'SENTINEL_SPIDER_MODEL_NAME',
    'TAVILY_API_KEY', 'SEARCH_TOOL_TYPE', 'BOCHA_BASE_URL', 'BOCHA_WEB_SEARCH_API_KEY',
    'ANSPIRE_BASE_URL', 'ANSPIRE_API_KEY',
]


def read_config_values() -> Dict[str, str]:
    try:
        from app import config as config_module
        config_module.reload_settings()
        current_settings = config_module.settings
        values = {}
        for key in CONFIG_KEYS:
            value = getattr(current_settings, key, None)
            values[key] = '' if value is None else str(value)
        return values
    except Exception:
        logger.exception("读取配置失败")
        return {}


def write_config_values(updates: Dict[str, Any]) -> None:
    project_root = PROJECT_ROOT
    env_file_path = project_root / ".env"

    env_lines: List[str] = []
    env_key_indices: Dict[str, int] = {}
    if env_file_path.exists():
        env_lines = env_file_path.read_text(encoding='utf-8').splitlines()
        for i, line in enumerate(env_lines):
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                key = line_stripped.split('=')[0].strip()
                env_key_indices[key] = i

    for key, raw_value in updates.items():
        if raw_value is None or raw_value == '':
            env_value = ''
        elif isinstance(raw_value, (int, float)):
            env_value = str(raw_value)
        elif isinstance(raw_value, bool):
            env_value = 'True' if raw_value else 'False'
        else:
            value_str = str(raw_value)
            if ' ' in value_str or '\n' in value_str or '#' in value_str:
                escaped = value_str.replace('\\', '\\\\').replace('"', '\\"')
                env_value = f'"{escaped}"'
            else:
                env_value = value_str

        if key in env_key_indices:
            env_lines[env_key_indices[key]] = f'{key}={env_value}'
        else:
            env_lines.append(f'{key}={env_value}')

    env_file_path.parent.mkdir(parents=True, exist_ok=True)
    env_file_path.write_text('\n'.join(env_lines) + '\n', encoding='utf-8')

    from app import config as config_module
    config_module.reload_settings()


def write_log_to_file(app_name: str, line: str):
    try:
        log_file_path = LOG_DIR / f"{app_name}.log"
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
            f.flush()
    except Exception:
        logger.exception(f"Error writing log for {app_name}")


def read_log_from_file(app_name: str, tail_lines: Optional[int] = None) -> List[str]:
    try:
        log_file_path = LOG_DIR / f"{app_name}.log"
        if not log_file_path.exists():
            return []
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = [line.rstrip('\n\r') for line in f.readlines() if line.strip()]
            if tail_lines:
                return lines[-tail_lines:]
            return lines
    except Exception:
        logger.exception(f"Error reading log for {app_name}")
        return []


def check_app_status():
    """No-op retained for compatibility with older callers."""
    pass
