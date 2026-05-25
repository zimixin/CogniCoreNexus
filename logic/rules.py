"""
Правила логического вывода.
Правило: набор условий, которые ведут к заключению.
"""

from typing import Any, Dict, List, Optional, Set, Tuple


class Rule:
    """
    Логическое правило вида: условия -> заключения.

    Пример:
        Rule(
            name="solid_srp_violation",
            conditions=[
                ("has_trait", "X", "multi_role"),
                ("has_trait", "X", "class_or_module"),
            ],
            conclusions=[
                ("violates", "X", "SRP"),
            ],
            confidence=0.8,
            domain="software_engineering",
        )
    """

    def __init__(
        self,
        name: str,
        conditions: List[Tuple[str, str, str]],
        conclusions: List[Tuple[str, str, str]],
        confidence: float = 0.7,
        domain: str = "general",
        description: str = "",
    ):
        self.name = name
        self.conditions = conditions  # [(предикат, субъект, объект), ...]
        self.conclusions = conclusions  # [(предикат, субъект, объект), ...]
        self.confidence = confidence
        self.domain = domain
        self.description = description

    def matches(self, facts: Set[Tuple[str, str, str]]) -> Tuple[bool, Dict[str, str]]:
        """
        Проверяет, соответствуют ли факты условиям правила.
        Использует backtracking для поиска БЕЗ переменных.
        Возвращает (True, переменные) если все условия выполнены.
        """
        return self._backtrack(self.conditions, facts, {})

    def _backtrack(self, conditions, facts, variables, cond_idx=0):
        """Рекурсивный backtracking: перебирает все варианты привязки фактов к условиям."""
        if cond_idx >= len(conditions):
            return True, dict(variables)

        predicate, subj, obj = conditions[cond_idx]

        for fact_pred, fact_subj, fact_obj in facts:
            if fact_pred != predicate:
                continue

            new_vars = {}
            ok = True

            # Проверяем субъект
            if subj[0].isupper():  # переменная
                if subj in variables:
                    if variables[subj] != fact_subj:
                        ok = False
                else:
                    new_vars[subj] = fact_subj
            else:  # литерал
                if fact_subj != subj:
                    ok = False

            if not ok:
                continue

            # Проверяем объект
            if obj[0].isupper():  # переменная
                if obj in variables:
                    if variables[obj] != fact_obj:
                        ok = False
                else:
                    new_vars[obj] = fact_obj
            else:  # литерал
                if fact_obj != obj:
                    ok = False

            if not ok:
                continue

            # Пробуем следующий уровень
            merged = {**variables, **new_vars}
            matched, result_vars = self._backtrack(conditions, facts, merged, cond_idx + 1)
            if matched:
                return True, result_vars

        return False, {}

    def apply(self, variables: Dict[str, str]) -> List[Tuple[str, str, str]]:
        """Применяет правило с подстановкой переменных, возвращает заключения."""
        results = []
        for predicate, subj, obj in self.conclusions:
            resolved_subj = variables.get(subj, subj)
            resolved_obj = variables.get(obj, obj)
            results.append((predicate, resolved_subj, resolved_obj))
        return results

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "conditions": self.conditions,
            "conclusions": self.conclusions,
            "confidence": self.confidence,
            "domain": self.domain,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Rule":
        return cls(
            name=data["name"],
            conditions=[tuple(c) for c in data["conditions"]],
            conclusions=[tuple(c) for c in data["conclusions"]],
            confidence=data.get("confidence", 0.7),
            domain=data.get("domain", "general"),
            description=data.get("description", ""),
        )

    def __repr__(self) -> str:
        conds = ", ".join(f"{c[0]}({c[1]},{c[2]})" for c in self.conditions)
        concs = ", ".join(f"{c[0]}({c[1]},{c[2]})" for c in self.conclusions)
        return f"Rule({self.name}): {conds} -> {concs}"


# Несколько стандартных правил
DEFAULT_RULES = [
    Rule(
        name="transitivity",
        conditions=[
            ("is_a", "X", "Y"),
            ("is_a", "Y", "Z"),
        ],
        conclusions=[
            ("is_a", "X", "Z"),
        ],
        confidence=0.95,
        description="Транзитивность отношения is_a",
    ),
    Rule(
        name="contradiction_detection",
        conditions=[
            ("supports", "X", "Y"),
            ("contradicts", "X", "Y"),
        ],
        conclusions=[
            ("inconsistent", "X", "Y"),
        ],
        confidence=0.6,
        description="Обнаружение противоречия",
    ),
    Rule(
        name="solution_applies",
        conditions=[
            ("solves", "X", "Y"),
            ("has_problem", "Z", "Y"),
        ],
        conclusions=[
            ("applicable", "X", "Z"),
        ],
        confidence=0.8,
        description="Если X решает Y, а Z имеет проблему Y, то X применимо к Z",
    ),
]