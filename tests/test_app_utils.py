"""
测试 app/utils/ — retry_helper, forum_reader
"""

from pathlib import Path
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import patch, mock_open
import time
import json


# ==================== RetryHelper ====================

class TestRetryConfig:
    """RetryConfig 类"""

    def test_default_values(self):
        from app.utils.retry_helper import RetryConfig
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.backoff_factor == 2.0
        assert config.max_delay == 60.0
        assert len(config.retry_on_exceptions) > 0
        assert Exception in config.retry_on_exceptions

    def test_custom_values(self):
        from app.utils.retry_helper import RetryConfig
        config = RetryConfig(max_retries=5, initial_delay=2.0, backoff_factor=1.5)
        assert config.max_retries == 5
        assert config.initial_delay == 2.0
        assert config.backoff_factor == 1.5

    def test_custom_exceptions(self):
        from app.utils.retry_helper import RetryConfig
        config = RetryConfig(retry_on_exceptions=(ValueError,))
        assert config.retry_on_exceptions == (ValueError,)


class TestWithRetry:
    """with_retry 装饰器"""

    def test_success_first_try(self):
        from app.utils.retry_helper import with_retry, RetryConfig
        call_count = [0]

        @with_retry(RetryConfig(max_retries=3))
        def func():
            call_count[0] += 1
            return "ok"

        result = func()
        assert result == "ok"
        assert call_count[0] == 1

    def test_success_after_retry(self):
        from app.utils.retry_helper import with_retry, RetryConfig
        call_count = [0]

        @with_retry(RetryConfig(max_retries=3, initial_delay=0.01, backoff_factor=1.0, max_delay=0.1))
        def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("temp failure")
            return "recovered"

        with patch.object(time, "sleep"):
            result = func()

        assert result == "recovered"
        assert call_count[0] == 3

    def test_all_retries_fail_then_raise(self):
        from app.utils.retry_helper import with_retry, RetryConfig
        call_count = [0]

        @with_retry(RetryConfig(max_retries=2, initial_delay=0.01, backoff_factor=1.0, max_delay=0.1))
        def func():
            call_count[0] += 1
            raise ConnectionError("persistent failure")

        with patch.object(time, "sleep"):
            with pytest.raises(ConnectionError):
                func()

        assert call_count[0] == 3  # 1 initial + 2 retries

    def test_non_retryable_exception_raises_immediately(self):
        from app.utils.retry_helper import with_retry, RetryConfig
        config = RetryConfig(retry_on_exceptions=(ConnectionError,))

        @with_retry(config)
        def func():
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            func()

    def test_default_config_used(self):
        from app.utils.retry_helper import with_retry

        @with_retry()
        def func():
            return "ok"

        assert func() == "ok"

    def test_backoff_delay_calculation(self):
        from app.utils.retry_helper import with_retry, RetryConfig
        delays = []

        original_sleep = time.sleep

        def capture_sleep(delay):
            delays.append(delay)

        call_count = [0]

        @with_retry(RetryConfig(max_retries=3, initial_delay=1.0, backoff_factor=2.0, max_delay=60.0))
        def func():
            call_count[0] += 1
            if call_count[0] < 4:
                raise ConnectionError("fail")
            return "ok"

        with patch.object(time, "sleep", capture_sleep):
            func()

        # delays: 1st retry = 1*2^0=1, 2nd = 1*2^1=2, 3rd = 1*2^2=4
        assert len(delays) == 3
        assert delays == pytest.approx([1.0, 2.0, 4.0], rel=0.1)

    def test_max_delay_capped(self):
        from app.utils.retry_helper import with_retry, RetryConfig
        delays = []

        def capture_sleep(delay):
            delays.append(delay)

        call_count = [0]

        @with_retry(RetryConfig(max_retries=5, initial_delay=1.0, backoff_factor=10.0, max_delay=5.0))
        def func():
            call_count[0] += 1
            raise ConnectionError("fail")

        with patch.object(time, "sleep", capture_sleep):
            with pytest.raises(ConnectionError):
                func()

        # All delays should be capped at max_delay=5.0
        for d in delays:
            assert d <= 5.0


class TestRetryOnNetworkError:
    """retry_on_network_error 装饰器"""

    def test_basic(self):
        from app.utils.retry_helper import retry_on_network_error

        @retry_on_network_error(max_retries=2)
        def func():
            return "ok"

        assert func() == "ok"


