"""
Комната (Room) — узел пространственной памяти.
Содержит метаданные (room.json) и ящики (.aaak файлы).
Связана с другими комнатами через граф.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from memory.loci.drawer import Drawer


class Room:
    """
    Комната пространственной памяти. Представлена папкой на диске.

    Структура папки:
    room_id/
    ├── room.json        — метаданные: имя, теги, связи, описание
    ├── drawer_001.aaak  — ящик с записями
    ├── drawer_002.aaak
    └── verbatim/        — полные тексты (опционально)
    """

    def __init__(self, path: str, codec: Any):
        self.path = Path(path)
        self.codec = codec
        self.meta: Dict = {}
        self.drawers: List[Drawer] = []
        self.loaded = False

    def load(self):
        """Загрузить метаданные и ящики комнаты."""
        # Загружаем метаданные
        meta_path = self.path / "room.json"
        if meta_path.exists():
            self.meta = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            self.meta = {
                "id": self.path.name,
                "name": self.path.name.replace("_", " ").title(),
                "tags": [],
                "connections": [],
                "description": "",
            }
            self._save_meta()

        # Загружаем ящики
        self.drawers = []
        for aaak_file in sorted(self.path.glob("*.aaak")):
            drawer = Drawer(str(aaak_file), self.codec)
            drawer.load()
            self.drawers.append(drawer)

        self.loaded = True

    def _save_meta(self):
        """Сохранить метаданные."""
        self.path.mkdir(parents=True, exist_ok=True)
        meta_path = self.path / "room.json"
        meta_path.write_text(
            json.dumps(self.meta, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def add_drawer(self, drawer_name: str) -> Drawer:
        """Создать новый ящик в комнате."""
        if not drawer_name.endswith(".aaak"):
            drawer_name += ".aaak"
        drawer_path = self.path / drawer_name
        drawer = Drawer(str(drawer_path), self.codec)
        drawer.load()
        self.drawers.append(drawer)
        return drawer

    def add_entry(self, aaak_content: str) -> str:
        """Добавить AAAK-запись в комнату (в новый или последний ящик)."""
        # Находим последний ящик или создаём новый
        if self.drawers:
            drawer = self.drawers[-1]
        else:
            drawer = self.add_drawer("drawer_001")

        # Парсим AAAK-строку в словарь
        try:
            parsed = self.codec.decode(aaak_content)
        except Exception:
            parsed = {"type": "RAW", "content": aaak_content[:500]}

        drawer.add_entry(parsed)
        return aaak_content

    def save_all(self):
        """Сохранить все ящики."""
        for drawer in self.drawers:
            drawer.save()

    def search(self, query: str, level: int = 0) -> List[Dict]:
        """Поиск по всем ящикам комнаты."""
        results = []
        for drawer in self.drawers:
            drawer_results = drawer.search(query, level)
            for r in drawer_results:
                r["room_id"] = self.meta.get("id", self.path.name)
                r["room_name"] = self.meta.get("name", "")
                results.append(r)
        return results

    def connect_to(self, other_room_id: str):
        """Добавить связь с другой комнатой."""
        connections = self.meta.setdefault("connections", [])
        if other_room_id not in connections:
            connections.append(other_room_id)
            self._save_meta()

    def get_connections(self) -> List[str]:
        """Получить список связанных комнат."""
        return self.meta.get("connections", [])

    def set_tag(self, tag: str):
        """Добавить тег комнате."""
        tags = self.meta.setdefault("tags", [])
        if tag not in tags:
            tags.append(tag)
            self._save_meta()

    def to_dict(self) -> Dict:
        """Полное представление комнаты."""
        return {
            "id": self.meta.get("id", self.path.name),
            "name": self.meta.get("name", ""),
            "tags": self.meta.get("tags", []),
            "connections": self.meta.get("connections", []),
            "description": self.meta.get("description", ""),
            "drawers_count": len(self.drawers),
            "total_entries": sum(len(d) for d in self.drawers),
        }

    def __repr__(self) -> str:
        return f"Room({self.meta.get('name', self.path.name)}, {len(self.drawers)} drawers)"