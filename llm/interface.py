"""
LLM Interface — абстрактный класс и фабрика для подключения языковых моделей.
Поддерживает OpenAI-совместимые API, LM Studio, Ollama, символьный режим
и цепочку fallback через LLMRouter.
"""

from typing import Any, Dict, Optional
import json
import logging

logger = logging.getLogger("cognicore.llm")


class BaseLLM:
    """
    Абстрактный базовый класс для LLM-интерфейсов.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.endpoint = config.get("endpoint", "")
        self.api_key = config.get("api_key", "")
        self.model_name = config.get("model_name", "")
        self.max_tokens = config.get("max_tokens", 2048)

    def generate(self, prompt: str, system: str = "",
                 temperature: float = 0.7) -> str:
        """
        Генерирует ответ.
        Должен быть переопределён в подклассах.
        """
        raise NotImplementedError("Подклассы должны реализовать generate()")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model_name})"


class NullLLM(BaseLLM):
    """
    Заглушка для режима без LLM.
    Возвращает сообщение о недоступности.
    """

    def __init__(self, config: Dict):
        super().__init__(config)

    def generate(self, prompt: str, system: str = "",
                 temperature: float = 0.7) -> str:
        return "[LLM не подключена. Настройте provider в config.yaml]"


class OpenAIAPI(BaseLLM):
    """
    Подключение к OpenAI-совместимому API (OpenAI, OpenRouter, etc.)
    """

    def __init__(self, config: Dict):
        super().__init__(config)

    def generate(self, prompt: str, system: str = "",
                 temperature: float = 0.7) -> str:
        try:
            import requests

            headers = {
                "Content-Type": "application/json",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": self.max_tokens,
            }

            url = f"{self.endpoint.rstrip('/')}/chat/completions"
            logger.info(f"OpenAI API запрос к {url}, модель {self.model_name}")

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            return data["choices"][0]["message"]["content"]

        except ImportError:
            return "[Ошибка: requests не установлен. pip install requests]"
        except Exception as e:
            logger.error(f"OpenAI API ошибка: {e}")
            return f"[Ошибка LLM: {e}]"


class LMStudioLLM(BaseLLM):
    """
    Подключение к локальному LM Studio серверу.
    """

    def __init__(self, config: Dict):
        super().__init__(config)

    def generate(self, prompt: str, system: str = "",
                 temperature: float = 0.7) -> str:
        try:
            import requests

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": self.max_tokens,
            }

            url = f"{self.endpoint.rstrip('/')}/chat/completions"
            logger.info(f"LM Studio запрос к {url}")

            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            return data["choices"][0]["message"]["content"]

        except ImportError:
            return "[Ошибка: requests не установлен. pip install requests]"
        except Exception as e:
            logger.error(f"LM Studio ошибка: {e}")
            return f"[Ошибка LM Studio: {e}]"


class OllamaLLM(BaseLLM):
    """
    Подключение к локальному Ollama серверу.
    """

    def __init__(self, config: Dict):
        super().__init__(config)

    def generate(self, prompt: str, system: str = "",
                 temperature: float = 0.7) -> str:
        try:
            import requests

            # Ollama использует другой формат
            full_prompt = f"{system}\n\n{prompt}" if system else prompt

            payload = {
                "model": self.model_name,
                "prompt": full_prompt,
                "temperature": temperature,
                "options": {
                    "num_predict": self.max_tokens,
                },
                "stream": False,
            }

            url = f"{self.endpoint.rstrip('/')}/api/generate"
            logger.info(f"Ollama запрос к {url}, модель {self.model_name}")

            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()

            return data.get("response", "")

        except ImportError:
            return "[Ошибка: requests не установлен. pip install requests]"
        except Exception as e:
            logger.error(f"Ollama ошибка: {e}")
            return f"[Ошибка Ollama: {e}]"


class LLMRouter(BaseLLM):
    """
    Роутер с цепочкой fallback между несколькими LLM-провайдерами.
    Пытается вызвать каждого по порядку; при ошибке переходит к следующему.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.chain = self._build_chain(config)

    def _build_chain(self, config):
        providers = []
        for provider_conf in config.get("llm_providers", []):
            p = provider_conf["type"]
            llm_config = {
                "endpoint": provider_conf.get("endpoint", ""),
                "api_key": provider_conf.get("api_key", ""),
                "model_name": provider_conf.get("model", ""),
                "max_tokens": provider_conf.get("max_tokens", 2048),
            }
            if p == "lmstudio":
                providers.append(LMStudioLLM(llm_config))
            elif p == "ollama":
                providers.append(OllamaLLM(llm_config))
            elif p == "openai":
                providers.append(OpenAIAPI(llm_config))
        return providers

    def generate(self, prompt: str, system: str = "",
                 temperature: float = 0.7) -> str:
        last_error = None
        for provider in self.chain:
            try:
                result = provider.generate(prompt, system, temperature)
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"Провайдер {provider} ошибка: {e}")
                continue
        return f"[Fallback: все провайдеры недоступны. Последняя ошибка: {last_error}]"

    @property
    def name(self):
        return "|".join(p.model_name for p in self.chain) if self.chain else "none"


class LLMFactory:
    """
    Фабрика для создания LLM-интерфейса по типу провайдера.
    Поддерживает как одиночного провайдера (backward compat),
    так и цепочку fallback через llm_providers.
    """

    PROVIDERS = {
        "openai": OpenAIAPI,
        "lmstudio": LMStudioLLM,
        "ollama": OllamaLLM,
        "none": NullLLM,
    }

    @classmethod
    def create(cls, provider: str, config: Any) -> BaseLLM:
        """
        Создать экземпляр LLM.

        Если в config есть 'llm_providers', создаётся LLMRouter.
        Иначе — одиночный провайдер (legacy путь через llm.provider).
        """
        # Проверяем наличие цепочки провайдеров (новый формат)
        if hasattr(config, "get"):
            raw = config._config if hasattr(config, "_config") else {}
            if isinstance(raw, dict) and "llm_providers" in raw:
                logger.info("Создан LLM роутер (fallback chain)")
                return LLMRouter(raw)

        # Legacy: одиночный провайдер через llm.* ключи
        llm_config = {
            "endpoint": config.get("llm", "endpoint", default=""),
            "api_key": config.get("llm", "api_key", default=""),
            "model_name": config.get("llm", "model_name", default=""),
            "max_tokens": config.get("llm", "max_tokens", default=2048),
        }

        provider_class = cls.PROVIDERS.get(provider.lower(), NullLLM)
        logger.info(f"Создан LLM провайдер: {provider_class.__name__}")
        return provider_class(llm_config)