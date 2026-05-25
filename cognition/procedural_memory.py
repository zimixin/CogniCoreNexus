"""
Процедурная память — хранит когнитивные матрицы (сценарии рассуждений).
Матрица — это последовательность шагов (намерений), каждый из которых
может быть: поиск в памяти, вызов правила, запрос к LLM, вызов инструмента.

Матрицы загружаются из data/matrices/*.yaml при старте.
Если YAML-файлов нет — используются хардкодные дефолты.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
import copy
import json
import yaml
import difflib


class ProceduralMemory:
    """
    Хранилище когнитивных матриц (процедурных сценариев).

    Матрица — это словарь:
    {
        "name": "code_review_solid",
        "description": "Проверка кода на нарушения SOLID",
        "trigger_goals": ["review_code", "code_review", "solid"],
        "steps": [
            {"id": "find_principles", "action": "find_genes",
             "params": {"type": "principle", "tags": ["SOLID"]}},
            {"id": "search_loci", "action": "loci_search",
             "params": {"tags": ["code", "smell"]}},
            {"id": "llm_analysis", "action": "llm_query",
             "params": {"template": "..."},
             "depends_on": ["find_principles", "search_loci"]},
        ],
        "max_iterations": 3,
    }
    """

    def __init__(self, matrices_dir: Optional[str] = None):
        self._matrices: Dict[str, Dict] = {}
        self._matrices_dir = None

        if matrices_dir:
            self._matrices_dir = Path(matrices_dir)
            if self._matrices_dir.exists():
                self._load_from_yaml()

        if not self._matrices:
            # Fallback на хардкодные дефолты
            self._load_defaults()

    def _load_from_yaml(self):
        """Загрузить матрицы из YAML-файлов в data/matrices/."""
        loaded = 0
        for yaml_file in sorted(self._matrices_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if not data or "name" not in data:
                    continue
                # Нормализуем: trigger_goals -> triggers (обратная совместимость)
                if "trigger_goals" in data and "triggers" not in data:
                    data["triggers"] = data["trigger_goals"]
                self._matrices[data["name"]] = data
                loaded += 1
            except Exception as e:
                print(f"[ProceduralMemory] Ошибка загрузки {yaml_file}: {e}")

        if loaded:
            print(f"[ProceduralMemory] Загружено {loaded} матриц из {self._matrices_dir}")

    def _load_defaults(self):
        """Загрузить стандартные когнитивные матрицы (хардкодный fallback)."""
        defaults = [
            {
                "name": "general_inquiry",
                "description": "Общий запрос — поиск в памяти, логика, LLM",
                "triggers": ["ask", "query", "what", "why", "how", "?"],
                "steps": [
                    {"action": "loci_search", "params": {"level": "all"}},
                    {"action": "find_genes", "params": {}},
                    {"action": "inference", "params": {}},
                    {"action": "llm_query", "params": {"template": "Ответь на запрос пользователя, используя контекст."}},
                ],
                "max_iterations": 1,
            },
            {
                "name": "knowledge_gap",
                "description": "Обнаружение и заполнение пробелов в знаниях",
                "triggers": ["dont_know", "unknown", "gap", "learn"],
                "steps": [
                    {"action": "loci_search", "params": {"level": 3}},
                    {"action": "find_genes", "params": {"max_distance": 1}},
                    {"action": "inference", "params": {}},
                    {"action": "verify", "params": {"check_contradictions": True}},
                    {"action": "llm_query", "params": {"template": "На основе контекста заполни пробел: {query}"}},
                ],
                "max_iterations": 2,
            },
            {
                "name": "code_review_solid",
                "description": "Проверка кода на нарушения принципов SOLID",
                "triggers": ["review_code", "code_review", "solid", "refactor"],
                "steps": [
                    {"action": "find_genes", "params": {"type": "principle", "tags": ["SOLID"]}},
                    {"action": "loci_search", "params": {"tags": ["code", "smell", "violation"]}},
                    {"action": "inference", "params": {}},
                    {"action": "llm_query", "params": {"template": "На основе принципов {genes} и найденного кода {loci} определи нарушения SOLID."}},
                ],
                "max_iterations": 1,
            },
            {
                "name": "deep_analysis",
                "description": "Глубокий анализ — полный обход всех слоёв памяти",
                "triggers": ["analyze", "deep", "investigate", "root_cause"],
                "steps": [
                    {"action": "loci_search", "params": {"level": 3, "bfs_depth": 5}},
                    {"action": "find_genes", "params": {"max_distance": 5}},
                    {"action": "inference", "params": {}},
                    {"action": "llm_query", "params": {"template": "Проведи глубокий анализ на основе всего доступного контекста. Ищи корневые причины."}},
                ],
                "max_iterations": 3,
            },
            {
                "name": "tom_simulation",
                "description": "Запуск Theory of Mind симуляции для агента",
                "triggers": ["simulate", "agent", "perspective", "theory_of_mind"],
                "steps": [
                    {"action": "tom_simulate", "params": {}},
                    {"action": "loci_search", "params": {"tags": ["agent", "behavior"]}},
                    {"action": "llm_query", "params": {"template": "На основе модели агента {tom_result} опиши его вероятные действия."}},
                ],
                "max_iterations": 1,
            },
        ]

        for matrix in defaults:
            self.add(matrix)

    def add(self, matrix: Dict):
        """Добавить или обновить матрицу."""
        name = matrix.get("name")
        if not name:
            raise ValueError("Матрица должна иметь поле 'name'")
        self._matrices[name] = matrix

    def get(self, name: str) -> Optional[Dict]:
        """Получить матрицу по имени."""
        return copy.deepcopy(self._matrices.get(name))

    def remove(self, name: str) -> bool:
        """Удалить матрицу."""
        return self._matrices.pop(name, None) is not None

    def find_matching(self, query: str) -> Optional[Dict]:
        """
        Найти матрицу, подходящую под запрос.

        Стратегия:
        1. Точное совпадение trigger_goals/triggers по query
        2. Fuzzy-совпадение через difflib (если точных нет)
        """
        query_lower = query.lower()
        best_match = None
        best_score = 0

        # Точное совпадение по триггерам
        for name, matrix in self._matrices.items():
            triggers = matrix.get("triggers", matrix.get("trigger_goals", []))
            score = sum(1 for t in triggers if t.lower() in query_lower)
            if score > best_score:
                best_score = score
                best_match = matrix

        # Fuzzy-совпадение, если точных нет
        if not best_match:
            words = query_lower.split()
            for name, matrix in self._matrices.items():
                triggers = matrix.get("triggers", matrix.get("trigger_goals", []))
                for t in triggers:
                    ratio = difflib.SequenceMatcher(None, t.lower(), query_lower).ratio()
                    if ratio > 0.6:
                        best_match = matrix
                        best_score = ratio
                        break

        return copy.deepcopy(best_match) if best_match else None

    def list_matrices(self) -> List[Dict]:
        """Список всех матриц (без шагов для краткости)."""
        return [
            {
                "name": m["name"],
                "description": m.get("description", ""),
                "triggers": m.get("triggers", m.get("trigger_goals", [])),
                "steps_count": len(m.get("steps", [])),
            }
            for m in self._matrices.values()
        ]

    def count(self) -> int:
        return len(self._matrices)

    def __repr__(self) -> str:
        return f"ProceduralMemory({self.count()} matrices)"