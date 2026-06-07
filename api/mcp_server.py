"""
MCP-сервер для CogniCore Nexus на официальном MCP SDK.

Протокол: Model Context Protocol "2024-11-05".
Транспорт: stdio (primary), HTTP/SSE (опционально).

Использует пакет `mcp` (pip install mcp) вместо ручной JSON-RPC реализации.
Поддерживаемые транспорты:
- stdio (через mcp.server.stdio)
- HTTP/SSE (опционально, через mcp.server.sse + Starlette)
"""

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
)

from core.nexus import CogniCoreNexus

logger = logging.getLogger("cognicore.mcp")


class CogniCoreMCP:
    """
    MCP-сервер CogniCore Nexus на официальном SDK.

    Вся JSON-RPC маршрутизация делегируется пакету mcp.
    """

    def __init__(self, config_path: str = "data/config.yaml"):
        self.nexus = CogniCoreNexus(config_path)
        self.app = Server(
            "cognicore-nexus",
            version="2.0.0",
            instructions="MCP сервер когнитивной архитектуры CogniCore Nexus. Протокол: 2024-11-05. Транспорт: stdio.",
        )
        self._register_handlers()

    def _register_handlers(self):
        """Зарегистрировать инструменты и ресурсы через декораторы MCP SDK."""

        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            """Список всех MCP-инструментов."""
            return [
                Tool(
                    name="cognicore_query",
                    description="Задать вопрос когнитивной системе. Возвращает ответ и трассировку рассуждений.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Запрос пользователя",
                            }
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="cognicore_add_knowledge",
                    description="Добавить знание (факт, ген, правило) в память системы.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["fact", "gene", "rule"],
                                "description": "Тип знания",
                            },
                            "data": {
                                "type": "object",
                                "description": "Данные знания (поля зависят от типа)",
                            },
                        },
                        "required": ["type", "data"],
                    },
                ),
                Tool(
                    name="cognicore_recall",
                    description="Извлечь контекст из памяти по ключевым словам или семантическому запросу.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Поисковый запрос",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Максимум результатов",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="cognicore_list_genes",
                    description="Список доступных генов (понятий) в графе знаний.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "type_filter": {
                                "type": "string",
                                "description": "Фильтр по типу гена (principle, pattern, fact, model)",
                            }
                        },
                    },
                ),
                Tool(
                    name="cognicore_navigate_loci",
                    description="Переместиться по пространственной памяти ('войти в комнату').",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "room_id": {
                                "type": "string",
                                "description": "ID комнаты (например, wing_general/room_general)",
                            }
                        },
                        "required": ["room_id"],
                    },
                ),
                Tool(
                    name="cognicore_run_matrix",
                    description="Выполнить когнитивную матрицу (сценарий мышления).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "matrix_name": {
                                "type": "string",
                                "description": "Имя матрицы (например, deep_analysis, code_review_solid)",
                            }
                        },
                        "required": ["matrix_name"],
                    },
                ),
                Tool(
                    name="cognicore_check_fact",
                    description="Проверить факт на противоречия с существующими знаниями. Возвращает найденные конфликты и рекомендацию.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "subject": {
                                "type": "string",
                                "description": "Субъект факта (например, '2ЭС6')"
                            },
                            "predicate": {
                                "type": "string",
                                "description": "Предикат (например, 'is_a', 'type_of', 'classification')"
                            },
                            "object": {
                                "type": "string",
                                "description": "Объект факта (например, 'электровоз', 'тепловоз')"
                            },
                            "statement": {
                                "type": "string",
                                "description": "Полное утверждение для проверки (альтернатива subject/predicate/object)"
                            }
                        }
                    },
                ),
                Tool(
                    name="cognicore_simulate_agent",
                    description="Запустить Theory of Mind симуляцию для агента.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "Имя агента"
                            },
                            "context": {
                                "type": "string",
                                "description": "Контекст для симуляции"
                            }
                        },
                        "required": ["agent_name"]
                    },
                ),
            ]

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Обработчик вызова инструмента. Диспатчит по имени."""
            handler = {
                "cognicore_query": self._handle_query,
                "cognicore_add_knowledge": self._handle_add_knowledge,
                "cognicore_recall": self._handle_recall,
                "cognicore_list_genes": self._handle_list_genes,
                "cognicore_navigate_loci": self._handle_navigate_loci,
                "cognicore_run_matrix": self._handle_run_matrix,
                "cognicore_check_fact": self._handle_check_fact,
                "cognicore_simulate_agent": self._handle_simulate_agent,
            }.get(name)

            if handler is None:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Инструмент не найден: {name}"}),
                )]

            try:
                result = handler(arguments)
                # Ensure result is valid JSON
                if isinstance(result, list):
                    return result
                return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
            except Exception as e:
                logger.exception("Tool call error")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, ensure_ascii=False),
                )]

        @self.app.list_resources()
        async def list_resources() -> list[Resource]:
            """Список MCP-ресурсов (читаемый контекст)."""
            return [
                Resource(
                    uri="context://current",
                    name="Текущий контекст",
                    description="Текущий сводный контекст (AAAK + гены)",
                    mimeType="application/json",
                ),
                Resource(
                    uri="genome://list",
                    name="Список генов",
                    description="Все гены в графе знаний",
                    mimeType="application/json",
                ),
                Resource(
                    uri="genome://gene/{id}",
                    name="Конкретный ген",
                    description="Информация о гене по ID",
                    mimeType="application/json",
                ),
                Resource(
                    uri="help://commands",
                    name="Справка по командам CLI",
                    description="Все доступные команды CogniCore Nexus CLI",
                    mimeType="text/plain",
                ),
                Resource(
                    uri="help://architecture",
                    name="Архитектура системы",
                    description="Описание компонентов и их взаимодействия",
                    mimeType="text/plain",
                ),
            ]

        @self.app.read_resource()
        async def read_resource(uri: Any) -> list:
            """Чтение MCP-ресурса по URI."""
            from mcp.server.lowlevel.helper_types import ReadResourceContents
            uri_str = str(uri)

            if uri_str == "context://current":
                ctx = self.nexus.get_current_context()
                return [ReadResourceContents(
                    content=json.dumps(ctx, indent=2, ensure_ascii=False),
                    mime_type="application/json",
                )]

            if uri_str == "genome://list":
                genes = self.nexus.genome.list_genes()
                return [ReadResourceContents(
                    content=json.dumps(genes, indent=2, ensure_ascii=False),
                    mime_type="application/json",
                )]

            if uri_str.startswith("genome://gene/"):
                gene_id = uri_str.replace("genome://gene/", "")
                gene = self.nexus.genome.get_gene(gene_id)
                if gene:
                    return [ReadResourceContents(
                        content=json.dumps(gene, indent=2, ensure_ascii=False),
                        mime_type="application/json",
                    )]
                return [ReadResourceContents(
                    content=json.dumps({"error": f"Ген не найден: {gene_id}"}),
                )]

            if uri_str == "help://commands":
                return [ReadResourceContents(content=HELP_COMMANDS)]

            if uri_str == "help://architecture":
                return [ReadResourceContents(content=HELP_ARCHITECTURE)]

            return [ReadResourceContents(
                content=json.dumps({"error": f"Неизвестный URI: {uri_str}"}),
            )]

    # --- Обработчики инструментов ---

    def _handle_query(self, args: dict) -> dict:
        """Обработать запрос к когнитивной системе."""
        query = args.get("query", "")
        if not query:
            return {"error": "Параметр 'query' обязателен"}
        result = self.nexus.process_query(query)
        return result

    def _handle_add_knowledge(self, args: dict) -> dict:
        """Обработать добавление знания."""
        result = self.nexus.add_knowledge(args)
        return result

    def _handle_recall(self, args: dict) -> dict:
        """Обработать извлечение из памяти."""
        query = args.get("query", "")
        max_results = args.get("max_results", 10)
        result = self.nexus.recall(query)
        if isinstance(result, dict):
            for k in ("loci", "genes"):
                if k in result and isinstance(result[k], list):
                    result[k] = result[k][:max_results]
        return result

    def _handle_list_genes(self, args: dict) -> dict:
        """Обработать запрос списка генов."""
        type_filter = args.get("type_filter")
        result = self.nexus.list_genes(type_filter=type_filter)
        return result

    def _handle_navigate_loci(self, args: dict) -> dict:
        """Обработать навигацию по локусам."""
        room_id = args.get("room_id", "")
        result = self.nexus.navigate_loci(room_id)
        return result

    def _handle_run_matrix(self, args: dict) -> dict:
        """Обработать запуск когнитивной матрицы."""
        matrix_name = args.get("matrix_name", "")
        result = self.nexus.run_matrix(matrix_name)
        return result

    def _handle_check_fact(self, args: dict) -> dict:
        """Проверить факт на противоречия с существующими знаниями."""
        subject = args.get("subject", "").strip()
        predicate = args.get("predicate", "").strip()
        object_val = args.get("object", "").strip()
        statement = args.get("statement", "").strip()

        # Build search query
        if statement:
            search_query = statement
        elif subject or object_val:
            parts = [p for p in [subject, predicate, object_val] if p]
            search_query = " ".join(parts)
        else:
            return {"error": "Нужно указать statement ИЛИ subject/predicate/object"}

        # Search for existing knowledge about the subject
        recall_result = self.nexus.recall(search_query)
        genes = recall_result.get("genes", [])
        loci = recall_result.get("loci", [])

        # Analyze for contradictions
        conflicts = []
        supporting = []

        # Known mutually exclusive category pairs
        EXCLUSIVE_CATEGORIES = {
            "электровоз": ["тепловоз", "дизель", "diesel", "паросиловая"],
            "тепловоз": ["электровоз", "электрический", "electric"],
            "diesel": ["электровоз", "electric"],
            "электрический": ["тепловоз", "diesel"],
            "мужчина": ["женщина"],
            "женщина": ["мужчина"],
            "живой": ["мертвый"],
            "правда": ["ложь"],
            "да": ["нет"],
        }

        for gene in genes:
            gene_text = (gene.get("full_text") or gene.get("name") or "").lower()
            gene_conf = gene.get("passport", {}).get("confidence", 0.5)
            gene_tags = gene.get("tags", [])

            # Check if gene mentions the subject
            if subject and subject.lower() in gene_text:
                # Check for classification contradiction
                contradiction_found = False
                
                if object_val:
                    obj_lower = object_val.lower()
                    # Check if gene contains an exclusive category
                    for existing_cat, exclusive_cats in EXCLUSIVE_CATEGORIES.items():
                        if existing_cat in gene_text and obj_lower in exclusive_cats:
                            # Found: gene says "subject is existing_cat" but new says "subject is exclusive_cat"
                            conflicts.append({
                                "existing_gene_id": gene["id"],
                                "existing_text": gene.get("full_text", gene.get("name", "")),
                                "existing_confidence": gene_conf,
                                "existing_category": existing_cat,
                                "new_category": obj_lower,
                                "conflict_type": "classification_mismatch",
                                "description": f"Конфликт классификации: в базе '{subject}' — {existing_cat}, новое утверждение: {obj_lower}",
                                "severity": "high" if gene_conf > 0.8 else "medium"
                            })
                            contradiction_found = True
                            break
                    
                    # Also check if same subject + different classification in gene
                    if not contradiction_found and obj_lower in gene_text:
                        # Same object mentioned - might be same statement
                        pass

                if not contradiction_found:
                    # Related info about subject (supporting)
                    supporting.append({
                        "gene_id": gene["id"],
                        "text": gene.get("full_text", gene.get("name", "")),
                        "confidence": gene_conf,
                        "tags": gene_tags
                    })

        # Also check logical facts in inference engine
        logical_conflicts = []
        if subject and predicate and object_val:
            # Check for opposite predicate
            negated_pred = f"not_{predicate}" if not predicate.startswith("not_") else predicate[4:]
            existing = self.nexus.inference_engine.query(negated_pred, subject, object_val)
            if existing:
                logical_conflicts.append({
                    "type": "logical_contradiction",
                    "fact": f"{negated_pred}({subject}, {object_val})",
                    "description": f"В логическом движке существует противоречащий факт: {negated_pred}({subject}, {object_val})"
                })

        # Build recommendation
        has_high_conflict = any(c.get("severity") == "high" for c in conflicts)
        has_logical = len(logical_conflicts) > 0

        if has_high_conflict or has_logical:
            recommendation = "reject_or_verify"
            message = "Обнаружены противоречия с высокой достоверностью существующих знаний."
        elif conflicts:
            recommendation = "verify"
            message = "Найдены противоречия в классификации, требуется проверка."
        else:
            recommendation = "safe_to_add"
            message = "Прямых противоречий не найдено."

        return {
            "status": "checked",
            "query": search_query,
            "subject": subject,
            "predicate": predicate,
            "object": object_val,
            "recommendation": recommendation,
            "message": message,
            "conflicts": conflicts,
            "logical_conflicts": logical_conflicts,
            "supporting_info": supporting,
            "summary": {
                "total_genes_found": len(genes),
                "total_loci_found": len(loci),
                "conflicts_count": len(conflicts),
                "logical_conflicts_count": len(logical_conflicts),
                "supporting_count": len(supporting)
            }
        }

    def _handle_simulate_agent(self, args: dict) -> dict:
        """Обработать ToM симуляцию."""
        agent_name = args.get("agent_name", "")
        context = args.get("context", "")
        result = self.nexus.tom.predict_action(agent_name, context)
        return result

    # --- Запуск ---

    async def run_stdio(self):
        """Запуск MCP-сервера через stdio.

        Использует официальный MCP stdio транспорт.
        Читает JSON-RPC из stdin, пишет в stdout.
        """
        async with stdio_server() as (read_stream, write_stream):
            await self.app.run(
                read_stream,
                write_stream,
                self.app.create_initialization_options(),
            )

    async def run_http(self, host: str = "0.0.0.0", port: int = 9100):
        """Запуск MCP-сервера через HTTP/SSE.

        Использует Starlette с SSE транспортом.
        """
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        from starlette.responses import JSONResponse
        from mcp.server.sse import SseServerTransport
        import uvicorn

        sse = SseServerTransport("/mcp/messages")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as (read_stream, write_stream):
                await self.app.run(
                    read_stream,
                    write_stream,
                    self.app.create_initialization_options(),
                )

        async def handle_messages(request):
            return await sse.handle_post_message(request.scope, request.receive, request._send)

        async def handle_health(request):
            return JSONResponse({
                "status": "ok",
                "llm": self.nexus.llm.model_name if self.nexus.llm else "none",
                "genes": self.nexus.genome.count_genes(),
                "rooms": len(self.nexus.palace.rooms),
                "matrices": self.nexus.procedural_memory.count(),
            })

        app = Starlette(routes=[
            Route("/mcp/sse", endpoint=handle_sse),
            Route("/mcp/messages", endpoint=handle_messages, methods=["POST"]),
            Route("/health", endpoint=handle_health),
        ])

        print(f"[MCP] HTTP/SSE-сервер запущен на {host}:{port}")
        print(f"[MCP] SSE: http://localhost:{port}/mcp/sse")
        print(f"[MCP] Messages: http://localhost:{port}/mcp/messages POST")
        print(f"[MCP] Здоровье: http://localhost:{port}/health")
        uvicorn.run(app, host=host, port=port, log_level="info")


# --- Статические тексты справки ---

HELP_COMMANDS = """\
CogniCore Nexus CLI — список команд

