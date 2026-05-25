"""
CogniCore Nexus — ядро когнитивной системы.
Инициализирует все подсистемы и реализует главный цикл обработки запросов.

process_query(query) — основной метод, проходящий через L0-L3 пробуждение
с ранней остановкой (STOP при достаточной уверенности),
сбор контекста, логический вывод, вызов LLM и обновление памяти.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import sqlite3

from core.config import Config, PROJECT_ROOT
from aaak.codec import AAAKCodec, AAAKDictionary
from core.utils import timestamp, aaak_timestamp
from symbols.symbol_manager import SymbolManager
from logic.inference_engine import InferenceEngine
from cognition.cognitive_arch import CognitiveArchitecture
from cognition.working_memory import WorkingMemory
from cognition.procedural_memory import ProceduralMemory
from memory.loci.palace import Palace
from memory.genome.genome_manager import GenomeManager
from llm.interface import LLMFactory
from tools.tool_manager import ToolManager
from tom.theory_of_mind import TheoryOfMind

logger = logging.getLogger("cognicore.nexus")


class CogniCoreNexus:
    """
    Главное ядро системы. Координирует все подсистемы.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = Config(config_path)
        self._init_logging()
        self._init_aaak()
        self._init_memory()
        self._init_cognition()
        self._init_llm()
        self._init_tools()
        self._init_tom()
        self._init_symbols()
        self._init_logic()

        self.session_id = 0
        self.dialog_history: List[Dict] = []

        # Инициализируем loci_index из существующих комнат
        self._sync_loci_index()

        logger.info("CogniCore Nexus инициализирован. LLM: %s, Векторы: %s",
                     self.config.get("llm", "provider", default="none"),
                     self.config.get("memory", "use_vectors", default=False))

    def _sync_loci_index(self):
        """Синхронизировать loci_index с файловой системой комнат."""
        try:
            for room_id, room in self.palace.rooms.items():
                wing, rid = room_id.split("/", 1)
                tags = room.meta.get("tags", [])
                connections = room.meta.get("connections", [])
                self.genome.update_loci_index(
                    room_id=room_id,
                    wing=wing,
                    path=str(room.path),
                    tags=tags,
                    linked_rooms=connections,
                )
        except Exception as e:
            logger.warning("loci_index sync skipped: %s", e)

    # ─── Инициализация подсистем ──────────────────────────────────────

    def _init_logging(self):
        """Настройка логирования."""
        logging.basicConfig(
            level=getattr(logging, self.config.get("log_level", default="INFO"), logging.INFO),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    def _init_aaak(self):
        """Инициализация AAAK-кодека."""
        dict_path = PROJECT_ROOT / self.config.get("aaak", "dictionary", default="aaak/dictionary.yaml")
        self.aaak_dict = AAAKDictionary(str(dict_path) if dict_path.exists() else None)
        self.codec = AAAKCodec(self.aaak_dict)

        profiles_dir = PROJECT_ROOT / self.config.get("aaak", "domain_profiles_dir",
                                                       default="aaak/domain_profiles/")
        if profiles_dir.exists():
            for profile_file in profiles_dir.glob("*.yaml"):
                self.aaak_dict.load_domain_profile(str(profile_file))

        self.auto_shorten_threshold = self.config.get("aaak", "auto_shorten_threshold", default=5)

    def _init_memory(self):
        """Инициализация подсистем памяти."""
        loci_dir = PROJECT_ROOT / self.config.get("loci", "data_dir", default="data/loci")
        self.palace = Palace(
            data_dir=str(loci_dir),
            codec=self.codec,
            config=self.config,
        )

        db_path = PROJECT_ROOT / self.config.get("genome", "db_path", default="data/genome.db")
        self.genome = GenomeManager(
            db_path=str(db_path),
            codec=self.codec,
            use_vectors=self.config.get("memory", "use_vectors", default=False),
            vector_backend=self.config.get("memory", "vector_backend", default="none"),
        )

    def _init_cognition(self):
        """Инициализация когнитивной архитектуры."""
        wm_size = self.config.get("cognition", "working_memory_size", default=20)
        max_steps = self.config.get("cognition", "max_inference_steps", default=50)
        max_depth = self.config.get("cognition", "max_planning_depth", default=5)

        self.working_memory = WorkingMemory(max_size=wm_size)
        # Загружаем матрицы из YAML, если есть
        matrices_dir = PROJECT_ROOT / "data" / "matrices"
        self.procedural_memory = ProceduralMemory(
            matrices_dir=str(matrices_dir) if matrices_dir.exists() else None
        )
        self.cognitive_arch = CognitiveArchitecture(
            working_memory=self.working_memory,
            procedural_memory=self.procedural_memory,
            max_inference_steps=max_steps,
            max_planning_depth=max_depth,
        )

    def _init_llm(self):
        """Инициализация LLM-интерфейса."""
        provider = self.config.get("llm", "provider", default="none")
        import os
        if provider != "none" and not self.config.get("llm", "api_key", default=""):
            env_key = os.environ.get("OPENROUTER_API_KEY", "")
            if env_key:
                self.config.data.setdefault("llm", {})["api_key"] = env_key
        self.llm = LLMFactory.create(provider, self.config)

    def _init_tools(self):
        """Инициализация менеджера инструментов."""
        self.tool_manager = ToolManager()

    def _init_tom(self):
        """Инициализация Theory of Mind."""
        self.tom = TheoryOfMind()

    def _init_symbols(self):
        """Инициализация символьного менеджера."""
        self.symbol_manager = SymbolManager()

    def _init_logic(self):
        """Инициализация логического движка."""
        self.inference_engine = InferenceEngine(
            max_steps=self.config.get("cognition", "max_inference_steps", default=50)
        )

    # ─── Вспомогательные методы ──────────────────────────────────────

    def _error_response(self, code: str, detail: str) -> Dict:
        """Стандартный ответ с ошибкой."""
        return {
            "answer": None,
            "error": {"code": code, "detail": detail},
            "trace": [],
            "confidence": 0.0,
            "mode": "error",
        }

    # ─── L0-L3 поиск с ранней остановкой ────────────────────────────

    def _search_memory(self, query: str, trace: List[str]) -> Dict[str, Any]:
        """
        Многоуровневый поиск с ранней остановкой (L0-L3).

        L0 — точное совпадение → STOP
        L1 — ключи AAAK → STOP при score >= threshold
        L2 — семантический / гены → STOP при score >= threshold
        L3 — BFS граф локусов → всегда возвращает что-то
        """
        threshold = self.config.get("memory", "search_threshold", default=0.7)
        use_vectors = self.config.get("memory", "use_vectors", default=False)
        results: List[Dict] = []
        stopped_at = "L0"
        found_loci = []
        found_genes = []

        # L0: точное совпадение
        trace.append("[L0] Точное совпадение...")
        l0 = self.palace.wake_up(query, level=0)
        trace.append(f"  L0: найдено {len(l0)} результатов")
        if l0:
            found_loci.extend(l0)
            trace.append(f"  → STOP на L0 (точное совпадение)")
            stopped_at = "L0"
            results.extend(l0)
            return {
                "loci": found_loci,
                "genes": found_genes,
                "stopped_at": stopped_at,
            }

        # L1: поиск по ключам AAAK
        trace.append("[L1] Поиск по ключам AAAK...")
        l1 = self.palace.wake_up(query, level=1)
        trace.append(f"  L1: найдено {len(l1)} результатов")
        if l1:
            score = min(0.85, 0.5 + len(l1) * 0.08)
            trace.append(f"  L1 уверенность: {score:.2f}, порог: {threshold}")
            found_loci.extend(l1)
            if score >= threshold:
                trace.append(f"  → STOP на L1 (уверенность >= порога)")
                stopped_at = "L1"
                results.extend(l1)
                return {
                    "loci": found_loci,
                    "genes": found_genes,
                    "stopped_at": stopped_at,
                }

        # L2: семантический поиск + гены
        trace.append("[L2] Семантический поиск + гены...")
        l2 = self.palace.wake_up(query, level=2)
        genome_results = self.genome.find_genes(query)
        trace.append(f"  L2: {len(l2)} локусов + {len(genome_results)} генов")
        found_loci.extend(l2)
        found_genes.extend(genome_results)
        combined = l2 + genome_results
        if combined:
            score = min(0.75, 0.3 + len(combined) * 0.04)
            trace.append(f"  L2 уверенность: {score:.2f}, порог: {threshold}, use_vectors={use_vectors}")
            if use_vectors and score >= threshold:
                trace.append(f"  → STOP на L2 (векторный поиск, уверенность >= порога)")
                stopped_at = "L2"
                results.extend(combined)
                return {
                    "loci": found_loci,
                    "genes": found_genes,
                    "stopped_at": stopped_at,
                }

        # L3: полный обход графа локусов (BFS) — всегда возвращает
        trace.append("[L3] Полный обход графа локусов (BFS)...")
        l3 = self.palace.wake_up(query, level=3)
        trace.append(f"  L3: найдено {len(l3)} результатов")
        found_loci.extend(l3)
        trace.append(f"  → STOP на L3 (финальный уровень)")
        stopped_at = "L3"

        # Дедупликация
        seen_ids = set()
        deduped = []
        for entry in found_loci:
            eid = entry.get("id", entry.get("path", ""))
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                deduped.append(entry)

        return {
            "loci": deduped,
            "genes": found_genes,
            "stopped_at": stopped_at,
        }

    # ─── Основной метод обработки запроса ────────────────────────────

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Главный метод обработки запроса.

        Этапы:
        1. L0-L3 поиск с ранней остановкой
        2. Сбор контекста
        3. Логический вывод
        4. Выбор и запуск когнитивной матрицы
        5. Вызов LLM (с fallback)
        6. Обновление памяти
        7. Возврат ответа с трассировкой
        """
        try:
            return self._process_query_inner(query)
        except FileNotFoundError as e:
            logger.error(f"Файл локуса не найден: {e}")
            return self._error_response("loci_missing", str(e))
        except sqlite3.DatabaseError as e:
            logger.error(f"Ошибка БД: {e}")
            return self._error_response("db_error", str(e))
        except Exception as e:
            logger.exception(f"Неожиданная ошибка в process_query")
            return self._error_response("unknown", str(e))

    def _process_query_inner(self, query: str) -> Dict[str, Any]:
        """Внутренняя реализация process_query без обработки ошибок."""
        trace: List[str] = []
        self.session_id += 1

        # 1. L0-L3 поиск с ранней остановкой
        search_result = self._search_memory(query, trace)
        loci_results = search_result["loci"]
        genome_results = search_result["genes"]

        # 2. Сбор контекста
        context = self._build_context(query, loci_results, genome_results)
        trace.append(
            f"  Контекст: {len(context.get('loci_entries', []))} локусов, "
            f"{len(context.get('genes', []))} генов"
        )

        # 3. Логический вывод
        trace.append("[Logic] Применение правил вывода...")
        inferences = self.inference_engine.forward_chain(context)
        trace.append(f"  Выведено {len(inferences)} новых фактов")
        if inferences:
            context["inferences"] = inferences

        # 4. Когнитивная матрица
        trace.append("[Matrix] Выбор когнитивной матрицы...")
        matrix = self.cognitive_arch.select_matrix(query, context)
        if matrix:
            trace.append(f"  Запущена матрица: {matrix.get('name', 'unnamed')}")
            matrix_result = self.cognitive_arch.run_matrix(matrix, context, self)
            context["matrix_result"] = matrix_result
            trace.append(f"  Матрица выполнена: {matrix_result.get('status', 'unknown')}")
        else:
            trace.append("  Матрица не выбрана")

        # 5. Вызов LLM (с fallback)
        system_prompt = self._build_system_prompt(context)
        llm_response = ""
        llm_used = False
        llm_chain = getattr(self.llm, "chain", None)

        if self.llm is not None:
            provider_name = getattr(self.llm, "name", str(self.llm))
            trace.append(f"[LLM] Отправка запроса ({provider_name})...")
            try:
                llm_response = self.llm.generate(
                    prompt=query,
                    system=system_prompt,
                    temperature=self.config.get("llm", "temperature", default=0.7),
                )
                llm_used = True
                trace.append(f"  LLM ответ получен ({len(llm_response)} символов)")
            except Exception as e:
                trace.append(f"  LLM ошибка: {e}")
                llm_response = f"[LLM недоступен: {e}]"
        else:
            trace.append("[LLM] LLM не подключена — символьный режим")
            llm_response = self._symbolic_response(query, context, inferences)

        # 6. Обновление памяти
        trace.append("[Memory] Сохранение диалога в Локусы...")
        self._save_to_memory(query, llm_response, context)
        trace.append("  Диалог сохранён")

        # 7. Рабочая память
        self.working_memory.add({
            "role": "user",
            "content": query,
            "session": self.session_id,
        })
        self.working_memory.add({
            "role": "assistant",
            "content": llm_response,
            "session": self.session_id,
        })

        # 8. Уверенность
        confidence = self._compute_confidence(context, inferences, llm_used)

        # 9. AAAK авто-сокращение
        auto_shorten = self.aaak_dict.register_auto_shorten(query)
        if auto_shorten:
            trace.append(f"  AAAK: алиас '{auto_shorten}' для частого запроса")

        # 10. Сохраняем сессию в БД
        try:
            self.genome.save_session({
                "id": f"session_{self.session_id}",
                "parent_id": None,
                "query": query,
                "answer": llm_response[:500],
                "trace": trace,
                "room_id": self.palace.current_room_id,
            })
        except Exception as e:
            logger.warning("Не удалось сохранить сессию: %s", e)

        result = {
            "answer": llm_response,
            "trace": trace,
            "new_genes": len(inferences),
            "confidence": confidence,
            "llm_used": llm_used,
            "stopped_at": search_result.get("stopped_at", "L3"),
            "context_summary": {
                "loci_count": len(context.get("loci_entries", [])),
                "gene_count": len(context.get("genes", [])),
                "inference_count": len(inferences),
            },
        }

        self.dialog_history.append({
            "session": self.session_id,
            "query": query,
            "response": llm_response,
            "confidence": confidence,
        })

        return result

    def _build_context(self, query: str, loci_results: List[Dict],
                       genome_results: List[Dict]) -> Dict[str, Any]:
        """Собирает контекст из всех источников."""
        context = {
            "query": query,
            "loci_entries": [],
            "genes": [],
            "inferences": [],
            "symbols": {},
            "working_memory": self.working_memory.get_all(),
        }

        # Без дубликатов
        seen_ids = set()
        for entry in loci_results:
            eid = entry.get("id", entry.get("path", ""))
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                context["loci_entries"].append(entry)

        for gene in genome_results:
            context["genes"].append(gene)

        return context

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Собирает системный промпт с AAAK-контекстом.
        LLM получает дистиллированное представление, а не сырой текст.
        """
        parts = [
            "Ты — исполнитель (executor) когнитивной системы CogniCore Nexus.",
            "Твоя задача — отвечать на запросы пользователя, опираясь на предоставленный контекст.",
            "Используй информацию из контекста для точных и обоснованных ответов.",
            "",
            "=== АКТИВНЫЙ КОНТЕКСТ ===",
        ]

        if context["loci_entries"]:
            parts.append("\n--- Записи пространственной памяти (Локусы) ---")
            for entry in context["loci_entries"][:10]:
                aaak_str = entry.get("aaak", entry.get("summary", ""))
                if isinstance(aaak_str, dict):
                    aaak_str = json.dumps(aaak_str, ensure_ascii=False)
                parts.append(str(aaak_str))

        if context["genes"]:
            parts.append("\n--- Гены (понятия из графа знаний) ---")
            for gene in context["genes"][:10]:
                name = gene.get("id", "unknown")
                aaak = gene.get("aaak_compressed", "")
                parts.append(f"  {name}: {str(aaak)[:200]}")

        if context.get("inferences"):
            parts.append("\n--- Логические выводы ---")
            for inf in context["inferences"][:10]:
                parts.append(f"  {inf}")

        wm = context.get("working_memory", [])
        if wm:
            parts.append(f"\n--- Рабочая память (последние {len(wm)} элементов) ---")
            for item in wm[-5:]:
                role = item.get("role", "?")
                content = item.get("content", "")[:100]
                parts.append(f"  [{role}] {content}")

        parts.append("")
        parts.append("Ответь пользователю, используя контекст выше. Если контекста недостаточно — скажи об этом.")
        parts.append("Формат ответа: обычный текст. Не используй AAAK-кодирование в ответе.")

        return "\n".join(parts)

    def _save_to_memory(self, query: str, response: str, context: Dict[str, Any]):
        """Сохраняет диалог в пространственную память с таймстемпом."""
        now = aaak_timestamp()
        aaak_content = self.codec.encode({
            "type": "EVENT",
            "id": f"dialog_{self.session_id}",
            "time": now,
            "query": query,
            "response": response[:500],
            "confidence": self._compute_confidence(
                context, context.get("inferences", []), self.llm is not None
            ),
        })
        self.palace.add_to_room("room_system", aaak_content)

    def _symbolic_response(self, query: str, context: Dict[str, Any],
                           inferences: List[str]) -> str:
        """Генерация ответа без LLM — только логический вывод и память."""
        lines = ["[Символьный режим — LLM не подключена]"]
        lines.append("")

        if context["loci_entries"]:
            lines.append("Найдено в пространственной памяти:")
            for entry in context["loci_entries"][:5]:
                lines.append(f"  • {entry.get('path', 'запись')}")
                lines.append(f"    {str(entry.get('aaak', entry.get('summary', '')))[:200]}")

        if context["genes"]:
            lines.append("\nРелевантные понятия:")
            for gene in context["genes"][:5]:
                lines.append(f"  • {gene.get('id', '?')}")

        if inferences:
            lines.append("\nЛогические выводы:")
            for inf in inferences[:5]:
                lines.append(f"  → {inf}")

        lines.append("\nДля полноценного ответа настрой подключение LLM в data/config.yaml")
        return "\n".join(lines)

    def _compute_confidence(self, context: Dict[str, Any],
                            inferences: List[str], llm_used: bool) -> float:
        """Вычисляет уверенность ответа на основе полноты контекста."""
        score = 0.3
        if context["loci_entries"]:
            score += 0.15
        if context["genes"]:
            score += 0.15
        if inferences:
            score += 0.1
        if llm_used:
            score += 0.2
        if len(self.working_memory.get_all()) > 3:
            score += 0.1
        return min(score, 1.0)

    # ─── Публичные методы для MCP и CLI ──────────────────────────────

    def add_knowledge(self, data: Dict) -> Dict:
        """Добавить знание в систему."""
        try:
            knowledge_type = data.get("_type", data.get("type", ""))
            if knowledge_type == "gene":
                gene_data = {k: v for k, v in data.items() if k != "_type"}
                gene_id = self.genome.add_gene(gene_data)
                return {"status": "ok", "gene_id": gene_id}

            if knowledge_type == "relation":
                rel_id = self.genome.add_relation(data)
                return {"status": "ok", "relation_id": rel_id}

            if knowledge_type == "fact":
                self.inference_engine.add_fact(
                    data.get("predicate", ""),
                    data.get("subject", ""),
                    data.get("object", ""),
                )
                return {"status": "ok", "fact": f"{data.get('predicate')}({data.get('subject')})"}

            if knowledge_type == "rule":
                self.inference_engine.add_rule(data)
                return {"status": "ok", "rule": data.get("name", "unnamed")}

            return {"status": "error", "message": f"Неизвестный тип знания: {knowledge_type}"}
        except sqlite3.DatabaseError as e:
            logger.error(f"Ошибка БД при add_knowledge: {e}")
            return {"status": "error", "message": f"Ошибка БД: {e}"}
        except Exception as e:
            logger.exception(f"Ошибка в add_knowledge")
            return {"status": "error", "message": str(e)}

    def recall(self, query: str, **kwargs) -> Dict:
        """Извлечь контекст по запросу."""
        try:
            loci_results = self.palace.wake_up(query)
            genome_results = self.genome.find_genes(query)
            return {"loci": loci_results, "genes": genome_results}
        except Exception as e:
            logger.exception(f"Ошибка в recall")
            return {"loci": [], "genes": [], "error": str(e)}

    def list_genes(self, type_filter: Optional[str] = None) -> Dict:
        """Список генов."""
        try:
            genes = self.genome.list_genes(type_filter=type_filter)
            return {"genes": genes, "count": len(genes)}
        except Exception as e:
            logger.exception(f"Ошибка в list_genes")
            return {"genes": [], "count": 0, "error": str(e)}

    def navigate_loci(self, room_id: str) -> Dict:
        """Переместиться по пространственной памяти."""
        try:
            room = self.palace.navigate_to(room_id)
            if room:
                return {"room": room, "status": "ok"}
            return {"status": "error", "message": f"Комната {room_id} не найдена"}
        except Exception as e:
            logger.exception(f"Ошибка в navigate_loci")
            return {"status": "error", "message": str(e)}

    def run_matrix(self, matrix_name: str) -> Dict:
        """Запустить когнитивную матрицу."""
        try:
            matrix = self.procedural_memory.get(matrix_name)
            if not matrix:
                return {"status": "error", "message": f"Матрица '{matrix_name}' не найдена"}
            context = self._build_context(matrix_name, [], [])
            result = self.cognitive_arch.run_matrix(matrix, context, self)
            return {"status": "ok", "matrix": matrix_name, "result": result}
        except Exception as e:
            logger.exception(f"Ошибка в run_matrix")
            return {"status": "error", "message": str(e)}

    def simulate_agent(self, agent_name: str, context: str = "") -> Dict:
        """Запустить Theory of Mind симуляцию."""
        try:
            prediction = self.tom.predict_action(agent_name, context)
            return {"agent": agent_name, "prediction": prediction}
        except Exception as e:
            logger.exception(f"Ошибка в simulate_agent")
            return {"agent": agent_name, "error": str(e)}

    def get_current_context(self) -> Dict:
        """Текущий сводный контекст (для MCP Resource)."""
        try:
            return {
                "working_memory": self.working_memory.get_all(),
                "current_room": getattr(self.palace, "current_room_id", None),
                "active_genes_count": self.genome.count_genes(),
                "session_id": self.session_id,
            }
        except Exception as e:
            logger.exception(f"Ошибка в get_current_context")
            return {"error": str(e)}


# Быстрый тест
if __name__ == "__main__":
    nexus = CogniCoreNexus()
    result = nexus.process_query("Привет! Как дела?")
    print("Ответ:", result.get("answer", "")[:200] if result.get("answer") else "None")
    print("Остановлен на:", result.get("stopped_at", "?"))
    print("\nТрассировка:")
    for t in result.get("trace", []):
        print(f"  {t}")