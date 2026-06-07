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

    NEGATION_PAIRS = []

    def __init__(self, nexus):
        self.nexus = nexus
        self.llm = nexus.llm if hasattr(nexus, 'llm') and nexus.llm else None

    def check(self, new_knowledge: Dict[str, Any]) -> List[Conflict]:
        """Main entry: check new knowledge against genome."""
        conflicts = []

        new_text_raw = self._extract_text(new_knowledge)
        new_text = new_text_raw.lower()
        new_type = new_knowledge.get("_type") or new_knowledge.get("type", "fact")

        if not new_text or len(new_text.strip()) < 3:
            return conflicts

        # 1. Direct negation check (fast, keyword-based)
        conflicts.extend(self._check_direct_negation(new_text_raw, new_text, new_type))

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
        # Priority: full_text > description > content > name > predicate/object/subject
        for key in ("full_text", "description", "content", "name", "predicate", "object", "subject"):
            val = knowledge.get(key)
            if val:
                return str(val)
        if "data" in knowledge and isinstance(knowledge["data"], dict):
            for key in ("full_text", "description", "content", "name", "predicate", "object", "subject"):
                val = knowledge["data"].get(key)
                if val:
                    return str(val)
        return ""

    def _extract_text_lower(self, knowledge: Dict) -> str:
        """Extract searchable text in lowercase."""
        text = self._extract_text(knowledge)
        return text.lower()

    def _llm_available(self) -> bool:
        """Check if LLM is available for semantic checking."""
        return (self.llm is not None and
                hasattr(self.llm, 'is_available') and
                self.llm.is_available())

    def _check_direct_negation(self, new_text_raw: str, new_text: str, new_type: str) -> List[Conflict]:
        """Generic contradiction detection: same subject, conflicting attributes."""
        conflicts = []

        existing_genes = self.nexus.genome.list_genes()
        if isinstance(existing_genes, dict):
            existing_genes = existing_genes.get("genes", [])

        # Extract subject entities from new knowledge (use original text for capitalization)
        new_subjects = self._extract_subjects(new_text_raw)
        if not new_subjects:
            return conflicts

        # Extract attribute-value pairs from new knowledge (use lowercased)
        new_attributes = self._extract_attributes(new_text)

        for gene in existing_genes:
            existing_text_raw = (gene.get("full_text") or gene.get("name") or "")
            if not existing_text_raw or len(existing_text_raw.strip()) < 3:
                continue

            existing_text = existing_text_raw.lower()

            # Check if gene mentions any of the same subjects
            existing_subjects = self._extract_subjects(existing_text_raw)
            shared_subjects = new_subjects & existing_subjects
            if not shared_subjects:
                continue

            # Extract attributes from existing gene
            existing_attributes = self._extract_attributes(existing_text)

            # Check for attribute conflicts on shared subjects
            for subject in shared_subjects:
                conflicts.extend(self._compare_attributes(
                    subject, new_attributes, existing_attributes, gene, new_text
                ))

        return conflicts

    def _extract_subjects(self, text: str) -> Set[str]:
        """Extract potential subject entities from text."""
        import re
        subjects = set()
        # Capitalized words (likely proper nouns/entities)
        subjects.update(re.findall(r'\b[А-ЯA-Z][а-яa-z0-9]+\b', text))
        # Words after common subject markers
        patterns = [
            r'(?:это|является|называется|известен как)\s+([А-ЯA-Z][а-яa-z0-9]+)',
            r'([А-ЯA-Z][а-яa-z0-9]+)\s+(?:это|—|-)',
        ]
        for pattern in patterns:
            subjects.update(re.findall(pattern, text))
        return {s.lower() for s in subjects if len(s) > 1}

    def _extract_attributes(self, text: str) -> Dict[str, Set[str]]:
        """Extract attribute-value pairs from text. Returns {subject: {attributes}}."""
        import re
        attributes = {}
        text_lower = text.lower()

        # Pattern 1: subject это/является attribute
        patterns = [
            r'([а-яa-z][а-яa-z0-9]+)\s+(?:это|является|—|-)\s*([а-яa-z]+)',
            r'([а-яa-z]+)\s+(?:это|является)\s+([а-яa-z][а-яa-z0-9]+)',
        ]

        # Pattern 2: subject verb object (Russian: subject verb object)
        verb_patterns = [
            r'([а-яa-z][а-яa-z0-9]+)\s+(любит|ненавидит|любят|ненавидят|хочет|не хочет|знает|не знает|может|не может)\s+([а-яa-z]+)',
            r'([а-яa-z]+)\s+(любит|ненавидит|любят|ненавидят|хочет|не хочет|знает|не знает|может|не может)\s+([а-яa-z][а-яa-z0-9]+)',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text_lower):
                groups = match.groups()
                if len(groups) >= 2:
                    subj, attr = groups[0].lower(), groups[1].lower()
                    if subj not in attributes:
                        attributes[subj] = set()
                    attributes[subj].add(attr)

        for pattern in verb_patterns:
            for match in re.finditer(pattern, text_lower):
                groups = match.groups()
                if len(groups) >= 3:
                    subj, verb, obj = groups[0].lower(), groups[1].lower(), groups[2].lower()
                    # Store verb as attribute category, object as value
                    attr_key = f"verb:{verb}"
                    if subj not in attributes:
                        attributes[subj] = set()
                    attributes[subj].add(attr_key)
                    # Also store object as attribute value
                    if subj not in attributes:
                        attributes[subj] = set()
                    attributes[subj].add(f"object:{obj}")

        return attributes

    def _compare_attributes(self, subject: str, new_attrs: Dict, existing_attrs: Dict, gene: Dict, new_text: str) -> List[Conflict]:
        """Compare attributes for same subject, detect conflicts."""
        conflicts = []

        new_subject_attrs = new_attrs.get(subject, set())
        existing_subject_attrs = existing_attrs.get(subject, set())

        if not new_subject_attrs or not existing_subject_attrs:
            return conflicts

        # Extract objects from attributes
        new_objects = {attr.replace("object:", "") for attr in new_subject_attrs if attr.startswith("object:")}
        existing_objects = {attr.replace("object:", "") for attr in existing_subject_attrs if attr.startswith("object:")}

        # Check for mutually exclusive attributes
        for new_attr in new_subject_attrs:
            for existing_attr in existing_subject_attrs:
                if new_attr != existing_attr and self._are_likely_exclusive(new_attr, existing_attr):
                    # If both have objects, only conflict if objects are the same
                    # (loving flowers AND hating spiders is fine; loving spiders AND hating spiders is conflict)
                    if new_objects and existing_objects:
                        # Check if there's any overlap in objects
                        if not (new_objects & existing_objects):
                            # Different objects - not a conflict (e.g., love flowers vs hate spiders)
                            continue
                    
                    conflicts.append(Conflict(
                        existing_gene_id=gene["id"],
                        existing_text=gene.get("full_text", gene.get("name", "")),
                        existing_confidence=gene.get("passport", {}).get("confidence", 0.5),
                        new_text=new_text,
                        conflict_type=ConflictType.DIRECT_NEGATION,
                        description=f"Конфликт атрибутов для '{subject}': в базе '{existing_attr}', новое '{new_attr}'",
                        proposed_action=self._propose_action(gene, new_text),
                        reasoning=f"Существующий ген '{gene['name']}' классифицирует '{subject}' как '{existing_attr}', новое знание — как '{new_attr}'"
                    ))

        return conflicts
        """Heuristic: two attributes are likely mutually exclusive if they look like alternative classifications."""
        # Same length-ish, both look like category nouns
        if abs(len(attr1) - len(attr2)) > 6:
            return False
        # Both end with typical category suffixes
        category_suffixes = ('овоз', 'воз', 'тип', 'класс', 'вид', 'разновидность', 'модель', 'серия')
        is_cat1 = any(attr1.endswith(s) for s in category_suffixes)
        is_cat2 = any(attr2.endswith(s) for s in category_suffixes)
        if is_cat1 and is_cat2:
            return True

        # Check for verb conflicts: verb:любит vs verb:ненавидит
        if attr1.startswith("verb:") and attr2.startswith("verb:"):
            verb1 = attr1[5:]
            verb2 = attr2[5:]
            negation_pairs = {
                "любит": "ненавидит", "любят": "ненавидят",
                "хочет": "не хочет", "хочет": "нехочет",
                "знает": "не знает", "может": "не может",
            }
            return negation_pairs.get(verb1) == verb2 or negation_pairs.get(verb2) == verb1

        return False

    def _are_likely_exclusive(self, attr1: str, attr2: str) -> bool:
        """Heuristic: two attributes are likely mutually exclusive if they look like alternative classifications."""
        # Same length-ish, both look like category nouns
        if abs(len(attr1) - len(attr2)) > 6:
            return False
        # Both end with typical category suffixes
        category_suffixes = ('овоз', 'воз', 'тип', 'класс', 'вид', 'разновидность', 'модель', 'серия')
        is_cat1 = any(attr1.endswith(s) for s in category_suffixes)
        is_cat2 = any(attr2.endswith(s) for s in category_suffixes)
        if is_cat1 and is_cat2:
            return True

        # Check for verb conflicts: verb:любит vs verb:ненавидит
        if attr1.startswith("verb:") and attr2.startswith("verb:"):
            verb1 = attr1[5:]
            verb2 = attr2[5:]
            negation_pairs = {
                "любит": "ненавидит", "любят": "ненавидят",
                "хочет": "не хочет", "хочет": "нехочет",
                "знает": "не знает", "может": "не может",
            }
            return negation_pairs.get(verb1) == verb2 or negation_pairs.get(verb2) == verb1

        return False

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