"""Proactive contradiction detection for incoming knowledge."""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json
import logging

logger = logging.getLogger("cognicore.contradiction")


class ConflictType(Enum):
    DIRECT_NEGATION = "direct_negation"
    LOGICAL_IMPOSSIBLE = "logical_impossible"
    TEMPORAL = "temporal"
    CARDINALITY = "cardinality"
    SEMANTIC = "semantic"


class ResolutionAction(Enum):
    REJECT_NEW = "reject_new"
    REPLACE_OLD = "replace_old"
    KEEP_BOTH = "keep_both"
    ASK_USER = "ask_user"
    MERGE = "merge"


@dataclass
class Conflict:
    existing_gene_id: str
    existing_text: str
    existing_confidence: float
    new_text: str
    conflict_type: ConflictType
    description: str
    proposed_action: ResolutionAction
    reasoning: str


class ContradictionDetector:
    """Detects contradictions between new knowledge and existing genome."""

    NEGATION_PAIRS = [
        # First person
        ("люблю", "ненавижу"), ("люблю", "не люблю"),
        # Third person (most common in facts)
        ("любит", "ненавидит"), ("любит", "не любит"),
        ("любят", "ненавидят"), ("любят", "не любят"),
        # Infinitive
        ("любить", "ненавидеть"), ("любить", "не любить"),
        # Noun forms
        ("любовь", "ненависть"),
        # Like/dislike
        ("нравятся", "не нравятся"), ("нравится", "не нравится"),
        ("нравиться", "не нравиться"),
        # Want
        ("хочу", "не хочу"), ("хочет", "не хочет"), ("хотят", "не хотят"),
        # Can
        ("можю", "не могу"), ("может", "не может"), ("могут", "не могут"),
        # Know
        ("знаю", "не знаю"), ("знает", "не знает"), ("знают", "не знают"),
        # Believe
        ("верю", "не верю"), ("верит", "не верит"), ("верят", "не верят"),
        # Yes/no
        ("да", "нет"), ("правда", "ложь"), ("истина", "ложь"),
        # Always/never
        ("всегда", "никогда"), ("часто", "редко"),
        # Exist
        ("есть", "нет"), ("существует", "не существует"),
        # Must
        ("должен", "не должен"), ("должна", "не должна"), ("должны", "не должны"),
    ]

    def __init__(self, nexus):
        self.nexus = nexus
        self.llm = nexus.llm if hasattr(nexus, 'llm') and nexus.llm else None

    def check(self, new_knowledge: Dict[str, Any]) -> List[Conflict]:
        """Main entry: check new knowledge against genome."""
        conflicts = []

        new_text = self._extract_text(new_knowledge)
        new_type = new_knowledge.get("_type") or new_knowledge.get("type", "fact")

        if not new_text or len(new_text.strip()) < 3:
            return conflicts

        # 1. Direct negation check (fast, keyword-based)
        conflicts.extend(self._check_direct_negation(new_text, new_type))

        # 2. Logical facts check (inference engine)
        conflicts.extend(self._check_logical_facts(new_knowledge))

        # 3. Semantic check via LLM (if available and enabled)
        if self._llm_available():
            conflicts.extend(self._check_semantic_llm(new_text, new_type, new_knowledge))

        # Deduplicate conflicts by existing_gene_id
        seen = set()
        unique_conflicts = []
        for c in conflicts:
            key = (c.existing_gene_id, c.conflict_type.value)
            if key not in seen:
                seen.add(key)
                unique_conflicts.append(c)

        return unique_conflicts

    def _extract_text(self, knowledge: Dict) -> str:
        """Extract searchable text from knowledge dict."""
        parts = []
        for key in ("full_text", "name", "description", "content", "predicate", "object", "subject"):
            val = knowledge.get(key)
            if val:
                parts.append(str(val))
        if "data" in knowledge and isinstance(knowledge["data"], dict):
            for key in ("full_text", "name", "description", "content", "predicate", "object", "subject"):
                val = knowledge["data"].get(key)
                if val:
                    parts.append(str(val))
        return " ".join(parts).lower()

    def _llm_available(self) -> bool:
        """Check if LLM is available for semantic checking."""
        return (self.llm is not None and
                hasattr(self.llm, 'is_available') and
                self.llm.is_available())

    def _check_direct_negation(self, new_text: str, new_type: str) -> List[Conflict]:
        """Fast keyword-based negation detection."""
        conflicts = []

        existing_genes = self.nexus.genome.list_genes()
        if isinstance(existing_genes, dict):
            existing_genes = existing_genes.get("genes", [])

        # Extract key entities from new text (nouns after verbs)
        new_entities = self._extract_entities(new_text)

        for gene in existing_genes:
            existing_text = (gene.get("full_text") or gene.get("name") or "").lower()
            if not existing_text or len(existing_text.strip()) < 3:
                continue

            existing_entities = self._extract_entities(existing_text)

            # Only check for negation if they share at least one entity
            # (same object being loved/hated)
            shared_entities = new_entities & existing_entities
            if not shared_entities:
                continue

            for pos, neg in self.NEGATION_PAIRS:
                # Check both directions with entity awareness
                if self._word_in_text(pos, existing_text) and self._word_in_text(neg, new_text):
                    conflicts.append(Conflict(
                        existing_gene_id=gene["id"],
                        existing_text=gene.get("full_text", gene.get("name", "")),
                        existing_confidence=gene.get("passport", {}).get("confidence", 0.5),
                        new_text=new_text,
                        conflict_type=ConflictType.DIRECT_NEGATION,
                        description=f"Прямое отрицание: '{pos}' ↔ '{neg}' (объект: {', '.join(shared_entities)})",
                        proposed_action=self._propose_action(gene, new_text),
                        reasoning=f"Существующий ген '{gene['name']}' содержит '{pos}', новое знание содержит '{neg}' для одного объекта"
                    ))
                elif self._word_in_text(neg, existing_text) and self._word_in_text(pos, new_text):
                    conflicts.append(Conflict(
                        existing_gene_id=gene["id"],
                        existing_text=gene.get("full_text", gene.get("name", "")),
                        existing_confidence=gene.get("passport", {}).get("confidence", 0.5),
                        new_text=new_text,
                        conflict_type=ConflictType.DIRECT_NEGATION,
                        description=f"Прямое отрицание: '{neg}' ↔ '{pos}' (объект: {', '.join(shared_entities)})",
                        proposed_action=self._propose_action(gene, new_text),
                        reasoning=f"Существующий ген '{gene['name']}' содержит '{neg}', новое знание содержит '{pos}' для одного объекта"
                    ))

        return conflicts

    def _extract_entities(self, text: str) -> Set[str]:
        """Extract potential entities (nouns) from text for entity-aware matching."""
        import re
        # Simple extraction: words that could be objects (after verbs like любит, ненавидит, хочет, etc.)
        # This is a heuristic - look for words after common verbs
        entities = set()

        # Stop words to filter out (too generic)
        stop_words = {
            "пользователь", "user", "человек", "люди", "он", "она", "они",
            "это", "то", "эта", "тот", "та", "те", "мой", "твой", "свой",
            "какой", "который", "где", "когда", "как", "почему",
        }

        # Patterns: verb + entity
        patterns = [
            r'любит\s+(\w+)', r'ненавидит\s+(\w+)', r'не любит\s+(\w+)',
            r'хочет\s+(\w+)', r'не хочет\s+(\w+)',
            r'знает\s+(\w+)', r'не знает\s+(\w+)',
            r'любят\s+(\w+)', r'ненавидят\s+(\w+)',
            r'любить\s+(\w+)', r'ненавидеть\s+(\w+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if m not in stop_words:
                    entities.add(m)

        # Also add all words longer than 3 chars as potential entities, but filter stop words
        words = re.findall(r'\b\w{4,}\b', text)
        for w in words:
            if w not in stop_words:
                entities.add(w)

        return entities

    def _word_in_text(self, word: str, text: str) -> bool:
        """Check if word appears as whole word in text."""
        import re
        return bool(re.search(rf'\b{re.escape(word)}\b', text))

    def _check_logical_facts(self, new_knowledge: Dict) -> List[Conflict]:
        """Check against inference engine facts."""
        conflicts = []

        knowledge_type = new_knowledge.get("_type") or new_knowledge.get("type")
        data = new_knowledge.get("data", new_knowledge)

        if knowledge_type == "fact":
            pred = data.get("predicate")
            subj = data.get("subject")
            obj = data.get("object")

            if pred and subj and obj:
                # Check if opposite fact exists
                negated_pred = f"not_{pred}" if not pred.startswith("not_") else pred[4:]
                existing = self.nexus.inference_engine.query(negated_pred, subj, obj)
                if existing:
                    conflicts.append(Conflict(
                        existing_gene_id=f"fact_{negated_pred}_{subj}_{obj}",
                        existing_text=f"{negated_pred}({subj}, {obj})",
                        existing_confidence=0.8,
                        new_text=f"{pred}({subj}, {obj})",
                        conflict_type=ConflictType.LOGICAL_IMPOSSIBLE,
                        description=f"Логическое противоречие: {pred} vs {negated_pred}",
                        proposed_action=ResolutionAction.ASK_USER,
                        reasoning=f"В логическом движке уже есть факт: {negated_pred}({subj}, {obj})"
                    ))

        return conflicts

    def _check_semantic_llm(self, new_text: str, new_type: str, new_knowledge: Dict) -> List[Conflict]:
        """Use LLM to detect subtle semantic contradictions."""
        conflicts = []

        existing_genes = self.nexus.genome.list_genes()
        if isinstance(existing_genes, dict):
            existing_genes = existing_genes.get("genes", [])

        candidates = self._filter_candidates(existing_genes, new_text, new_knowledge)
        if not candidates:
            return conflicts

        prompt = self._build_semantic_prompt(new_text, candidates)

        try:
            response = self.llm.complete(prompt, temperature=0.1, max_tokens=500)
            parsed = self._parse_llm_conflicts(response, candidates, new_text)
            conflicts.extend(parsed)
        except Exception as e:
            logger.debug(f"LLM semantic check failed: {e}")

        return conflicts

    def _filter_candidates(self, genes: List[Dict], new_text: str, new_knowledge: Dict) -> List[Dict]:
        """Filter genes that might semantically relate to new text."""
        new_words = set(new_text.split())
        new_tags = set(new_knowledge.get("tags", []))
        if "data" in new_knowledge and isinstance(new_knowledge["data"], dict):
            new_tags |= set(new_knowledge["data"].get("tags", []))

        candidates = []

        for gene in genes:
            gene_text = (gene.get("full_text") or gene.get("name") or "").lower()
            gene_words = set(gene_text.split())
            gene_tags = set(gene.get("tags", []))

            # Overlap in keywords or shared tags
            word_overlap = len(new_words & gene_words)
            tag_overlap = len(new_tags & gene_tags)

            if word_overlap >= 2 or tag_overlap >= 1:
                candidates.append(gene)

        return candidates[:10]

    def _build_semantic_prompt(self, new_text: str, candidates: List[Dict]) -> str:
        lines = [
            "Ты — детектор противоречий в базе знаний.",
            "Новое знание:",
            f"  {new_text}",
            "",
            "Существующие знания (проверь на противоречия):"
        ]

        for i, gene in enumerate(candidates):
            conf = gene.get("passport", {}).get("confidence", 0.5)
            text = gene.get("full_text", gene.get("name", ""))
            lines.append(f"  {i+1}. [{gene['id']}] {text} (conf: {conf:.2f})")

        lines.extend([
            "",
            "Верни JSON массив противоречий:",
            '[{"index": 1, "conflict_type": "semantic", "description": "...", "severity": "high|medium|low", "proposed_action": "reject_new|replace_old|keep_both|ask_user", "reasoning": "..."}]',
            "Если противоречий нет — верни []."
        ])

        return "\n".join(lines)

    def _parse_llm_conflicts(self, response: str, candidates: List[Dict], new_text: str) -> List[Conflict]:
        conflicts = []
        try:
            data = json.loads(response)
            for item in data:
                idx = item.get("index", 0) - 1
                if 0 <= idx < len(candidates):
                    gene = candidates[idx]
                    conflicts.append(Conflict(
                        existing_gene_id=gene["id"],
                        existing_text=gene.get("full_text", gene.get("name", "")),
                        existing_confidence=gene.get("passport", {}).get("confidence", 0.5),
                        new_text=new_text,
                        conflict_type=ConflictType.SEMANTIC,
                        description=item.get("description", "Семантическое противоречие"),
                        proposed_action=ResolutionAction(item.get("proposed_action", "ask_user")),
                        reasoning=item.get("reasoning", "LLM-detected")
                    ))
        except Exception as e:
            logger.debug(f"Failed to parse LLM conflicts: {e}")
        return conflicts

    def _propose_action(self, existing_gene: Dict, new_text: str) -> ResolutionAction:
        """Heuristic for proposing resolution action."""
        existing_conf = existing_gene.get("passport", {}).get("confidence", 0.5)

        if existing_conf >= 0.8:
            return ResolutionAction.ASK_USER
        if existing_conf <= 0.4:
            return ResolutionAction.REPLACE_OLD
        return ResolutionAction.KEEP_BOTH