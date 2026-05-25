"""
AAAK 2.0 — кодек для сверхплотного представления знаний.
Синтаксис: S-выражения с именованными полями (:key value).

Формат:
    (TYPE [id]
      :field1 value1
      :field2 (SUBTYPE sub_val :sub_f1 sub_v1 ...))

Кодек поддерживает:
  - encode(dict) -> str — превращает словарь в AAAK-строку
  - decode(str) -> dict — разбирает AAAK-строку в словарь
  - Авто-замена длинных имён на короткие (из dictionary.yaml)
  - Вложенные структуры любой глубины

Внутренний парсер: рекурсивный descent (AAKParser).
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml


class AAAKDictionary:
    """Загружает и управляет словарём сокращений."""

    def __init__(self, dict_path: Optional[str] = None):
        self.code_to_name: Dict[str, str] = {}
        self.name_to_code: Dict[str, str] = {}
        self.auto_shorten_pool: Dict[str, int] = {}
        self.auto_shorten_threshold: int = 5

        if dict_path:
            self.load(dict_path)

    def load(self, path: str):
        """Загрузить словарь из YAML-файла."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Словарь не найден: {path}")
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not data:
            return
        for code, name in data.items():
            if isinstance(name, str):
                self.code_to_name[code] = name
                self.name_to_code[name] = code

    def load_domain_profile(self, path: str):
        """Загрузить доменный профиль (расширяет основной словарь)."""
        p = Path(path)
        if not p.exists():
            return
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not data or "shortcuts" not in data:
            return
        for code, name in data["shortcuts"].items():
            if isinstance(name, str):
                self.code_to_name[code] = name
                self.name_to_code[name] = code

    def shorten(self, name: str) -> str:
        """Найти или создать сокращение для полного имени."""
        # Прямой поиск
        if name in self.name_to_code:
            return self.name_to_code[name]

        # Авто-сокращение: первые 3-4 буквы в верхнем регистре
        short = "".join(w[0].upper() for w in name.split() if w)
        if len(short) < 2:
            short = name[:3].upper()
        self.name_to_code[name] = short
        self.code_to_name[short] = name
        return short

    def expand(self, code: str) -> str:
        """Раскрыть сокращение в полное имя."""
        return self.code_to_name.get(code, code)

    def register_auto_shorten(self, entity_name: str) -> Optional[str]:
        """Авто-генерация алиаса для частых сущностей.
        Возвращает код, если сущность превысила порог."""
        self.auto_shorten_pool[entity_name] = self.auto_shorten_pool.get(entity_name, 0) + 1
        count = self.auto_shorten_pool[entity_name]
        if count == self.auto_shorten_threshold and entity_name not in self.name_to_code:
            short = self.shorten(entity_name)
            return short
        return None


