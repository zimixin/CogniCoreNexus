"""
Genome Manager — управление графом знаний через SQLite.
Хранит гены (понятия), отношения, локации (loci), сессии и агентов.
Поддерживает поиск по типу, паспорту и опционально — векторный поиск.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from memory.genome.gene import Gene, GenePassport
from memory.genome.relation import Relation
from core.utils import timestamp


class GenomeManager:
    """
    Менеджер графа знаний (Генома).

    Хранит:
    - genes: id, type, passport (JSON), aaak_compressed, full_text, provenance, embedding, timestamps
    - relations: source_id, target_id, relation_type, confidence, description
    - loci_index: room_id, wing, path, tags, linked_rooms
    - sessions: id, parent_id, query, answer, trace, room_id
    - agents: name, beliefs, knowledge, desires, nested_models

    Поиск: по типу, ключевым словам из passport/full_text.
    Опционально: векторный поиск через numpy/annoy по embedding.
    """

    def __init__(self, db_path: str, codec: Any = None,
                 use_vectors: bool = False, vector_backend: str = "none"):
        self.db_path = Path(db_path)
        self.codec = codec
        self.use_vectors = use_vectors
        self.vector_backend = vector_backend
        self._vector_index = None
        self._embeddings_model = None
        self._vectors: List[Tuple[str, List[float]]] = []  # [(gene_id, embedding)]

        self._init_db()

    # ─── Инициализация БД ──────────────────────────────────────────────

    def _init_db(self):
        """Создать таблицы и индексы, если их нет."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS genes (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    passport JSON NOT NULL,
                    aaak_compressed TEXT,
                    full_text TEXT,
                    provenance TEXT DEFAULT 'human',
                    embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    description TEXT DEFAULT '',
                    FOREIGN KEY (source_id) REFERENCES genes(id),
                    FOREIGN KEY (target_id) REFERENCES genes(id)
                );
                CREATE TABLE IF NOT EXISTS loci_index (
                    room_id TEXT PRIMARY KEY,
                    wing TEXT NOT NULL,
                    path TEXT NOT NULL,
                    tags JSON,
                    linked_rooms JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    parent_id TEXT,
                    query TEXT NOT NULL,
                    answer TEXT,
                    trace JSON,
                    room_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (room_id) REFERENCES loci_index(room_id)
                );
                CREATE TABLE IF NOT EXISTS agents (
                    name TEXT PRIMARY KEY,
                    beliefs JSON DEFAULT '[]',
                    knowledge JSON DEFAULT '[]',
                    desires JSON DEFAULT '[]',
                    nested_models JSON DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_genes_type ON genes(type);
                CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id);
                CREATE INDEX IF NOT EXISTS idx_loci_wing ON loci_index(wing);
            """)
            conn.commit()
        finally:
            conn.close()

    # ─── Гены ──────────────────────────────────────────────────────────

    def add_gene(self, data: Dict) -> str:
        """
        Добавить ген в базу.
        name и tags из Gene.from_dict записываются внутрь passport JSON.
        Возвращает id гена.
        """
        gene = Gene.from_dict(data)

        # Генерация AAAK-сжатия, если не предоставлено
        if not gene.aaak_compressed and self.codec:
            try:
                gene.aaak_compressed = self.codec.encode({
                    "type": gene.type.upper(),
                    "id": gene.id,
                    "name": gene.name,
                    "purpose": gene.passport.purpose,
                    "domain": gene.passport.domain,
                })
            except Exception:
                pass

        # Мигрируем name и tags из модели Gene в passport
        passport_dict = gene.passport.to_dict()
        if gene.name:
            passport_dict["name"] = gene.name
        if gene.tags:
            passport_dict["tags"] = gene.tags

        now = timestamp()
        gene.created_at = gene.created_at or now
        gene.updated_at = now

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO genes
                (id, type, passport, aaak_compressed, full_text,
                 provenance, embedding, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gene.id,
                gene.type,
                json.dumps(passport_dict, ensure_ascii=False),
                gene.aaak_compressed,
                gene.full_text,
                gene.provenance,
                None,  # embedding — placeholder; заполняется через _add_embedding
                gene.created_at,
                gene.updated_at,
            ))
            conn.commit()
        finally:
            conn.close()

        # Обновляем векторный индекс
        if self.use_vectors:
            self._add_embedding(gene)

        return gene.id

    def add_relation(self, data: Dict) -> int:
        """Добавить отношение между генами. Возвращает id отношения."""
        relation = Relation.from_dict(data)

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO relations (source_id, target_id, relation_type, confidence, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                relation.source_id,
                relation.target_id,
                relation.relation_type,
                relation.confidence,
                relation.description,
            ))
            conn.commit()
            rel_id = cursor.lastrowid
        finally:
            conn.close()
        return rel_id

    def find_genes(self, query: str, max_distance: int = 3) -> List[Dict]:
        """
        Поиск генов по запросу.

        Стратегия:
        1. Точное совпадение id
        2. Поиск по ключевым словам в full_text/passport/aaak_compressed
        3. BFS по отношениям (если совпадение найдено)
        4. Опционально: векторный поиск
        """
        query_lower = query.lower().strip()
        import re
        words = [re.sub(r'[^\w\s]', '', w) for w in query_lower.split() if len(w) > 2]
        words = [w for w in words if w]

        if not query_lower:
            return []

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()

            # 1. Точное совпадение id
            cursor.execute(
                "SELECT * FROM genes WHERE id = ? OR id = ?",
                (query_lower, query_lower.capitalize())
            )
            exact_matches = [self._row_to_gene(row) for row in cursor.fetchall()]

            # 1b. Точное совпадение имени в passport (для коротких запросов)
            if not exact_matches and len(query_lower) <= 3:
                cursor.execute(
                    "SELECT * FROM genes WHERE passport LIKE ?",
                    (f'%"name": "{query_lower}"%',)
                )
                exact_matches = [self._row_to_gene(row) for row in cursor.fetchall()]

            # 2. Поиск по ключевым словам
            if words:
                cols = ["type", "passport", "aaak_compressed", "full_text"]
                or_groups = []
                params = []
                for w in words:
                    variants = list(set([w, w.capitalize(), w.upper()]))
                    for v in variants:
                        for c in cols:
                            or_groups.append(f"lower({c}) LIKE lower(?)")
                            params.append(f"%{v}%")
                sql_conditions = " OR ".join(or_groups)

                cursor.execute(
                    f"SELECT DISTINCT * FROM genes WHERE {sql_conditions} LIMIT 20",
                    params
                )
                keyword_matches = []
                for row in cursor.fetchall():
                    gene = self._row_to_gene(row)
                    if gene["id"] not in {g["id"] for g in exact_matches}:
                        keyword_matches.append(gene)
            else:
                keyword_matches = []

            # 3. BFS от найденных генов через отношения
            bfs_matches = []
            if exact_matches or keyword_matches:
                visited_ids = {g["id"] for g in exact_matches}
                visited_ids.update(g["id"] for g in keyword_matches)
                queue = list(visited_ids)

                for _ in range(max_distance):
                    if not queue:
                        break
                    current = queue.pop(0)

                    cursor.execute("""
                        SELECT DISTINCT g.* FROM genes g
                        JOIN relations r ON r.source_id = g.id OR r.target_id = g.id
                        WHERE (r.source_id = ? OR r.target_id = ?)
                        AND g.id NOT IN ({})
                    """.format(",".join("?" * len(visited_ids))),
                        [current, current] + list(visited_ids)
                    )

                    for row in cursor.fetchall():
                        gene = self._row_to_gene(row)
                        if gene["id"] not in visited_ids:
                            visited_ids.add(gene["id"])
                            bfs_matches.append(gene)
                            queue.append(gene["id"])
        finally:
            conn.close()

        # 4. Векторный поиск (если включён)
        vector_matches = []
        if self.use_vectors and not exact_matches and not keyword_matches:
            vector_matches = self._vector_search(query, top_k=5)

        # Объединяем результаты
        all_results = exact_matches + keyword_matches + bfs_matches + vector_matches

        # Добавляем отношения к каждому гену
        for gene in all_results:
            gene["relations"] = self._get_gene_relations(gene["id"])

        return all_results[:20]

    def get_gene(self, gene_id: str) -> Optional[Dict]:
        """Получить ген по id."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM genes WHERE id = ?", (gene_id,))
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row:
            return None

        gene = self._row_to_gene(row)
        gene["relations"] = self._get_gene_relations(gene_id)
        return gene

    def list_genes(self, type_filter: Optional[str] = None,
                   limit: int = 100, offset: int = 0) -> List[Dict]:
        """Список генов с опциональной фильтрацией по типу."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            if type_filter:
                cursor.execute(
                    "SELECT * FROM genes WHERE type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (type_filter, limit, offset)
                )
            else:
                cursor.execute(
                    "SELECT * FROM genes ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset)
                )
            results = [self._row_to_gene(row) for row in cursor.fetchall()]
        finally:
            conn.close()
        return results

    def count_genes(self, type_filter: Optional[str] = None) -> int:
        """Количество генов."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            if type_filter:
                cursor.execute("SELECT COUNT(*) FROM genes WHERE type = ?", (type_filter,))
            else:
                cursor.execute("SELECT COUNT(*) FROM genes")
            count = cursor.fetchone()[0]
        finally:
            conn.close()
        return count

    def delete_gene(self, gene_id: str) -> bool:
        """Удалить ген и все его отношения."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM relations WHERE source_id = ? OR target_id = ?",
                           (gene_id, gene_id))
            cursor.execute("DELETE FROM genes WHERE id = ?", (gene_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
        finally:
            conn.close()
        return deleted

    # ─── Отношения ─────────────────────────────────────────────────────

    def _get_gene_relations(self, gene_id: str) -> List[Dict]:
        """Получить все отношения гена с правильным направлением."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT source_id, target_id, relation_type, confidence, description
                FROM relations WHERE source_id = ? OR target_id = ?
            """, (gene_id, gene_id))
            rows = cursor.fetchall()
        finally:
            conn.close()

        relations = []
        for row in rows:
            relations.append({
                "source_id": row[0],
                "target_id": row[1],
                "type": row[2],
                "confidence": row[3],
                "description": row[4],
                "direction": "out" if row[0] == gene_id else "in",
            })
        return relations

    # ─── Векторный поиск ───────────────────────────────────────────────

    def _add_embedding(self, gene: Gene):
        """Добавить эмбеддинг для гена (для векторного поиска)."""
        if not self.use_vectors:
            return

        # Заглушка — загрузка модели и вычисление эмбеддинга
        # В реальности здесь был бы вызов sentence-transformers
        # Для MVP храним пустой вектор
        self._vectors.append((gene.id, []))

    def _vector_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Векторный поиск (заглушка — возвращает пустой список)."""
        # Для полноценного векторного поиска нужно:
        # 1. Загрузить sentence-transformers модель (квантованную)
        # 2. Вычислить эмбеддинг запроса
        # 3. Найти косинусное сходство с эмбеддингами генов (из БД или in-memory)
        # 4. Вернуть топ-K
        return []

    # ─── Служебные методы ──────────────────────────────────────────────

    def _row_to_gene(self, row) -> Dict:
        """Преобразовать строку SQLite в словарь гена."""
        passport = json.loads(row[2]) if isinstance(row[2], str) else (row[2] or {})
        # name и tags извлекаются из passport для обратной совместимости
        name = passport.get("name", row[0])
        tags = passport.get("tags", [])
        return {
            "id": row[0],
            "name": name,
            "type": row[1],
            "passport": passport,
            "aaak_compressed": row[3],
            "full_text": row[4],
            "provenance": row[5],
            "embedding": row[6],
            "created_at": row[7],
            "updated_at": row[8],
            "tags": tags,
            "relations": [],
        }

    # ─── Loci Index (локации) ──────────────────────────────────────────

    def update_loci_index(self, room_id: str, wing: str, path: str,
                          tags: Optional[List[str]] = None,
                          linked_rooms: Optional[List[str]] = None):
        """Создать или обновить запись локации."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO loci_index
                (room_id, wing, path, tags, linked_rooms, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                room_id,
                wing,
                path,
                json.dumps(tags or [], ensure_ascii=False),
                json.dumps(linked_rooms or [], ensure_ascii=False),
                timestamp(),
            ))
            conn.commit()
        finally:
            conn.close()

    def get_loci_index(self, room_id: str) -> Optional[Dict]:
        """Получить запись локации по room_id."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM loci_index WHERE room_id = ?", (room_id,))
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row:
            return None

        return {
            "room_id": row[0],
            "wing": row[1],
            "path": row[2],
            "tags": json.loads(row[3]) if isinstance(row[3], str) else (row[3] or []),
            "linked_rooms": json.loads(row[4]) if isinstance(row[4], str) else (row[4] or []),
            "updated_at": row[5],
        }

    def list_loci(self, wing: Optional[str] = None) -> List[Dict]:
        """Список всех локаций, опционально отфильтрованных по wing."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            if wing:
                cursor.execute("SELECT * FROM loci_index WHERE wing = ? ORDER BY wing", (wing,))
            else:
                cursor.execute("SELECT * FROM loci_index ORDER BY wing, room_id")
            rows = cursor.fetchall()
        finally:
            conn.close()

        results = []
        for row in rows:
            results.append({
                "room_id": row[0],
                "wing": row[1],
                "path": row[2],
                "tags": json.loads(row[3]) if isinstance(row[3], str) else (row[3] or []),
                "linked_rooms": json.loads(row[4]) if isinstance(row[4], str) else (row[4] or []),
                "updated_at": row[5],
            })
        return results

    # ─── Сессии ────────────────────────────────────────────────────────

    def save_session(self, session_data: Dict):
        """Сохранить или обновить сессию."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sessions
                (id, parent_id, query, answer, trace, room_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data["id"],
                session_data.get("parent_id"),
                session_data["query"],
                session_data.get("answer"),
                json.dumps(session_data.get("trace", {}), ensure_ascii=False),
                session_data.get("room_id"),
                session_data.get("created_at", timestamp()),
            ))
            conn.commit()
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Получить сессию по id."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row:
            return None

        return {
            "id": row[0],
            "parent_id": row[1],
            "query": row[2],
            "answer": row[3],
            "trace": json.loads(row[4]) if isinstance(row[4], str) else (row[4] or {}),
            "room_id": row[5],
            "created_at": row[6],
        }

    # ─── Агенты ────────────────────────────────────────────────────────

    def save_agent(self, agent_data: Dict):
        """Сохранить или обновить агента."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO agents
                (name, beliefs, knowledge, desires, nested_models, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                agent_data["name"],
                json.dumps(agent_data.get("beliefs", []), ensure_ascii=False),
                json.dumps(agent_data.get("knowledge", []), ensure_ascii=False),
                json.dumps(agent_data.get("desires", []), ensure_ascii=False),
                json.dumps(agent_data.get("nested_models", {}), ensure_ascii=False),
                timestamp(),
            ))
            conn.commit()
        finally:
            conn.close()

    def get_agent(self, name: str) -> Optional[Dict]:
        """Получить агента по имени."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agents WHERE name = ?", (name,))
            row = cursor.fetchone()
        finally:
            conn.close()

        if not row:
            return None

        return {
            "name": row[0],
            "beliefs": json.loads(row[1]) if isinstance(row[1], str) else (row[1] or []),
            "knowledge": json.loads(row[2]) if isinstance(row[2], str) else (row[2] or []),
            "desires": json.loads(row[3]) if isinstance(row[3], str) else (row[3] or []),
            "nested_models": json.loads(row[4]) if isinstance(row[4], str) else (row[4] or {}),
            "updated_at": row[5],
        }

    def list_agents(self) -> List[Dict]:
        """Список всех агентов."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agents ORDER BY name")
            rows = cursor.fetchall()
        finally:
            conn.close()

        results = []
        for row in rows:
            results.append({
                "name": row[0],
                "beliefs": json.loads(row[1]) if isinstance(row[1], str) else (row[1] or []),
                "knowledge": json.loads(row[2]) if isinstance(row[2], str) else (row[2] or []),
                "desires": json.loads(row[3]) if isinstance(row[3], str) else (row[3] or []),
                "nested_models": json.loads(row[4]) if isinstance(row[4], str) else (row[4] or {}),
                "updated_at": row[5],
            })
        return results

    def __repr__(self) -> str:
        return f"GenomeManager(db={self.db_path.name}, genes={self.count_genes()})"