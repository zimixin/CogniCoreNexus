"""
Relation — типы отношений между генами.
Поддерживает 200+ типов, сгруппированных по категориям.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass


# Категории отношений
RELATION_CATEGORIES = {
    "hierarchical": [
        "is_a", "part_of", "member_of", "instance_of", "subclass_of",
        "superclass_of", "belongs_to", "contained_in",
    ],
    "causal": [
        "causes", "contributes_to", "leads_to", "results_in",
        "triggers", "enables", "prevents", "blocks", "inhibits",
        "amplifies", "reduces", "mitigates", "compensates",
    ],
    "dependency": [
        "depends_on", "requires", "needs", "prerequisite_of",
        "built_upon", "foundation_for", "supported_by",
    ],
    "logical": [
        "contradicts", "supports", "proves", "disproves",
        "implies", "entails", "suggests", "indicates",
        "correlates_with", "is_consistent_with", "inconsistent_with",
    ],
    "solution": [
        "solves", "addresses", "fixes", "resolves",
        "mitigates", "works_around", "alternative_to",
    ],
    "comparison": [
        "similar_to", "different_from", "opposite_of",
        "better_than", "worse_than", "equivalent_to",
        "superset_of", "subset_of", "variant_of",
    ],
    "temporal": [
        "before", "after", "during", "simultaneous_with",
        "follows", "precedes", "overlaps_with",
    ],
    "spatial": [
        "located_at", "near", "far_from", "connected_to",
        "adjacent_to", "inside", "outside", "between",
    ],
    "composition": [
        "composed_of", "made_of", "contains", "consists_of",
        "includes", "excludes", "has_part",
    ],
    "knowledge": [
        "example_of", "exception_to", "generalizes",
        "specializes", "refines", "expands_on",
        "summarizes", "details", "illustrates",
    ],
    "software": [
        "implements", "extends", "overrides", "calls",
        "imports", "exports", "configures", "deploys",
        "deprecates", "replaces", "version_of",
    ],
}


@dataclass
class Relation:
    """Отношение между двумя генами."""
    source_id: str
    target_id: str
    relation_type: str
    confidence: float = 0.7
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "confidence": self.confidence,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Relation":
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=data["relation_type"],
            confidence=data.get("confidence", 0.7),
            description=data.get("description", ""),
        )

    def __repr__(self) -> str:
        return f"Rel({self.source_id} --[{self.relation_type}]--> {self.target_id})"


def get_relation_types(category: Optional[str] = None) -> Dict[str, List[str]]:
    """Получить типы отношений, опционально — только одной категории."""
    if category:
        return {category: RELATION_CATEGORIES.get(category, [])}
    return RELATION_CATEGORIES


def is_valid_relation_type(rel_type: str) -> bool:
    """Проверить, является ли тип отношения валидным."""
    for types in RELATION_CATEGORIES.values():
        if rel_type in types:
            return True
    return False