class TestWithGracefulRetry:
    """with_graceful_retry 装饰器"""

    def test_returns_default_on_failure(self):
        from app.utils.retry_helper import with_graceful_retry, RetryConfig

        @with_graceful_retry(
            RetryConfig(max_retries=2, initial_delay=0.01, backoff_factor=1.0, max_delay=0.1),
            default_return="fallback"
        )
        def func():
            raise ConnectionError("fail")

        with patch.object(time, "sleep"):
            result = func()

        assert result == "fallback"

    def test_non_retryable_returns_default(self):
        from app.utils.retry_helper import with_graceful_retry, RetryConfig
        config = RetryConfig(retry_on_exceptions=(ConnectionError,))

        @with_graceful_retry(config, default_return="fallback")
        def func():
            raise ValueError("not retryable")

        result = func()
        assert result == "fallback"

    def test_success_returns_result(self):
        from app.utils.retry_helper import with_graceful_retry

        @with_graceful_retry(default_return="fallback")
        def func():
            return "success"

        assert func() == "success"


class TestMakeRetryableRequest:
    """make_retryable_request 函数"""

    def test_success(self):
        from app.utils.retry_helper import make_retryable_request

        def request_func():
            return "data"

        result = make_retryable_request(request_func, max_retries=3)
        assert result == "data"

    def test_failure_raises(self):
        from app.utils.retry_helper import make_retryable_request

        def request_func():
            raise ConnectionError("fail")

        with patch.object(time, "sleep"):
            with pytest.raises(ConnectionError):
                make_retryable_request(request_func, max_retries=2)


class TestPredefinedConfigs:
    """预定义重试配置"""

    def test_llm_retry_config(self):
        from app.utils.retry_helper import LLM_RETRY_CONFIG
        assert LLM_RETRY_CONFIG.max_retries == 6
        assert LLM_RETRY_CONFIG.initial_delay == 60.0

    def test_search_api_retry_config(self):
        from app.utils.retry_helper import SEARCH_API_RETRY_CONFIG
        assert SEARCH_API_RETRY_CONFIG.max_retries == 5
        assert SEARCH_API_RETRY_CONFIG.initial_delay == 2.0

    def test_db_retry_config(self):
        from app.utils.retry_helper import DB_RETRY_CONFIG
        assert DB_RETRY_CONFIG.max_retries == 5
        assert DB_RETRY_CONFIG.initial_delay == 1.0
        assert DB_RETRY_CONFIG.max_delay == 10.0


# ==================== ForumReader ====================

class TestGetLatestHostSpeech:
    """get_latest_host_speech 函数（从 EventBus 内存缓存读取）"""

    @staticmethod
    def _set_cache(value):
        import app.utils.forum_reader as fr
        with fr._cache_lock:
            fr._latest_host_speech = value

    def test_returns_cached_speech(self):
        from app.utils.forum_reader import get_latest_host_speech

        self._set_cache("这是一条HOST发言")
        try:
            assert get_latest_host_speech() == "这是一条HOST发言"
        finally:
            self._set_cache(None)

    def test_returns_none_when_cache_empty(self):
        from app.utils.forum_reader import get_latest_host_speech

        self._set_cache(None)
        assert get_latest_host_speech() is None

    def test_eventbus_subscriber_updates_cache(self):
        import app.utils.forum_reader as fr

        self._set_cache(None)
        try:
            fr._on_forum_message("forum_message", {"type": "host", "content": "新的HOST发言"})
            with fr._cache_lock:
                assert fr._latest_host_speech == "新的HOST发言"
        finally:
            self._set_cache(None)

    def test_ignores_non_host_messages(self):
        import app.utils.forum_reader as fr

        self._set_cache("已有发言")
        try:
            fr._on_forum_message("forum_message", {"type": "agent", "content": "不是HOST"})
            fr._on_forum_message("summary_ready", {"summary": "也不是HOST"})
            with fr._cache_lock:
                assert fr._latest_host_speech == "已有发言"
        finally:
            self._set_cache(None)

    def test_ignores_empty_content(self):
        import app.utils.forum_reader as fr

        self._set_cache("已有发言")
        try:
            fr._on_forum_message("forum_message", {"type": "host", "content": ""})
            with fr._cache_lock:
                assert fr._latest_host_speech == "已有发言"
        finally:
            self._set_cache(None)


class TestFormatHostSpeechForPrompt:
    """format_host_speech_for_prompt 函数"""

    def test_formats_content(self):
        from app.utils.forum_reader import format_host_speech_for_prompt
        result = format_host_speech_for_prompt("Hello World")
        assert "Hello World" in result
        assert "### 论坛主持人最新总结" in result

    def test_empty_string(self):
        from app.utils.forum_reader import format_host_speech_for_prompt
        result = format_host_speech_for_prompt("")
        assert result == ""

    def test_none(self):
        from app.utils.forum_reader import format_host_speech_for_prompt
        result = format_host_speech_for_prompt(None)
        assert result == ""