Основные:
  /query <текст>       — основной запрос к системе
  <любой текст>        — то же, что /query

Пространственная память (Локусы):
  /loci                — карта всех комнат
  /loci go <room_id>   — перейти в комнату

Граф знаний (Геном):
  /genes list          — все гены
  /genes list <type>   — фильтр по типу
  /genes search <q>    — поиск по тексту
  /genes count         — количество генов

Когнитивные матрицы:
  /matrix list         — список матриц
  /matrix run <name>   — запустить матрицу

Theory of Mind:
  /tom agent <name>    — модель агента
  /tom agents          — список агентов

Добавление знаний:
  /add fact <p> <o>    — факт predicate(object)
  /add fact_full <p> <s> <o> — факт predicate(subject, object)

Справка:
  /help                — краткая справка
  /help <topic>        — по теме (genes, loci, matrix, tom, add, syntax)
  /help all            — полная справка
  /context             — рабочая память
  /stats               — статистика системы
  /exit                — выход"""

HELP_ARCHITECTURE = """\
CogniCore Nexus Architecture

Компоненты:

1. Ядро (core/nexus.py)
   - process_query: L0-L3 пробуждение памяти, сбор контекста, логика, LLM
   - L0: точное совпадение, L1: ключи AAAK, L2: семантика, L3: BFS графа

