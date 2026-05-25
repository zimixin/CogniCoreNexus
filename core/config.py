"""\
Конфигурация CogniCore Nexus.
Загружает и предоставляет доступ к настройкам из config.yaml.
Содержит NexusConfig dataclass для валидации при старте.
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import yaml


# Корень проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class NexusConfig:
    """Валидированная конфигурация системы."""
    llm_providers: List[Dict] = field(default_factory=list)
    working_memory_size: int = 10
    max_inference_steps: int = 50
    use_vectors: bool = False
    vector_backend: str = "numpy"
    search_threshold: float = 0.7
    data_dir: str = "data"
    log_level: str = "INFO"

    def validate(self):
        """Проверка границ допустимых значений."""
        assert 0 < self.working_memory_size <= 100, \
            f"working_memory_size вне допустимого диапазона: {self.working_memory_size}"
        assert 0 < self.max_inference_steps <= 500, \
            f"max_inference_steps вне диапазона: {self.max_inference_steps}"
        assert 0.0 < self.search_threshold < 1.0, \
            f"search_threshold вне (0,1): {self.search_threshold}"
        assert self.vector_backend in ("numpy", "annoy", "faiss", "none"), \
            f"Неизвестный vector_backend: {self.vector_backend}"

    @classmethod
    def from_dict(cls, data: Dict) -> "NexusConfig":
        """Создать из сырого словаря (из YAML)."""
        memory = data.get("memory", {})
        cognition = data.get("cognition", {})
        return cls(
            llm_providers=data.get("llm_providers", []),
            working_memory_size=cognition.get("working_memory_size", 10),
            max_inference_steps=cognition.get("max_inference_steps", 50),
            use_vectors=memory.get("use_vectors", False),
            vector_backend=memory.get("vector_backend", "numpy"),
            search_threshold=memory.get("search_threshold", 0.7),
            data_dir=data.get("loci", {}).get("data_dir", "data"),
            log_level=data.get("log_level", "INFO"),
        )


class Config:
    """Загрузчик и провайдер конфигурации."""

    def __init__(self, config_path: Optional[str] = None):
        self._data: Dict[str, Any] = {}
        self.config_path: Path = PROJECT_ROOT / "data" / "config.yaml"

        if config_path:
            self.config_path = Path(config_path)

        self.load()

    def load(self):
        """Загрузить конфигурацию из YAML-файла. Если файла нет — создать с настройками по умолчанию."""
        if not self.config_path.exists():
            print(f"[Config] Файл конфигурации не найден: {self.config_path}")
            print("[Config] Создаю config.yaml с настройками по умолчанию...")
            self._create_default()
            print(f"[Config] Создан {self.config_path}. Отредактируйте перед запуском.")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

        # Валидация через NexusConfig (только warn, не блокируем запуск)
        try:
            validated = NexusConfig.from_dict(self._data)
            validated.validate()
        except AssertionError as e:
            print(f"[Config] ⚠ Предупреждение валидации: {e}")

        # Убедимся, что директории для данных существуют
        self._ensure_dirs()

    def _create_default(self):
        """Создать конфиг по умолчанию."""
        default_config = """\
# CogniCore Nexus — конфигурация
llm:
  provider: "none"
  endpoint: ""
  api_key: ""
  model_name: "gpt-4o-mini"
  temperature: 0.7
  max_tokens: 2048

llm_providers: []

memory:
  use_vectors: false
  vector_backend: "numpy"
  vector_model: "all-MiniLM-L6-v2"
  search_threshold: 0.7

cognition:
  working_memory_size: 20
  max_inference_steps: 50
  max_planning_depth: 5

loci:
  data_dir: "data/loci"
  default_wings:
    - id: "wing_general"
      name: "Общее"
      rooms:
        - id: "room_general"
          name: "Общая"
          tags: ["general", "common"]
        - id: "room_system"
          name: "Система"
          tags: ["system", "meta"]

genome:
  db_path: "data/genome.db"

aaak:
  dictionary: "aaak/dictionary.yaml"
  domain_profiles_dir: "aaak/domain_profiles/"
  auto_shorten_threshold: 5

api:
  mcp_http_port: 9100
  mcp_transport: "stdio"
"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(default_config)

    def _ensure_dirs(self):
        """Создать необходимые директории для данных."""
        loci_dir = PROJECT_ROOT / self.get("loci", "data_dir", default="data/loci")
        loci_dir.mkdir(parents=True, exist_ok=True)

        genome_path = PROJECT_ROOT / self.get("genome", "db_path", default="data/genome.db")
        genome_path.parent.mkdir(parents=True, exist_ok=True)

        vectors_dir = PROJECT_ROOT / "data" / "vectors"
        vectors_dir.mkdir(parents=True, exist_ok=True)

        matrices_dir = PROJECT_ROOT / "data" / "matrices"
        matrices_dir.mkdir(parents=True, exist_ok=True)

    def get(self, *keys: str, default: Any = None) -> Any:
        """Безопасный доступ к вложенным ключам конфигурации."""
        current = self._data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return default
            else:
                return default
        return current if current is not None else default

    def set(self, *keys: str, value: Any):
        """Установить значение по вложенным ключам."""
        current = self._data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def save(self):
        """Сохранить текущую конфигурацию в файл."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key, {})

    def __repr__(self) -> str:
        return f"Config({self.config_path})"