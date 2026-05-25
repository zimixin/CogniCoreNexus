"""
CLI — интерактивный интерфейс CogniCore Nexus.
Поддерживает команды: /query, /add, /loci, /genes, /matrix, /tom, /help, /exit
"""

import sys
from typing import Any, Dict, Optional

from core.nexus import CogniCoreNexus


class CogniCoreCLI:
    """
    Интерактивный командный интерфейс для работы с CogniCore Nexus.
    """

    def __init__(self, config_path: str = "data/config.yaml"):
        print("=" * 60)
        print("  CogniCore Nexus — Когнитивная архитектура (MCP-сервер)")
        print("=" * 60)
        print()

        print("Инициализация ядра...")
        self.nexus = CogniCoreNexus(config_path)

        llm_status = ("подключена" if self.nexus.llm and self.nexus.llm.model_name
                      else "не подключена (символьный режим)")
        print(f"  LLM: {llm_status}")
        print(f"  Локусов: {len(self.nexus.palace.rooms)}")
        print(f"  Генов: {self.nexus.genome.count_genes()}")
        print(f"  Матриц: {self.nexus.procedural_memory.count()}")
        print()

    def run(self):
        """Главный цикл CLI."""
        print("Команды: /query <текст> | /help | /exit")
        print()

        while True:
            try:
                user_input = input(">>> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nДо встречи!")
                break

            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit", "/q"):
                print("До встречи!")
                break

            elif user_input.startswith("/help "):
                self._show_help(user_input[6:])

            elif user_input == "/help":
                self._show_help()

            elif user_input.startswith("/query "):
                query = user_input[7:].strip()
                if query:
                    self._handle_query(query)

            elif user_input.startswith("/add fact_full "):
                parts = user_input[15:].strip().split()
                if len(parts) >= 3:
                    self.nexus.inference_engine.add_fact(parts[0], parts[1], parts[2])
                    print(f"  Факт добавлен: {parts[0]}({parts[1]}, {parts[2]})")
                else:
                    print("Использование: /add fact_full <предикат> <субъект> <объект>")

            elif user_input.startswith("/add "):
                self._handle_add(user_input[5:].strip())

            elif user_input.startswith("/loci go "):
                room_id = user_input[9:].strip()
                room = self.nexus.palace.navigate_to(room_id)
                if room:
                    print(f"  Перешёл в комнату: {room.get('name', room_id)}")
                else:
                    print(f"  Комната не найдена: {room_id}")

            elif user_input == "/loci":
                self._handle_loci()

            elif user_input.startswith("/genes search "):
                query = user_input[14:].strip()
                if query:
                    genes = self.nexus.genome.find_genes(query)
                    print(f"\nПоиск генов: '{query}' — найдено {len(genes)}")
                    for g in genes[:10]:
                        name = g.get("name", g.get("id", "?"))
                        gtype = g.get("type", "?")
                        conf = g.get("passport", {}).get("confidence", "?")
                        print(f"  • {name} ({gtype}, conf={conf})")
                    if len(genes) > 10:
                        print(f"  ... и ещё {len(genes) - 10}")

            elif user_input == "/genes count":
                print(f"  Всего генов: {self.nexus.genome.count_genes()}")

            elif user_input.startswith("/genes list ") or user_input == "/genes list" or user_input == "/genes":
                self._handle_genes(user_input[12:].strip() if user_input.startswith("/genes list ") else "")

            elif user_input == "/matrix list":
                print("\n--- КОГНИТИВНЫЕ МАТРИЦЫ ---\n")
                for m in self.nexus.procedural_memory.list_matrices():
                    print(f"  • {m['name']}: {m['description']}")

            elif user_input.startswith("/matrix run "):
                matrix_name = user_input[12:].strip()
                self._handle_matrix(matrix_name)

            elif user_input.startswith("/tom agent "):
                agent_name = user_input[11:].strip()
                self._handle_tom(agent_name)

            elif user_input == "/tom agents":
                agents = self.nexus.tom.list_agents()
                if agents:
                    print(f"\nАгенты ToM: {', '.join(agents)}")
                else:
                    print("\nАгенты не зарегистрированы.")

            elif user_input == "/context":
                self._handle_context()

            elif user_input == "/stats":
                print(f"\n--- СТАТИСТИКА COGNICORE NEXUS ---")
                print(f"  Гены: {self.nexus.genome.count_genes()}")
                print(f"  Матрицы: {self.nexus.procedural_memory.count()}")
                print(f"  Комнат: {len(self.nexus.palace.rooms)}")
                print(f"  Фактов: {len(self.nexus.inference_engine.get_facts())}")
                print(f"  Символов: {self.nexus.symbol_manager.count()}")
                print(f"  Агентов ToM: {len(self.nexus.tom.list_agents())}")
                print(f"  Сессий: {self.nexus.session_id}")
                print(f"  Рабочая память: {self.nexus.working_memory.count()}/{self.nexus.working_memory.max_size}")
                print(f"  LLM: {'подключена (' + str(self.nexus.llm) + ')' if self.nexus.llm and self.nexus.llm.model_name and self.nexus.config.get('llm','provider') != 'none' else 'символьный режим'}")

            elif user_input.startswith("/"):
                print(f"Неизвестная команда: {user_input}")
                print("Введите /help для списка команд.")

            else:
                # Любой текст без / — это /query
                self._handle_query(user_input)

    def _show_help(self, topic: str = ""):
        """Показать справку. Поддерживает топики: genes, loci, matrix, tom, add, syntax, all"""
        topic = topic.lower().strip()

        if topic == "genes":
            self._show_help_genes()
        elif topic == "loci":
            self._show_help_loci()
        elif topic == "matrix" or topic == "matrices":
            self._show_help_matrix()
        elif topic == "tom":
            self._show_help_tom()
        elif topic == "add":
            self._show_help_add()
        elif topic in ("syntax", "query"):
            self._show_help_syntax()
        elif topic in ("all", "full", "everything"):
            self._show_help_all()
        else:
            self._show_help_main()

    def _show_help_main(self):
        """Основная справка (краткая)."""
        print()
        print("=" * 60)
        print("  COGNICORE NEXUS — КОМАНДЫ")
        print("=" * 60)
        print()
        print("  /query <текст>       — основной запрос к системе")
        print("  <любой текст>        — то же, что /query")
        print("  /help                — эта справка")
        print("  /help <topic>        — подробно по теме:")
        print("                         genes, loci, matrix, tom, add, syntax")
        print("  /help all            — полная справка")
        print()
        print("  /add fact <p> <o>    — добавить факт predicate(object)")
        print("  /loci                — состояние пространственной памяти")
        print("  /loci go <room>      — перейти в комнату")
        print("  /genes list          — список генов")
        print("  /genes search <q>    — поиск генов")
        print("  /context             — рабочая память")
        print("  /matrix list         — список когнитивных матриц")
        print("  /matrix run <name>   — запустить матрицу")
        print("  /tom agent <name>    — модель агента ToM")
        print("  /tom agents          — список агентов")
        print("  /stats               — статистика системы")
        print("  /exit                — выход")
        print()
        print(f"  Всего генов: {self.nexus.genome.count_genes()} | "
              f"Матриц: {self.nexus.procedural_memory.count()} | "
              f"Комнат: {len(self.nexus.palace.rooms)}")
        print()

    def _show_help_genes(self):
        """Справка по генам (граф знаний)."""
        print()
        print("--- ГЕНЫ (Граф знаний) ---")
        print()
        print("  Гены — это единицы знания в графе знаний (SQLite).")
        print("  Каждый ген имеет: id, name, type, passport, full_text, tags")
        print()
        print("  Типы генов: principle, pattern, fact, model, concept, rule, heuristic")
        print()
        print("  Команды:")
        print("    /genes list                — все гены")
        print("    /genes list <тип>          — только гены типа (person, fact, ...)")
        print("    /genes search <query>      — поиск по тексту")
        print("    /genes count               — количество")
        print()
        print("  Паспорт гена:")
        print("    purpose         — для чего")
        print("    domain          — предметная область")
        print("    confidence      — достоверность (0..1)")
        print("    audience        — целевая аудитория")
        print("    cost            — стоимость применения")
        print("    context_restrictions — ограничения")
        print()
        print(f"  Сейчас: {self.nexus.genome.count_genes()} генов")

    def _show_help_loci(self):
        """Справка по пространственной памяти (Локусы)."""
        print()
        print("--- КОГНИТИВНЫЕ ЛОКУСЫ (Пространственная память) ---")
        print()
        print("  Иерархия: Крылья (Wings) → Комнаты (Rooms) → Ящики (Drawers)")
        print("  Данные хранятся в папках: data/loci/<крыло>/<комната>/")
        print("  Ящики — файлы .aaak с записями в формате AAAK 2.0")
        print()
        print("  Уровни пробуждения (L0-L3):")
        print("    L0: точное совпадение запроса с AAAK-строкой")
        print("    L1: поиск по тегам и именованным полям")
        print("    L2: семантический (ключевые слова)")
        print("    L3: полный обход графа комнат (BFS)")
        print()
        print("  Команды:")
        print("    /loci               — карта всех комнат")
        print("    /loci go <room_id>  — перейти в комнату")
        print("                         (например: wing_general/room_system)")
        print()
        wings = self.nexus.palace.list_wings()
        for w in wings:
            print(f"  Крыло: {w['id']}")
            for r in w['rooms']:
                print(f"    • {r['name']} — {r.get('total_entries', 0)} записей")

    def _show_help_matrix(self):
        """Справка по когнитивным матрицам."""
        print()
        print("--- КОГНИТИВНЫЕ МАТРИЦЫ (Сценарии рассуждений) ---")
        print()
        print("  Матрица — последовательность шагов рассуждений.")
        print("  Каждый шаг: поиск в памяти, вызов правила, LLM, инструмент.")
        print()
        print("  Встроенные матрицы:")
        for m in self.nexus.procedural_memory.list_matrices():
            print(f"    • {m['name']}: {m['description']}")
            print(f"      Триггеры: {', '.join(m['triggers'][:3])} (шагов: {m['steps_count']})")
        print()
        print("  Команды:")
        print("    /matrix list               — список")
        print("    /matrix run <name>          — запустить")
        print("    /matrix run deep_analysis  — глубокий анализ")

    def _show_help_tom(self):
        """Справка по Theory of Mind."""
        print()
        print("--- THEORY OF MIND (Ментальные модели агентов) ---")
        print()
        print("  Ментальное состояние агента:")
        print("    • beliefs    — убеждения (что считает правдой)")
        print("    • knowledge  — знания (что точно знает)")
        print("    • desires    — желания (чего хочет)")
        print("    • intentions — намерения")
        print("    • personality_traits — черты личности")
        print()
        print("  Черты личности: curiosity, conservatism, cooperativeness, assertiveness")
        print()
        print("  Команды:")
        print("    /tom agent <name>    — показать модель агента")
        print("    /tom agents          — список агентов")
        print()
        agents = self.nexus.tom.list_agents()
        if agents:
            print(f"  Зарегистрированные агенты: {', '.join(agents)}")
        else:
            print(f"  Агенты не зарегистрированы. Создаются через ToM API.")
        print()

    def _show_help_add(self):
        """Справка по добавлению знаний."""
        print()
        print("--- ДОБАВЛЕНИЕ ЗНАНИЙ ---")
        print()
        print("  /add fact <предикат> <объект>")
        print("    Добавить факт: predicate(object)")
        print("    Пример: /add fact violates PaymentService SRP")
        print()
        print("  /add fact_full <предикат> <субъект> <объект>")
        print("    Добавить факт с субъектом: predicate(subject, object)")
        print("    Пример: /add fact_full has_component nexus mcp_server")
        print()
        print("  Через MCP: cognicore_add_knowledge")
        print("    {'_type': 'gene', 'id': '...', 'name': '...', ...}")
        print("    {'_type': 'fact', 'predicate': '...', 'subject': '...', 'object': '...'}")
        print("    {'_type': 'rule', ...}")
        print()
        print("  Новые знания сохраняются в:")
        print("    • Геном (SQLite) — для генов")
        print("    • Локусы (.aaak файлы) — для записей")
        print("    • Логический движок (память) — для фактов")

    def _show_help_syntax(self):
        """Справка по синтаксису запросов."""
        print()
        print("--- СИНТАКСИС ЗАПРОСОВ ---")
        print()
        print("  Система обрабатывает запросы через L0-L3 пробуждение:")
        print()
        print("  L0 — Точное совпадение с AAAK-записями в локусах")
        print("  L1 — Поиск по именованным полям AAAK")
        print("  L2 — Семантический поиск (ключевые слова)")
        print("  L3 — BFS по графу комнат")
        print()
        print("  Затем: сбор контекста → логический вывод → LLM (если есть)")
        print()
        print("  Советы:")
        print("  • Используйте ключевые слова из full_text генов")
        print("  • Для поиска по тегам укажите их в запросе")
        print("  • Без LLM — только символьный режим (память + логика)")
        print("  • Для LLM настройте data/config.yaml")
        print()

    def _show_help_all(self):
        """Полная справка."""
        self._show_help_main()
        self._show_help_genes()
        self._show_help_loci()
        self._show_help_matrix()
        self._show_help_tom()
        self._show_help_add()
        self._show_help_syntax()

    def _handle_query(self, query: str):
        """Обработать запрос."""
        print(f"\n[Обработка: {query[:60]}...]\n")
        try:
            result = self.nexus.process_query(query)

            print("--- ОТВЕТ ---")
            print(result["answer"])
            print()

            if result["trace"]:
                print(f"--- ТРАССИРОВКА ({len(result['trace'])} шагов) ---")
                for t in result["trace"][:10]:
                    print(f"  {t}")
                if len(result["trace"]) > 10:
                    print(f"  ... и ещё {len(result['trace']) - 10} шагов")

            print(f"\nУверенность: {result['confidence']:.2f}")
            print(f"LLM: {'да' if result['llm_used'] else 'нет (символьный режим)'}")

        except Exception as e:
            print(f"[Ошибка] {e}")
            import traceback
            traceback.print_exc()

    def _handle_add(self, args: str):
        """Обработать добавление знания."""
        parts = args.split()
        if not parts:
            print("Использование: /add fact <предикат> <объект>")
            return

        cmd = parts[0].lower()

        if cmd == "fact" and len(parts) >= 3:
            predicate = parts[1]
            obj = parts[2]
            result = self.nexus.add_knowledge({
                "type": "fact",
                "predicate": predicate,
                "object": obj,
            })
            print(f"  Факт добавлен: {result}")

        elif cmd == "rule" and len(parts) >= 4:
            # Простой формат: /add rule имя условие1,условие2 -> заключение
            print("  Добавление правил через CLI — в разработке.")
            print("  Используйте /add fact для простых фактов.")

        else:
            print("Неизвестная команда /add.")
            print("Пример: /add fact violates PaymentService SRP")

    def _handle_loci(self):
        """Показать текущее состояние пространственной памяти."""
        print("\n--- ПРОСТРАНСТВЕННАЯ ПАМЯТЬ (Когнитивные Локусы) ---\n")

        wings = self.nexus.palace.list_wings()
        for wing in wings:
            print(f"  Крыло: {wing['id']}")
            for room in wing["rooms"]:
                current = ""
                if f"{wing['id']}/{room['id']}" == self.nexus.palace.current_room_id:
                    current = " ← текущая"
                print(f"    ├─ Комната: {room['name']}{current}")
                print(f"    │  Теги: {', '.join(room.get('tags', []))}")
                print(f"    │  Ящиков: {room.get('drawers_count', 0)}, "
                      f"Записей: {room.get('total_entries', 0)}")
                if room.get("connections"):
                    print(f"    │  Связи: {', '.join(room['connections'])}")
            print()

        print(f"Всего: {len(self.nexus.palace.rooms)} комнат(ы)")

    def _handle_genes(self, type_filter: str = ""):
        """Показать список генов. Если type_filter задан — только гены этого типа."""
        print("\n--- ГРАФ ЗНАНИЙ (Геном) ---\n")
        genes = self.nexus.genome.list_genes(limit=30)
        if not genes:
            print("  Гены не найдены. Добавьте знания через /add или /query.")
            print()
            return

        # Фильтр по типу
        if type_filter:
            genes = [g for g in genes if g.get("type", "") == type_filter]
            if not genes:
                print(f"  Гены типа '{type_filter}' не найдены.\n")
                print(f"  Доступные типы: {set(g.get('type','?') for g in self.nexus.genome.list_genes(limit=50))}\n")
                return

        # Группируем по типам
        by_type: Dict[str, list] = {}
        for gene in genes:
            gtype = gene.get("type", "unknown")
            if gtype not in by_type:
                by_type[gtype] = []
            by_type[gtype].append(gene)

        for gtype, glist in by_type.items():
            print(f"  [{gtype}] ({len(glist)}):")
            for gene in glist[:10]:
                name = gene.get("name", gene.get("id", "?"))
                conf = gene.get("passport", {}).get("confidence", "?")
                print(f"    • {name} (conf={conf})")
            if len(glist) > 10:
                print(f"    ... и ещё {len(glist) - 10}")
            print()

        print(f"Всего: {self.nexus.genome.count_genes()} генов")

    def _handle_matrix(self, matrix_name: str):
        """Запустить когнитивную матрицу."""
        print(f"\n[Запуск матрицы: {matrix_name}]\n")
        result = self.nexus.run_matrix(matrix_name)
        print(f"Статус: {result.get('status', 'unknown')}")
        if "result" in result:
            r = result["result"]
            for step in r.get("steps", []):
                print(f"  Шаг {step['step']}.{step['iteration']}: {step['action']}")
                if "result" in step:
                    res = step["result"]
                    if isinstance(res, dict):
                        for k, v in res.items():
                            print(f"    {k}: {v}")
                if "error" in step:
                    print(f"    Ошибка: {step['error']}")

    def _handle_tom(self, agent_name: str):
        """Показать модель агента ToM."""
        print(f"\n--- THEORY OF MIND: {agent_name} ---\n")
        agent = self.nexus.tom.get_agent(agent_name)
        if not agent:
            print(f"  Агент '{agent_name}' не найден.")
            print("  Зарегистрируйте агента через вызов ToM:")
            print(f"    nexus.tom.register_agent('{agent_name}')")
            print()
            return

        state = agent.to_dict()
        print(f"  Убеждения ({len(state['beliefs'])}):")
        for b in state["beliefs"][:10]:
            print(f"    • {b}")
        print(f"\n  Желания ({len(state['desires'])}):")
        for d in state["desires"][:10]:
            print(f"    • {d}")
        print(f"\n  Черты личности:")
        for trait, val in state["personality_traits"].items():
            bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
            print(f"    {trait}: {bar} {val:.1f}")

        # Прогноз действия
        prediction = self.nexus.tom.predict_action(agent_name)
        print(f"\n  Прогноз действия:")
        print(f"    {prediction['action']} (conf={prediction['confidence']:.2f})")
        print(f"    Причина: {prediction.get('reason', 'N/A')}")
        print()

    def _handle_context(self):
        """Показать текущий контекст."""
        print("\n--- ТЕКУЩИЙ КОНТЕКСТ ---\n")
        ctx = self.nexus.get_current_context()
        print(f"  Сессия: #{ctx['session_id']}")
        print(f"  Текущая комната: {ctx.get('current_room', 'N/A')}")
        print(f"  Активных генов: {ctx['active_genes_count']}")
        print(f"  Рабочая память: {len(ctx['working_memory'])} элементов")
        for item in ctx["working_memory"][-5:]:
            role = item.get("role", "?")
            content = str(item.get("content", ""))[:100]
            print(f"    [{role}] {content}")
        print()