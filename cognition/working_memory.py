"""
Рабочая память (Working Memory) — текущий фокус внимания.
Ограниченная по размеру deque, автоматически вытесняет старые элементы.
Все элементы получают timestamp при добавлении.
"""

from typing import Any, Dict, List, Optional
from collections import deque
from core.utils import timestamp


class WorkingMemory:
    """
    Рабочая память с фиксированным размером.
    Новые элементы вытесняют старые при превышении лимита.
    """

    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self._items: deque = deque(maxlen=max_size)
        self._focus: Optional[str] = None  # Текущий фокус внимания

    def add(self, item: Dict) -> int:
        """Добавить элемент в рабочую память с авто-таймстемпом. Возвращает текущий размер."""
        if "timestamp" not in item:
            item["timestamp"] = timestamp()
        self._items.append(item)
        return len(self._items)

    def add_all(self, items: List[Dict]):
        """Добавить несколько элементов (с таймстемпом)."""
        for item in items:
            self.add(item)

    def get_all(self) -> List[Dict]:
        """Получить все элементы."""
        return list(self._items)

    def get_recent(self, n: int = 5) -> List[Dict]:
        """Получить последние n элементов."""
        items = list(self._items)
        return items[-n:]

    def get_by_role(self, role: str) -> List[Dict]:
        """Найти элементы по роли (user/assistant/system)."""
        return [item for item in self._items if item.get("role") == role]

    def get_by_key(self, key: str, value: Any) -> List[Dict]:
        """Найти элементы с определённым значением ключа."""
        return [item for item in self._items if item.get(key) == value]

    def search(self, query: str) -> List[Dict]:
        """Поиск по содержимому элементов."""
        query_lower = query.lower()
        return [
            item for item in self._items
            if query_lower in str(item.get("content", "")).lower()
        ]

    def set_focus(self, focus_id: str):
        """Установить текущий фокус внимания."""
        self._focus = focus_id

    def get_focus(self) -> Optional[str]:
        """Получить текущий фокус."""
        return self._focus

    def clear(self):
        """Очистить рабочую память."""
        self._items.clear()
        self._focus = None

    def count(self) -> int:
        return len(self._items)

    def is_full(self) -> bool:
        return len(self._items) >= self.max_size

    def __repr__(self) -> str:
        return f"WorkingMemory({len(self._items)}/{self.max_size}, focus={self._focus})"