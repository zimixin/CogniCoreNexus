"""
Ящик (Drawer) — файл .aaak, содержащий одну или несколько записей.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional


class Drawer:
    """
    Ящик — физический файл .aaak с данными.
    Каждый файл может содержать несколько AAAK-записей.
    """

    def __init__(self, path: str, codec: Any):
        self.path = Path(path)
        self.codec = codec
        self.entries: List[Dict] = []
        self.loaded = False

    def load(self):
        """Загрузить записи из файла."""
        if not self.path.exists():
            self.entries = []
            self.loaded = True
            return

        content = self.path.read_text(encoding="utf-8").strip()
        if not content:
            self.entries = []
            self.loaded = True
            return

        # Разделяем на отдельные AAAK-выражения
        self.entries = self._parse_multiple(content)
        self.loaded = True

    def _parse_multiple(self, content: str) -> List[Dict]:
        """Парсит несколько AAAK-выражений из одного текста."""
        entries = []
        depth = 0
        start = 0

        for i, ch in enumerate(content):
            if ch == '(':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    expr = content[start:i + 1].strip()
                    if expr:
                        try:
                            parsed = self.codec.decode(expr)
                            entries.append(parsed)
                        except Exception as e:
                            # Пропускаем повреждённые записи
                            entries.append({
                                "type": "CORRUPTED",
                                "error": str(e),
                                "raw": expr[:200],
                            })
        return entries

    def add_entry(self, data: Dict) -> str:
        """Добавить запись в ящик (кодирует в AAAK и сохраняет)."""
        aaak_str = self.codec.encode(data)
        self.entries.append(data)
        return aaak_str

    def save(self):
        """Сохранить все записи в файл."""
        aaak_strs = []
        for entry in self.entries:
            try:
                aaak_strs.append(self.codec.encode(entry))
            except Exception as e:
                aaak_strs.append(f"(ERROR :message \"{e}\")")

        content = "\n\n".join(aaak_strs)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(content, encoding="utf-8")

    def search(self, query: str, level: int = 0) -> List[Dict]:
        """
        Поиск в ящике по уровням L0-L3.
        Возвращает совпадающие записи.
        """
        results = []
        query_lower = query.lower()

        for entry in self.entries:
            match = self._match_entry(entry, query_lower, level)
            if match:
                results.append({
                    "drawer": str(self.path),
                    "entry": entry,
                    "match": match,
                })

        return results

    def _match_entry(self, entry: Dict, query_lower: str, level: int) -> Optional[str]:
        """Проверяет, соответствует ли запись запросу на заданном уровне."""
        entry_str = str(entry).lower()

        # L0: точное совпадение
        if level <= 0:
            if query_lower in entry_str:
                return "exact"

        # L1: поиск по ключам и полям
        if level <= 1:
            # Проверяем поля
            for key, value in entry.items():
                if isinstance(value, str) and query_lower in value.lower():
                    return f"key:{key}"
                if key.lower() == query_lower:
                    return f"field_match:{key}"

        # L2: семантический (для простоты — по тегам и ключевым словам)
        if level <= 2:
            # Ищем по полям, похожим на tag (tag, tags, TAG, T, ...)
            for key, value in entry.items():
                kl = key.lower()
                if 'tag' in kl or kl in ('t', 'tg'):
                    if isinstance(value, str) and query_lower in value.lower():
                        return "tag"
                    if isinstance(value, list):
                        for tag in value:
                            if isinstance(tag, str) and query_lower in tag.lower():
                                return "tag"
            # Поиск по вложенным полям
            for key, value in entry.items():
                if isinstance(value, dict):
                    if self._match_entry(value, query_lower, 2):
                        return f"nested:{key}"

        # L3: полный текстовый поиск (подстрока в любой части записи)
        if level <= 3:
            if query_lower in entry_str:
                return f"bfs_match"

        return None

    def get_summary(self) -> Dict:
        """Краткая информация о ящике."""
        return {
            "path": str(self.path),
            "entries_count": len(self.entries),
            "types": list(set(e.get("type", "unknown") for e in self.entries)),
        }

    def __repr__(self) -> str:
        return f"Drawer({self.path.name}, {len(self.entries)} entries)"

    def __len__(self) -> int:
        return len(self.entries)