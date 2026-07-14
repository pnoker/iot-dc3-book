"""
LLM 客户端 - DeepSeek (chat) + OpenRouter (embedding)
带重试、超时、日志
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError
from tenacity import RetryCallState, Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.log import get_logger
from core.utils import parse_json_from_llm

logger = get_logger("llm")

# 需要重试的异常类型
_RETRYABLE = (ConnectionError, TimeoutError, OSError, APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)

ResultT = TypeVar("ResultT")

if TYPE_CHECKING:
    from collections.abc import Callable


class LLMClient:
    """统一的 LLM 调用客户端（延迟初始化）"""

    def __init__(
            self,
            base_url: str,
            api_key: str,
            model: str,
            temperature: float = 0.7,
            max_tokens: int = 8192,
            embed_base_url: str = "",
            embed_api_key: str = "",
            embed_model: str = "",
            embed_timeout: float | None = None,
            embed_retry_attempts: int | None = None,
            embed_retry_min_seconds: float | None = None,
            embed_retry_max_seconds: float | None = None,
            timeout: float = 120.0,
            retry_attempts: int = 3,
            retry_min_seconds: float = 2.0,
            retry_max_seconds: float = 30.0,
            json_retry_attempts: int = 2,
    ) -> None:
        if retry_attempts <= 0:
            raise ValueError("retry_attempts 必须大于 0")
        if retry_min_seconds < 0:
            raise ValueError("retry_min_seconds 不能小于 0")
        if retry_max_seconds < retry_min_seconds:
            raise ValueError("retry_max_seconds 必须不小于 retry_min_seconds")
        if json_retry_attempts <= 0:
            raise ValueError("json_retry_attempts 必须大于 0")
        resolved_embed_timeout = timeout if embed_timeout is None else embed_timeout
        resolved_embed_retry_attempts = retry_attempts if embed_retry_attempts is None else embed_retry_attempts
        resolved_embed_retry_min_seconds = retry_min_seconds if embed_retry_min_seconds is None else embed_retry_min_seconds
        resolved_embed_retry_max_seconds = retry_max_seconds if embed_retry_max_seconds is None else embed_retry_max_seconds
        if resolved_embed_timeout <= 0:
            raise ValueError("embed_timeout 必须大于 0")
        if resolved_embed_retry_attempts <= 0:
            raise ValueError("embed_retry_attempts 必须大于 0")
        if resolved_embed_retry_min_seconds < 0:
            raise ValueError("embed_retry_min_seconds 不能小于 0")
        if resolved_embed_retry_max_seconds < resolved_embed_retry_min_seconds:
            raise ValueError("embed_retry_max_seconds 必须不小于 embed_retry_min_seconds")
        # Chat config (DeepSeek)
        self._base_url = base_url
        self._api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._timeout = timeout
        self._retry_attempts = retry_attempts
        self._retry_min_seconds = retry_min_seconds
        self._retry_max_seconds = retry_max_seconds
        self._json_retry_attempts = json_retry_attempts
        self._client: OpenAI | None = None

        # Embedding config (OpenRouter)
        self._embed_base_url = embed_base_url
        self._embed_api_key = embed_api_key
        self._embed_model = embed_model
        self._embed_timeout = resolved_embed_timeout
        self._embed_retry_attempts = resolved_embed_retry_attempts
        self._embed_retry_min_seconds = resolved_embed_retry_min_seconds
        self._embed_retry_max_seconds = resolved_embed_retry_max_seconds
        self._embed_client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            if not self._api_key:
                raise ValueError("未配置 Chat API Key。请在 config/llm.yaml 中引用 ${DEEPSEEK_API_KEY}，并在 .env 或 shell 环境变量中设置。")
            self._client = OpenAI(
                base_url=self._base_url,
                api_key=self._api_key,
                timeout=self._timeout,
                max_retries=0,
            )
            logger.info(
                "Chat 客户端初始化: %s / %s, timeout=%ss, retry=%d",
                self._base_url,
                self.model,
                self._timeout,
                self._retry_attempts,
            )
        return self._client

    @property
    def embed_client(self) -> OpenAI:
        if self._embed_client is None:
            if not self._embed_base_url:
                raise ValueError("未配置 Embedding base_url。请在 config/llm.yaml 的 embedding.base_url 中显式设置。")
            if not self._embed_api_key:
                raise ValueError("未配置 Embedding API Key。请在 config/llm.yaml 中引用 ${OPENROUTER_API_KEY}，并在 .env 或 shell 环境变量中设置。")
            if not self._embed_model:
                raise ValueError("未配置 Embedding model。请在 config/llm.yaml 的 embedding.model 中显式设置。")
            self._embed_client = OpenAI(
                base_url=self._embed_base_url,
                api_key=self._embed_api_key,
                timeout=self._embed_timeout,
                max_retries=0,
            )
            logger.info(
                "Embedding 客户端初始化: %s / %s, timeout=%ss, retry=%d",
                self._embed_base_url,
                self._embed_model,
                self._embed_timeout,
                self._embed_retry_attempts,
            )
        return self._embed_client

    def chat(
            self,
            system_prompt: str,
            user_prompt: str,
            temperature: float | None = None,
            max_tokens: int | None = None,
            response_format: dict[str, str] | None = None,
            timeout: float | None = None,
            retry_attempts: int | None = None,
    ) -> str:
        """单轮对话（按配置自动重试）。"""
        logger.debug("Chat 请求: model=%s, user_len=%d", self.model, len(user_prompt))
        try:
            return self._run_with_retry(
                "Chat",
                lambda: self._chat_once(system_prompt, user_prompt, temperature, max_tokens, response_format, timeout),
                retry_attempts=retry_attempts,
            )
        except _RETRYABLE as exc:
            logger.warning("Chat 调用失败: model=%s, %s", self.model, exc)
            raise
        except Exception:
            logger.exception("Chat 调用失败: model=%s", self.model)
            raise

    def chat_json(
            self,
            system_prompt: str,
            user_prompt: str,
            temperature: float | None = None,
            max_tokens: int | None = None,
            timeout: float | None = None,
            retry_attempts: int | None = None,
            json_retry_attempts: int | None = None,
    ) -> dict[str, object]:
        """请求 JSON object 响应并解析。"""
        attempts = self._json_retry_attempts if json_retry_attempts is None else json_retry_attempts
        if attempts <= 0:
            raise ValueError("json_retry_attempts 必须大于 0")
        last_error: ValueError | None = None
        for attempt in range(1, attempts + 1):
            content = self.chat(
                system_prompt,
                user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=timeout,
                retry_attempts=retry_attempts,
            )
            try:
                return parse_json_from_llm(content)
            except ValueError as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                logger.warning(
                    "JSON 响应解析失败，准备重新请求 (%d/%d): %s",
                    attempt,
                    attempts,
                    exc,
                )
        if last_error is not None:
            raise last_error
        raise RuntimeError("JSON 请求未执行")

    def embed(self, text: str) -> list[float]:
        """文本嵌入（按配置自动重试）。"""
        self._require_embed_model()
        logger.debug("Embed 请求: model=%s, text_len=%d", self._embed_model, len(text))
        try:
            return self._run_with_retry(
                "Embed",
                lambda: self._embed_once(text),
                retry_attempts=self._embed_retry_attempts,
                retry_min_seconds=self._embed_retry_min_seconds,
                retry_max_seconds=self._embed_retry_max_seconds,
            )
        except Exception:
            logger.exception("Embed 调用失败: model=%s", self._embed_model)
            raise

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """批量文本嵌入（按配置自动重试）。"""
        if not texts:
            return []
        self._require_embed_model()
        logger.debug("Embed 批量请求: model=%s, count=%d", self._embed_model, len(texts))
        try:
            return self._run_with_retry(
                "Embed 批量",
                lambda: self._embed_many_once(texts),
                retry_attempts=self._embed_retry_attempts,
                retry_min_seconds=self._embed_retry_min_seconds,
                retry_max_seconds=self._embed_retry_max_seconds,
            )
        except Exception:
            logger.exception("Embed 批量调用失败: model=%s", self._embed_model)
            raise

    def _chat_once(
            self,
            system_prompt: str,
            user_prompt: str,
            temperature: float | None,
            max_tokens: int | None,
            response_format: dict[str, str] | None,
            timeout: float | None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        if timeout is not None:
            kwargs["timeout"] = timeout
        resp = self.client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or ""
        logger.debug("Chat 响应: len=%d", len(content))
        return content

    def _embed_once(self, text: str) -> list[float]:
        resp = self.embed_client.embeddings.create(
            model=self._embed_model,
            input=text,
        )
        return resp.data[0].embedding

    def _embed_many_once(self, texts: list[str]) -> list[list[float]]:
        resp = self.embed_client.embeddings.create(
            model=self._embed_model,
            input=texts,
        )
        return [item.embedding for item in resp.data]

    def _run_with_retry(
            self,
            operation: str,
            action: Callable[[], ResultT],
            *,
            retry_attempts: int | None = None,
            retry_min_seconds: float | None = None,
            retry_max_seconds: float | None = None,
    ) -> ResultT:
        attempts = self._retry_attempts if retry_attempts is None else retry_attempts
        min_seconds = self._retry_min_seconds if retry_min_seconds is None else retry_min_seconds
        max_seconds = self._retry_max_seconds if retry_max_seconds is None else retry_max_seconds
        for attempt in Retrying(
                stop=stop_after_attempt(attempts),
                wait=wait_exponential(multiplier=1, min=min_seconds, max=max_seconds),
                retry=retry_if_exception_type(_RETRYABLE),
                before_sleep=lambda retry_state: self._log_retry(operation, retry_state, attempts),
                reraise=True,
        ):
            with attempt:
                return action()
        raise RuntimeError(f"{operation} 重试未执行")

    def _log_retry(self, operation: str, retry_state: RetryCallState, attempts: int) -> None:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        sleep_seconds = retry_state.next_action.sleep if retry_state.next_action else 0.0
        logger.warning(
            "%s 调用失败，%.1fs 后重试 (%d/%d): %s",
            operation,
            sleep_seconds,
            retry_state.attempt_number,
            attempts,
            exc,
        )

    def _require_embed_model(self) -> None:
        if not self._embed_model:
            raise ValueError("未配置 Embedding model。请在 config/llm.yaml 的 embedding.model 中显式设置。")
