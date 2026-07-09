"""
LLM 客户端 - DeepSeek (chat) + OpenRouter (embedding)
带重试、超时、日志
"""

from __future__ import annotations

from typing import Any

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.log import get_logger
from core.utils import parse_json_from_llm

logger = get_logger("llm")

# 需要重试的异常类型
_RETRYABLE = (ConnectionError, TimeoutError, OSError, APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)


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
            timeout: float = 120.0,
    ) -> None:
        # Chat config (DeepSeek)
        self._base_url = base_url
        self._api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._timeout = timeout
        self._client: OpenAI | None = None

        # Embedding config (OpenRouter)
        self._embed_base_url = embed_base_url
        self._embed_api_key = embed_api_key
        self._embed_model = embed_model
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
            )
            logger.info("Chat 客户端初始化: %s / %s", self._base_url, self.model)
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
                timeout=self._timeout,
            )
            logger.info("Embedding 客户端初始化: %s / %s", self._embed_base_url, self._embed_model)
        return self._embed_client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    def chat(
            self,
            system_prompt: str,
            user_prompt: str,
            temperature: float | None = None,
            max_tokens: int | None = None,
            response_format: dict[str, str] | None = None,
    ) -> str:
        """单轮对话（自动重试 3 次）"""
        logger.debug("Chat 请求: model=%s, user_len=%d", self.model, len(user_prompt))
        try:
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
            resp = self.client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content or ""
            logger.debug("Chat 响应: len=%d", len(content))
            return content
        except Exception:
            logger.exception("Chat 调用失败: model=%s", self.model)
            raise

    def chat_json(
            self,
            system_prompt: str,
            user_prompt: str,
            temperature: float | None = None,
            max_tokens: int | None = None,
    ) -> dict[str, object]:
        """请求 JSON object 响应并解析。"""
        content = self.chat(
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return parse_json_from_llm(content)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    def embed(self, text: str) -> list[float]:
        """文本嵌入（自动重试 3 次）"""
        self._require_embed_model()
        logger.debug("Embed 请求: model=%s, text_len=%d", self._embed_model, len(text))
        try:
            resp = self.embed_client.embeddings.create(
                model=self._embed_model,
                input=text,
            )
            return resp.data[0].embedding
        except Exception:
            logger.exception("Embed 调用失败: model=%s", self._embed_model)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(_RETRYABLE),
        reraise=True,
    )
    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """批量文本嵌入（自动重试 3 次）"""
        if not texts:
            return []
        self._require_embed_model()
        logger.debug("Embed 批量请求: model=%s, count=%d", self._embed_model, len(texts))
        try:
            resp = self.embed_client.embeddings.create(
                model=self._embed_model,
                input=texts,
            )
            return [item.embedding for item in resp.data]
        except Exception:
            logger.exception("Embed 批量调用失败: model=%s", self._embed_model)
            raise

    def _require_embed_model(self) -> None:
        if not self._embed_model:
            raise ValueError("未配置 Embedding model。请在 config/llm.yaml 的 embedding.model 中显式设置。")
