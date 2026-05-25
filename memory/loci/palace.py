"""
Palace — управление Крыльями (Wings), Комнатами (Rooms) и Ящиками (Drawers).
Организация пространственной памяти по методу локусов.

Иерархия:
  Дворец (Palace) → Крылья (Wings) → Комнаты (Rooms) → Ящики (Drawers)

Физически: data/loci/ → папки крыльев → папки комнат → .aaak файлы.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import deque
import json
import shutil

from memory.loci.room import Room


class Palace:
    """
    Дворец памяти — верхний уровень Когнитивных Локусов.
    Управляет созданием, поиском и навигацией по пространственной памяти.
    """

    def __init__(self, data_dir: str, codec: Any, config: Any = None):
        self.data_dir = Path(data_dir)
        self.codec = codec
        self.config = config
        self.wings: Dict[str, List[Room]] = {}  # wing_id -> [Room, ...]
        self.rooms: Dict[str, Room] = {}  # room_id -> Room
        self.current_room_id: Optional[str] = None
        self.initialized = False

        self._initialize()

    def _initialize(self):
        """Инициализация — создание структуры дворца."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Загружаем существующие крылья/комнаты
        self._load_wings()

        # Если пусто — создаём стандартные комнаты
        if not self.rooms:
            self._create_default_rooms()

        # Устанавливаем текущую комнату
        if self.rooms:
            self.current_room_id = list(self.rooms.keys())[0]

        self.initialized = True

    def _load_wings(self):
        """Загрузить все комнаты из файловой системы."""
        for wing_dir in sorted(self.data_dir.iterdir()):
            if not wing_dir.is_dir():
                continue
            wing_id = wing_dir.name
            self.wings[wing_id] = []

            for room_dir in sorted(wing_dir.iterdir()):
                if not room_dir.is_dir():
                    continue
                room_id = room_dir.name
                full_room_id = f"{wing_id}/{room_id}"
                room = Room(str(room_dir), self.codec)
                try:
                    room.load()
                except Exception as e:
                    print(f"[Palace] Ошибка загрузки комнаты {room_dir}: {e}")
                    continue
                self.rooms[full_room_id] = room
                self.wings[wing_id].append(room)

    def _create_default_rooms(self):
        """Создать стандартные комнаты из конфигурации."""
        default_wings = []
        if self.config:
            default_wings = self.config.get("loci", "default_wings", default=[])

        if not default_wings:
            # Жёстко заданные умолчания
            default_wings = [
                {
                    "id": "wing_general",
                    "name": "Общее",
                    "rooms": [
                        {"id": "room_general", "name": "Общая", "tags": ["general", "common"]},
                        {"id": "room_system", "name": "Система", "tags": ["system", "meta"]},
                    ],
                }
            ]

        for wing_cfg in default_wings:
            wing_id = wing_cfg["id"]
            wing_path = self.data_dir / wing_id
            wing_path.mkdir(parents=True, exist_ok=True)
            self.wings[wing_id] = []

            for room_cfg in wing_cfg.get("rooms", []):
                room_id = room_cfg["id"]
                room_path = wing_path / room_id
                room_path.mkdir(parents=True, exist_ok=True)

                meta = {
                    "id": room_id,
                    "name": room_cfg.get("name", room_id),
                    "tags": room_cfg.get("tags", []),
                    "connections": [],
                    "description": "",
                }
                meta_path = room_path / "room.json"
                if not meta_path.exists():
                    meta_path.write_text(
                        json.dumps(meta, indent=2, ensure_ascii=False),
                        encoding="utf-8"
                    )

                full_room_id = f"{wing_id}/{room_id}"
                room = Room(str(room_path), self.codec)
                room.load()
                self.rooms[full_room_id] = room
                self.wings[wing_id].append(room)

    def wake_up(self, query: str, level: int = 2) -> List[Dict]:
        """
        Пробуждение релевантных ящиков по уровням L0-L3.
        Возвращает список совпадающих записей.

        L0: точное совпадение
        L1: поиск по ключам AAAK
        L2: семантический (теги, ключевые слова)
        L3: полный обход графа комнат (BFS)
        """
        results = []

        if level == "all":
            level = 3
        if level <= 0:
            results.extend(self._search_rooms(query, 0))
        if level <= 1 and not results:
            results.extend(self._search_rooms(query, 1))
        if level <= 2 and not results:
            results.extend(self._search_rooms(query, 2))
        if level <= 3 and not results:
            results.extend(self._bfs_search(query))

        return results

    def _search_rooms(self, query: str, level: int) -> List[Dict]:
        """Поиск по всем комнатам на указанном уровне."""
        results = []
        for room_id, room in self.rooms.items():
            room_results = room.search(query, level)
            for r in room_results:
                r["room_id"] = room_id
            results.extend(room_results)

        # Сортируем по релевантности
        if level == 0:
            results.sort(key=lambda x: 0 if x.get("match") == "exact" else 1)
        elif level == 1:
            results.sort(key=lambda x: 0 if "key:" in str(x.get("match", "")) else 1)

        return results

    def _bfs_search(self, query: str) -> List[Dict]:
        """
        Полный обход графа комнат (BFS) начиная с текущей.
        Собирает все записи, имеющие хотя бы одно пересечение с запросом.
        """
        if not self.current_room_id:
            return []

        visited: Set[str] = set()
        queue = deque([self.current_room_id])
        results = []

        while queue:
            room_id = queue.popleft()
            if room_id in visited:
                continue
            visited.add(room_id)

            room = self.rooms.get(room_id)
            if not room:
                continue

            # Поиск в комнате на уровне 3 (полный текстовый)
            room_results = room.search(query, 3)
            for r in room_results:
                r["room_id"] = room_id
            results.extend(room_results)

            # Добавляем связанные комнаты в очередь
            for conn_id in room.get_connections():
                if conn_id not in visited:
                    queue.append(conn_id)

        return results

    def navigate_to(self, room_id: str) -> Optional[Dict]:
        """Переместиться в указанную комнату. Возвращает её содержимое."""
        room = self.rooms.get(room_id)
        if not room:
            # Пробуем найти неполным id
            for key, r in self.rooms.items():
                if key.endswith(room_id) or r.meta.get("name", "").lower() == room_id.lower():
                    room = r
                    room_id = key
                    break

        if room:
            self.current_room_id = room_id
            return room.to_dict()
        return None

    def add_to_room(self, room_id: str, aaak_content: str) -> bool:
        """Добавить AAAK-запись в указанную комнату."""
        room = self.rooms.get(room_id)
        if not room:
            return False
        room.add_entry(aaak_content)
        room.save_all()
        return True

    def create_room(self, wing_id: str, room_id: str, name: str,
                    tags: Optional[List[str]] = None,
                    connections: Optional[List[str]] = None) -> Room:
        """
        Создать новую комнату в указанном крыле.
        """
        if wing_id not in self.wings:
            self.wings[wing_id] = []

        room_path = self.data_dir / wing_id / room_id
        room_path.mkdir(parents=True, exist_ok=True)

        meta = {
            "id": room_id,
            "name": name,
            "tags": tags or [],
            "connections": connections or [],
            "description": "",
        }
        meta_path = room_path / "room.json"
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        full_room_id = f"{wing_id}/{room_id}"
        room = Room(str(room_path), self.codec)
        room.load()
        self.rooms[full_room_id] = room
        self.wings[wing_id].append(room)
        return room

    def get_current_room(self) -> Optional[Dict]:
        """Получить текущую комнату."""
        if self.current_room_id and self.current_room_id in self.rooms:
            return self.rooms[self.current_room_id].to_dict()
        return None

    def list_wings(self) -> List[Dict]:
        """Список всех крыльев с комнатами."""
        result = []
        for wing_id, rooms in self.wings.items():
            result.append({
                "id": wing_id,
                "rooms": [room.to_dict() for room in rooms],
            })
        return result

    def save_all(self):
        """Сохранить все комнаты."""
        for room in self.rooms.values():
            room.save_all()

    def __repr__(self) -> str:
        return f"Palace({len(self.rooms)} rooms in {len(self.wings)} wings)"