2. AAAK 2.0 (aaak/codec.py)
   - Сверхплотное представление знаний (S-выражения)
   - encode(dict)->str, decode(str)->dict
   - dictionary.yaml для сокращений

3. Пространственная память (memory/loci/)
   - Когнитивные Локусы: Крылья->Комнаты->Ящики
   - BFS-граф связей между комнатами
   - Файлы .aaak с AAAK-записями

4. Граф знаний (memory/genome/)
   - Гены с паспортами (purpose, domain, confidence...)
   - 200+ типов отношений
   - SQLite (data/genome.db)

5. Логический движок (logic/inference_engine.py)
   - Forward chaining с правилами
   - Правила: транзитивность, обнаружение противоречий

6. Когнитивные матрицы (cognition/)
   - Сценарии рассуждений
   - general_inquiry, deep_analysis, code_review_solid

7. Theory of Mind (tom/theory_of_mind.py)
   - MentalState: beliefs, knowledge, desires, intentions
   - predict_action(), simulate_dialog()

8. MCP сервер (api/mcp_server.py)
   - Официальный MCP SDK (mcp.server)
   - 7 инструментов, 5 ресурсов
   - Транспорты: stdio и HTTP/SSE

9. CLI (api/cli.py)
   - Интерактивный режим с командами"""