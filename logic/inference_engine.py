"""
Логический движок прямого вывода (Forward Chaining Inference).
Применяет правила к фактам, пока не достигнут лимит шагов или не появится новых фактов.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from logic.rules import Rule, DEFAULT_RULES


class InferenceEngine:
    """
    Движок прямого логического вывода.

    Факты: {(предикат, субъект, объект)}
    Правила: [Rule, ...]

    forward_chain() применяет все правила, пока возможно.
    """

    def __init__(self, max_steps: int = 50):
        self.facts: Set[Tuple[str, str, str]] = set()
        self.rules: List[Rule] = list(DEFAULT_RULES)
        self.max_steps = max_steps

    def add_fact(self, predicate: str, subject: str, obj: str):
        """Добавить факт: predicate(subject, object)."""
        self.facts.add((predicate, subject, obj))

    def add_rule(self, rule_data: Dict) -> str:
        """Добавить правило из словаря."""
        rule = Rule.from_dict(rule_data)
        self.rules.append(rule)
        return rule.name

    def add_rules(self, rules: List[Rule]):
        """Добавить несколько правил."""
        self.rules.extend(rules)

    def remove_fact(self, predicate: str, subject: str, obj: str):
        """Удалить факт."""
        self.facts.discard((predicate, subject, obj))

    def forward_chain(self, context: Optional[Dict] = None) -> List[str]:
        """
        Прямой логический вывод.
        Возвращает список строк с новыми выводами.

        Извлекает факты из контекста (genes, loci), применяет правила,
        добавляет новые факты и повторяет до стабилизации.
        """
        # Извлекаем факты из контекста
        if context:
            self._extract_facts_from_context(context)

        new_inferences: List[str] = []
        step = 0

        while step < self.max_steps:
            step += 1
            any_new_facts = False

            for rule in self.rules:
                matched, variables = rule.matches(self.facts)
                if matched:
                    conclusions = rule.apply(variables)
                    for conclusion in conclusions:
                        if conclusion not in self.facts:
                            self.facts.add(conclusion)
                            pred, subj, obj = conclusion
                            new_inferences.append(
                                f"[{rule.name}] {pred}({subj}, {obj}) "
                                f"(уверенность: {rule.confidence})"
                            )
                            any_new_facts = True

            if not any_new_facts:
                break

        return new_inferences

    def _extract_facts_from_context(self, context: Dict):
        """Извлекает факты из генов и записей локусов."""
        # Из генов
        for gene in context.get("genes", []):
            gtype = gene.get("type", "")
            gname = gene.get("name", gene.get("id", ""))
            if gname:
                self.add_fact("has_type", gname, gtype)

            # Отношения из гена
            relations = gene.get("relations", [])
            for rel in relations:
                rel_type = rel.get("type", "")
                target = rel.get("target", "")
                if rel_type and target:
                    self.add_fact(rel_type, gname, target)

        # Из записей локусов
        for entry in context.get("loci_entries", []):
            tags = entry.get("tags", [])
            path = entry.get("path", "")
            for tag in tags:
                if tag and path:
                    self.add_fact("has_tag", path, tag)

    def get_facts(self, predicate: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """Получить факты, опционально фильтруя по предикату."""
        if predicate:
            return [(p, s, o) for p, s, o in self.facts if p == predicate]
        return list(self.facts)

    def query(self, predicate: str, subject: str, obj: str) -> List[Tuple[str, str, str, float]]:
        """
        Запросить факты с переменными.
        Если аргумент — пустая строка, считается переменной.
        Возвращает (pred, subj, obj, confidence) с совпадениями.
        """
        results = []
        for p, s, o in self.facts:
            if predicate and p != predicate:
                continue
            if subject and s != subject:
                continue
            if obj and o != obj:
                continue
            results.append((p, s, o, 1.0))
        return results

    def clear_facts(self):
        """Очистить все факты."""
        self.facts.clear()

    def __repr__(self) -> str:
        return f"InferenceEngine(facts={len(self.facts)}, rules={len(self.rules)})"