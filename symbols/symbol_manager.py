"""
Symbol Manager — управление символами (объекты, концепты, агенты, цели, убеждения).
Поддерживает добавление и поиск отношений между символами.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class SymbolType(Enum):
    OBJECT = "object"
    CONCEPT = "concept"
    AGENT = "agent"
    GOAL = "goal"
    BELIEF = "belief"
    INTENTION = "intention"
    EVENT = "event"
    STATE = "state"


@dataclass
class Symbol:
    """Единица символьного представления."""
    name: str
    symbol_type: SymbolType = SymbolType.CONCEPT
    attributes: Dict[str, Any] = field(default_factory=dict)
    relations: Dict[str, List[str]] = field(default_factory=dict)  # rel_type -> [target_names]
    description: str = ""

    def add_relation(self, rel_type: str, target_name: str):
        if rel_type not in self.relations:
            self.relations[rel_type] = []
        if target_name not in self.relations[rel_type]:
            self.relations[rel_type].append(target_name)

    def has_relation(self, rel_type: str, target_name: str) -> bool:
        return rel_type in self.relations and target_name in self.relations[rel_type]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.symbol_type.value,
            "attributes": self.attributes,
            "relations": self.relations,
            "description": self.description,
        }

    def __repr__(self) -> str:
        rels = "; ".join(f"{k}:{v}" for k, v in self.relations.items())
        return f"Symbol({self.name}, {self.symbol_type.value}, rels=[{rels}])"


class SymbolManager:
    """
    Менеджер символов. Хранит все символы в словаре,
    поддерживает поиск по типу, отношениям, атрибутам.
    """

    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}

    def add_symbol(self, name: str, symbol_type: SymbolType = SymbolType.CONCEPT,
                   attributes: Optional[Dict] = None,
                   description: str = "") -> Symbol:
        """Создать или обновить символ."""
        if name in self.symbols:
            sym = self.symbols[name]
            if attributes:
                sym.attributes.update(attributes)
            if description:
                sym.description = description
            return sym

        sym = Symbol(
            name=name,
            symbol_type=symbol_type,
            attributes=attributes or {},
            description=description,
        )
        self.symbols[name] = sym
        return sym

    def get_symbol(self, name: str) -> Optional[Symbol]:
        """Получить символ по имени."""
        return self.symbols.get(name)

    def add_relation(self, source: str, rel_type: str, target: str,
                     create_missing: bool = True):
        """
        Добавить отношение между символами.
        Если символы не существуют и create_missing=True — создаёт их.
        """
        if source not in self.symbols and create_missing:
            self.add_symbol(source)
        if target not in self.symbols and create_missing:
            self.add_symbol(target)

        if source in self.symbols and target in self.symbols:
            self.symbols[source].add_relation(rel_type, target)

    def find_by_type(self, symbol_type: SymbolType) -> List[Symbol]:
        """Найти все символы по типу."""
        return [s for s in self.symbols.values() if s.symbol_type == symbol_type]

    def find_by_relation(self, rel_type: str, target: str) -> List[Symbol]:
        """Найти символы, имеющие отношение указанного типа к цели."""
        return [
            s for s in self.symbols.values()
            if s.has_relation(rel_type, target)
        ]

    def find_by_attribute(self, key: str, value: Any) -> List[Symbol]:
        """Найти символы по атрибуту."""
        return [
            s for s in self.symbols.values()
            if s.attributes.get(key) == value
        ]

    def find_related(self, name: str, rel_type: Optional[str] = None,
                     max_depth: int = 2) -> List[Tuple[str, str, str]]:
        """
        Найти связанные символы BFS.
        Возвращает [(source, rel_type, target), ...].
        """
        if name not in self.symbols:
            return []

        visited = {name}
        results = []
        queue = [(name, 0)]

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            sym = self.symbols[current]
            for rel, targets in sym.relations.items():
                if rel_type and rel != rel_type:
                    continue
                for target in targets:
                    results.append((current, rel, target))
                    if target not in visited and target in self.symbols:
                        visited.add(target)
                        queue.append((target, depth + 1))

        return results

    def remove_symbol(self, name: str):
        """Удалить символ и все ссылки на него."""
        self.symbols.pop(name, None)
        for sym in self.symbols.values():
            for rel_type in list(sym.relations.keys()):
                sym.relations[rel_type] = [
                    t for t in sym.relations[rel_type] if t != name
                ]
                if not sym.relations[rel_type]:
                    del sym.relations[rel_type]

    def count(self) -> int:
        return len(self.symbols)

    def list_symbols(self) -> List[str]:
        return list(self.symbols.keys())

    def to_dict(self) -> Dict:
        return {name: sym.to_dict() for name, sym in self.symbols.items()}

    def __repr__(self) -> str:
        return f"SymbolManager({self.count()} symbols)"