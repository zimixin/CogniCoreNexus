"""
Gene — единица графа знаний ("ген").
Содержит паспорт (passport), AAAK-сжатие, полный текст и метаданные.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from core.utils import timestamp, utcnow as _utcnow


@dataclass
class GenePassport:
    """
    Паспорт гена — метаинформация для оценки применимости знания.

    Поля:
    - purpose: для чего это знание
    - domain: предметная область
    - confidence: достоверность (0.0-1.0)
    - audience: целевая аудитория (кому это полезно)
    - cost: стоимость применения (вычислительная/временная)
    - context_restrictions: контекстные ограничения
    """
    purpose: str = ""
    domain: str = "general"
    confidence: float = 0.7
    audience: str = ""
    cost: float = 0.1
    context_restrictions: str = ""

    def to_dict(self) -> Dict:
        return {
            "purpose": self.purpose,
            "domain": self.domain,
            "confidence": self.confidence,
            "audience": self.audience,
            "cost": self.cost,
            "context_restrictions": self.context_restrictions,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GenePassport":
        return cls(
            purpose=data.get("purpose", ""),
            domain=data.get("domain", "general"),
            confidence=data.get("confidence", 0.7),
            audience=data.get("audience", ""),
            cost=data.get("cost", 0.1),
            context_restrictions=data.get("context_restrictions", ""),
        )


@dataclass
class Gene:
    """
    Ген — единица знания в графе знаний.

    Типы: principle, pattern, fact, model, concept, rule, heuristic
    """
    id: str
    name: str
    type: str = "fact"  # principle, pattern, fact, model, concept, rule, heuristic
    passport: GenePassport = field(default_factory=GenePassport)
    aaak_compressed: str = ""  # AAAK-представление
    full_text: str = ""  # Полный текст
    provenance: str = "human"  # human, llm_inferred, external
    relations: List[Dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "passport": self.passport.to_dict(),
            "aaak_compressed": self.aaak_compressed,
            "full_text": self.full_text,
            "provenance": self.provenance,
            "relations": self.relations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Gene":
        passport = GenePassport.from_dict(data.get("passport", {}))

        now = timestamp()
        return cls(
            id=data.get("id", ""),
            name=data.get("name", data.get("id", "")),
            type=data.get("type", "fact"),
            passport=passport,
            aaak_compressed=data.get("aaak_compressed", ""),
            full_text=data.get("full_text", ""),
            provenance=data.get("provenance", "human"),
            relations=data.get("relations", []),
            created_at=data.get("created_at") or now,
            updated_at=data.get("updated_at") or now,
            tags=data.get("tags", []),
        )

    def __repr__(self) -> str:
        return f"Gene({self.name}, {self.type}, conf={self.passport.confidence})"