class AAAKCodec:
    """
    Кодек для языка сверхплотного представления AAAK 2.0.
    Использует рекурсивный descent парсер.
    """

    # Регулярка для токенизации: строки в кавычках, скобки, :поля, числа с точкой, прочее
    _TOKEN_PATTERN = r'"[^"]*"|\(|\)|:[a-z_]+|[^\s()]+|\d+\.\d+'

    def __init__(self, dictionary: Optional[AAAKDictionary] = None):
        self.dict = dictionary or AAAKDictionary()

    # ──────────────────────────────────────────────
    #  ENCODE — словарь -> AAAK-строка
    #  Сокращение (shorten) применяется ДО сборки
    # ──────────────────────────────────────────────

    def encode(self, data: Dict[str, Any], indent: int = 0) -> str:
        """
        Превращает словарь в AAAK S-выражение.

        Пример:
            encode({"type": "EVENT", "id": "test",
                     "fields": {"agent": "user", "action": "query"}})
            -> "(EVENT test\\n  :agent user\\n  :action query)"
        """
        if not isinstance(data, dict):
            return self._encode_value(data)

        # КОПИРУЕМ, чтобы не мутировать оригинал
        data = {k: v for k, v in data.items()}

        # Определяем тип и id
        entry_type = data.pop("type", None) or data.pop("_type", None) or "ITEM"
        entry_id = data.pop("id", None) or data.pop("_id", None)

        # Собираем поля
        parts = []
        entry_type_short = self.dict.shorten(entry_type) if entry_type else "ITEM"
        if entry_id:
            parts.append(f"({entry_type_short} {entry_id}")
        else:
            parts.append(f"({entry_type_short}")

        for key, value in data.items():
            key_short = self.dict.shorten(key) if isinstance(key, str) else key
            if isinstance(value, dict):
                # Рекурсивно кодируем вложенный словарь
                nested = self.encode(dict(value), indent + 1)
                parts.append(f"\n{'  ' * (indent + 1)}:{key_short} {nested}")
            elif isinstance(value, list):
                # Список значений — явный маркер LIST
                list_items = []
                for item in value:
                    if isinstance(item, dict):
                        list_items.append(self.encode(item, indent + 1))
                    else:
                        list_items.append(self._encode_value(item))
                items_str = "\n".join(
                    f"{'  ' * (indent + 1)}" + li for li in list_items
                )
                parts.append(f"\n{'  ' * (indent + 1)}:{key_short} (LIST\n{items_str}\n{'  ' * (indent + 1)})")
            else:
                val_str = self._encode_value(value)
                parts.append(f"\n{'  ' * (indent + 1)}:{key_short} {val_str}")

        # Закрываем скобку
        parts.append(f"\n{'  ' * indent})")

        return "".join(parts)

    def _encode_value(self, value: Any) -> str:
        """Кодирует примитивное значение."""
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            # Экранируем спецсимволы
            if " " in value or ")" in value or "(" in value:
                return f'"{value}"'
            return value
        if value is None:
            return "nil"
        if isinstance(value, list):
            items = " ".join(self._encode_value(v) for v in value)
            return f"({items})"
        return str(value)

    # ──────────────────────────────────────────────
    #  DECODE — AAAK-строка -> словарь
    #  Раскрытие (expand) применяется ПОСЛЕ парсинга
    # ──────────────────────────────────────────────

    def decode(self, text: str) -> Dict[str, Any]:
        """
        Разбирает AAAK S-выражение в словарь.
        Использует рекурсивный descent парсер.
        """
        text = text.strip()
        if not text.startswith("("):
            raise ValueError(f"Неверный AAAK-формат: ожидается '(' в начале:\n{text[:100]}")

        tokens = self._tokenize(text)
        parsed, pos = self._parse_expr(tokens, 0)

        if isinstance(parsed, list):
            # Верхнеуровневый список — оборачиваем в словарь
            return {"_items": parsed}

        if not isinstance(parsed, dict):
            raise ValueError(f"Ожидался словарь на верхнем уровне, получено: {type(parsed).__name__}")

        # Пост-обработка: раскрываем сокращения (expand) и нормализуем структуру
        result = self._expand_tree(parsed)
        return result

    def _tokenize(self, text: str) -> List[str]:
        """Токенизирует AAAK-строку с помощью regex.

        Pattern components:
          "..."  — строки в двойных кавычках
          (      — открывающая скобка
          )      — закрывающая скобка
          :field — именованные поля
          token  — любые непробельные непунктуационные токены
          float  — числа с плавающей точкой (избыточно, но явно)
        """
        return re.findall(self._TOKEN_PATTERN, text)

    def _parse_expr(self, tokens: List[str], pos: int) -> tuple:
        """Парсит одно выражение: S-выражение или атом.
        Возвращает (parsed_value, next_pos)."""
        if pos >= len(tokens):
            raise ValueError("Неожиданный конец ввода")

        token = tokens[pos]
        if token == '(':
            return self._parse_sexp(tokens, pos)
        else:
            val = self._parse_atom(token)
            return val, pos + 1

    def _parse_sexp(self, tokens: List[str], pos: int) -> tuple:
        """Парсит S-выражение рекурсивным descent.

        Грамматика:
          sexp ::= '(' symbol [id] item* ')'
          item ::= ':' key value  |  value

        Внутреннее представление ДО expand:
          - (TYPE id :f1 v1 :f2 v2)
            -> {'_raw_type': 'TYPE', '_raw_id': 'id',
                '_fields': {'f1': v1, 'f2': v2}}

          - (LIST a b c) или (a b c) без полей
            -> [a, b, c]  (список)

          - (TYPE :f1 v1 a b c)  — смешанный стиль
            -> {'_raw_type': 'TYPE',
                '_fields': {'f1': v1},
                '_items': [a, b, c]}
        """
        assert tokens[pos] == '(', f"Ожидается '(' на позиции {pos}, получено: {tokens[pos]}"
        pos += 1

        if pos >= len(tokens):
            raise ValueError("Незакрытое S-выражение: конец ввода после '('")

        if tokens[pos] == ')':
            raise ValueError("Пустое S-выражение: () не допускается")

        # ── 1. Читаем symbol (type) ──
        symbol_token = tokens[pos]
        pos += 1

        # ── 2. Определяем режим: список или словарь ──
        is_list = (symbol_token == 'LIST')

        # Смотрим, есть ли :поля в оставшихся токенах до ')'
        has_colon = self._any_colon_before_close(tokens, pos)

        if is_list or not has_colon:
            # ── РЕЖИМ СПИСКА: (LIST ...) или (type val1 val2 ...) ──
            items = []
            while pos < len(tokens) and tokens[pos] != ')':
                val, pos = self._parse_expr(tokens, pos)
                items.append(val)

            if pos >= len(tokens):
                raise ValueError("Незакрытое S-выражение: не найдена ')'")
            pos += 1  # eat ')'

            return items, pos

        else:
            # ── РЕЖИМ СЛОВАРЯ: (TYPE :field value ...) ──
            result: Dict[str, Any] = {'_raw_type': symbol_token}

            # Пробуем прочитать id (следующий токен не ':' и не ')')
            if pos < len(tokens) and tokens[pos] != ')' and not tokens[pos].startswith(':'):
                result['_raw_id'] = self._parse_atom(tokens[pos])
                pos += 1

            # Парсим именованные поля и позиционные items
            fields: Dict[str, Any] = {}
            items: List[Any] = []

            while pos < len(tokens) and tokens[pos] != ')':
                token = tokens[pos]
                if token.startswith(':'):
                    # Именованное поле
                    key = token[1:]  # убираем ':'
                    pos += 1
                    if pos < len(tokens) and tokens[pos] != ')':
                        value, pos = self._parse_expr(tokens, pos)
                    else:
                        value = None
                    fields[key] = value
                else:
                    # Позиционный item (смешанный стиль)
                    value, pos = self._parse_expr(tokens, pos)
                    items.append(value)

            if pos >= len(tokens):
                raise ValueError("Незакрытое S-выражение: не найдена ')'")
            pos += 1  # eat ')'

            if fields:
                result['_fields'] = fields
            if items:
                result['_items'] = items

            return result, pos

    @staticmethod
    def _any_colon_before_close(tokens: List[str], start: int) -> bool:
        """Проверяет, есть ли :поля в токенах начиная с start до ')'."""
        depth = 0
        for i in range(start, len(tokens)):
            t = tokens[i]
            if t == '(':
                depth += 1
            elif t == ')':
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and t.startswith(':'):
                return True
        return False

    @staticmethod
    def _parse_atom(token: str):
        """Парсит атомарное значение (число, буль, строка, nil, символ)."""
        # Строка в кавычках
        if token.startswith('"') and token.endswith('"'):
            return token[1:-1]

        # Числа
        try:
            if '.' in token:
                return float(token)
            else:
                return int(token)
        except (ValueError, TypeError):
            pass

        # Специальные значения
        if token == "nil":
            return None
        if token == "true":
            return True
        if token == "false":
            return False

        # Обычный символ/имя
        return token

    def _expand_tree(self, node: Any) -> Any:
        """Пост-обработка AST: рекурсивно раскрывает сокращения (expand)
        и нормализует внутреннюю структуру во внешний словарь.

        expand вызывается для:
          - _raw_type  -> 'type'
          - _raw_id    -> 'id'
          - ключи в _fields
        """
        if isinstance(node, dict):
            if '_fields' in node or '_raw_type' in node:
                # Это S-выражение — нормализуем
                result: Dict[str, Any] = {}

                # Тип
                raw_type = node.get('_raw_type', 'ITEM')
                if isinstance(raw_type, str):
                    result['type'] = self.dict.expand(raw_type)
                else:
                    result['type'] = str(raw_type)

                # ID
                if '_raw_id' in node:
                    raw_id = node['_raw_id']
                    if isinstance(raw_id, str):
                        result['id'] = raw_id
                    else:
                        result['id'] = str(raw_id)

                # Поля с раскрытием ключей
                for key, value in node.get('_fields', {}).items():
                    expanded_key = self.dict.expand(key) if isinstance(key, str) else key
                    result[expanded_key] = self._expand_tree(value)

                # Позиционные items (смешанный стиль)
                if '_items' in node:
                    result['_items'] = [self._expand_tree(item) for item in node['_items']]

                return result
            else:
                # Обычный словарь (например, внутри списка)
                return {k: self._expand_tree(v) for k, v in node.items()}

        elif isinstance(node, list):
            return [self._expand_tree(item) for item in node]

        else:
            return node

    # ──────────────────────────────────────────────
    #  COMPRESS — сжатие произвольного текста
    # ──────────────────────────────────────────────

    def compress(self, text: str) -> str:
        """
        Сжимает произвольный текст в AAAK-формат.
        Извлекает ключевые сущности, удаляет стоп-слова.
        """
        # Простая имплементация: извлекаем ключевые слова
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text)
        # Удаляем короткие и стоп-слова
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
                     'been', 'being', 'have', 'has', 'had', 'do', 'does',
                     'did', 'will', 'would', 'could', 'should', 'may', 'might',
                     'shall', 'can', 'need', 'dare', 'ought', 'used', 'to',
                     'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                     'as', 'into', 'through', 'during', 'before', 'after',
                     'above', 'below', 'between', 'out', 'off', 'over', 'under'}
        keywords = [w for w in words if w.lower() not in stop_words and len(w) > 2]
        # Собираем топ-15 ключевых слов
        from collections import Counter
        top_keywords = [w for w, _ in Counter(keywords).most_common(15)]

        return self.encode({
            "type": "COMPRESSED",
            "content": " ".join(top_keywords),
            "original_length": len(text),
        })


# Быстрый тест
if __name__ == "__main__":
    dict_path = Path(__file__).parent / "dictionary.yaml"
    aaak_dict = AAAKDictionary(str(dict_path))
    codec = AAAKCodec(aaak_dict)

    test_data = {
        "type": "EVENT",
        "id": "code_review",
        "time": "20250410T1500",
        "agent": "Alexey",
        "subject": "PaymentService",
        "findings": [
            {
                "type": "VIOLATION",
                "id": "SRP",
                "cause": "multi_role VALID API LOG",
                "severity": "high",
                "confidence": 0.95,
            }
        ],
    }

    encoded = codec.encode(test_data)
    print("=== ENCODED ===")
    print(encoded)

    decoded = codec.decode(encoded)
    print("\n=== DECODED ===")
    import json
    print(json.dumps(decoded, indent=2, ensure_ascii=False))