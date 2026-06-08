<picture>
  <source
    media="(prefers-color-scheme: dark)"
    srcset="https://raw.githubusercontent.com/zimixin/CogniCoreNexus/main/docs/banner-dark.svg"
  />
  <img alt="CogniCore Nexus" src="https://raw.githubusercontent.com/zimixin/CogniCoreNexus/main/docs/banner-light.svg" />
</picture>

# CogniCore Nexus

> **Портативная гибридная когнитивная архитектура.** Модульная система долговременной памяти, графа знаний, логического вывода и Theory of Mind — оформленная как MCP-сервер.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![MCP Protocol](https://img.shields.io/badge/MCP-2024--11--05-purple)](https://modelcontextprotocol.io)
[![Tests](https://img.shields.io/badge/tests-22/22-passing-brightgreen)](_test_all.py)
[![Termux](https://img.shields.io/badge/termux-supported-orange)](https://termux.com)
[![Platform](https://img.shields.io/badge/linux-%20macOS%20-%20Windows%20-%20Android-lightgrey)]()

---

## Философия

Большинство AI-агентов страдают от одной проблемы: **у них нет памяти, отделённой от LLM**. Каждый запрос — чистый лист. Контекстное окно растёт, но не структурируется. Знания не накапливаются. Противоречия не замечаются.

**CogniCore Nexus** решает это через гибридную архитектуру:

| Компонент | Что делает | Хранилище |
|-----------|-----------|-----------|
| **AAAK 2.0** | Сверхплотное кодирование знаний (S-выражения) | `dictionary.yaml` |
| **Loci Memory** | Пространственная память (метод локусов) | `.aaak` файлы |
| **Genome** | Граф знаний (гены + отношения) | SQLite |
| **Inference Engine** | Прямой логический вывод (forward chaining) | Память |
| **Cognitive Matrices** | Сценарии рассуждений (процедурная память) | YAML |
| **Theory of Mind** | Ментальные модели агентов | Память |
| **LLM Interface** | Fallback-цепочка провайдеров | OpenRouter / LM Studio / Ollama |

Ключевой принцип: **LLM — исполнитель, а не мозг**. Мозг — это L0-L3 пробуждение памяти, логический вывод и матрицы рассуждений. LLM получает уже дистиллированный контекст и отвечает на его основе. Если LLM не подключена — система работает в символьном режиме (память + логика, без LLM).

---

## Архитектура

```
                    ┌──────────────────────┐
                    │    CLI / MCP Client   │
                    └──────────┬───────────┘
                               │ query
                    ┌──────────▼───────────┐
                    │   CogniCoreNexus     │
                    │  (core/nexus.py)     │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐
│  L0-L3 Search   │  │  Forward Chain   │  │  LLM (optional)│
│  (Palace+BFS)   │  │  (Inference)     │  │  OpenRouter    │
│                 │  │                  │  │  LM Studio     │
│  L0: exact      │  │  is_a(X,Y)+      │  │  Ollama        │
│  L1: AAAK keys  │  │  is_a(Y,Z)       │  │                │
│  L2: keywords   │  │  → is_a(X,Z)     │  │  fallback      │
│  L3: BFS graph  │  │                  │  │  chain         │
└────────┬────────┘  └────────┬─────────┘  └────────┬───────┘
         │                    │                       │
         ▼                    ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Loci Memory    │  │  Genome (SQLite)  │  │  Working Memory  │
│  (space-based)   │  │  (graph-based)    │  │  (focus-based)   │
│                  │  │                   │  │                  │
│  Wings → Rooms   │  │  genes + relations│  │  deque(maxlen=N) │
│  → Drawers       │  │  + sessions       │  │  + timestamp     │
│  → .aaak files   │  │  + agents         │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Поток запроса

```
query
  │
  ├─ L0: точное совпадение в локусах + поиск генов
  │     если есть → ответ (ранняя остановка)
  │
  ├─ L1: поиск по AAAK-ключам
  │     если уверенность ≥ 0.7 → ответ
  │
  ├─ L2: семантический поиск + гены (find_genes)
  │     если уверенность ≥ 0.7 + vectors включены → ответ
  │
  └─ L3: полный BFS по графу комнат (всегда возвращает)
       │
       ▼
  контекст → логический вывод → когнитивная матрица → LLM → сохранение
```

Система не проходит все 4 уровня каждый раз. Как только на уровне достигается достаточная уверенность, поиск останавливается. L0 теперь ищет **одновременно** локусы и гены — даже при точном совпадении ответ включает контекст из графа знаний.

---

## Установка

### Требования

- Python 3.10+
- SQLite (встроен в Python)
- Желательно: `pip install requests mcp` (для LLM и MCP-сервера)

### Быстрый старт

```bash
git clone https://github.com/zimixin/CogniCoreNexus.git
cd CogniCoreNexus
pip install -r requirements.txt
python3 seed.py
python3 main.py cli
```

### На Android/Termux

```bash
pkg install python git -y
git clone https://github.com/zimixin/CogniCoreNexus.git
cd CogniCoreNexus
pip install -r requirements.txt
# Установка mcp может занять 2-3 минуты (сборка native-зависимостей)
python3 seed.py
python3 main.py cli
```

---

## Использование

### Режимы запуска

```bash
python3 main.py cli          # Интерактивный CLI
python3 main.py mcp          # MCP-сервер (stdio)
python3 main.py mcp-http     # MCP-сервер (HTTP/SSE, порт 9100)
```

### Команды CLI

После запуска `python3 main.py cli` вы попадёте в интерактивную оболочку.

| Команда | Описание | Пример |
|---------|----------|--------|
| `/query <текст>` | Основной запрос к системе | `/query SOLID` |
| `<любой текст>` | То же, что /query | `что такое SOLID?` |
| `/help` | Краткая справка | `/help` |
| `/help <topic>` | Справка по теме | `/help genes` |
| `/help all` | Полная справка | `/help all` |
| `/add fact <p> <o>` | Факт predicate(object) | `/add fact solid oop` |
| `/add fact_full <p> <s> <o>` | Факт с субъектом | `/add fact_full has nexus mcp` |
| `/loci` | Карта пространственной памяти | `/loci` |
| `/loci go <room>` | Перейти в комнату | `/loci go wing_general/room_system` |
| `/genes list` | Все гены | `/genes list` |
| `/genes list <type>` | Фильтр по типу | `/genes list person` |
| `/genes search <q>` | Поиск по тексту | `/genes search SOLID` |
| `/genes count` | Количество | `/genes count` |
| `/context` | Текущая рабочая память | `/context` |
| `/matrix list` | Список матриц | `/matrix list` |
| `/matrix run <name>` | Запустить матрицу | `/matrix run deep_analysis` |
| `/tom agent <name>` | Показать агента ToM | `/tom agent assistant` |
| `/tom agents` | Список агентов | `/tom agents` |
| `/stats` | Статистика системы | `/stats` |
| `/exit` | Выход | `/exit` |

### Пример сессии (символьный режим, без LLM)

```
$ python3 main.py cli

============================================================
  CogniCore Nexus — Когнитивная архитектура (MCP-сервер)
============================================================

Инициализация ядра...
  LLM: не подключена (символьный режим)
  Локусов: 3
  Генов: 10
  Матриц: 3

Команды: /query <текст> | /help | /exit

>>> /query SOLID

Связанные понятия:
  • solid: Пять принципов ООП: SRP, OCP, LSP, ISP, DIP
  • singleton: Гарантирует единственный экземпляр класса
  • factory: Интерфейс создания объектов с выбором класса подклассами
  • project_nexus: Гибридная когнитивная архитектура с MCP-сервером, L0-L3 памятью, графом знаний

>>> /query что такое Singleton?

Связанные понятия:
  • singleton: Гарантирует единственный экземпляр класса

>>> /genes list principle

--- ГРАФ ЗНАНИЙ (Геном) ---

  [principle] (3):
    • SOLID (conf=0.95)
    • KISS (conf=0.85)
    • DRY (conf=0.9)

Всего: 10 генов

>>> /loci

--- ПРОСТРАНСТВЕННАЯ ПАМЯТЬ (Когнитивные Локусы) ---

  Крыло: wing_general
    ├─ Комната: Общая
    │  Теги: general, common
    │  Ящиков: 0, Записей: 0
    ├─ Комната: Система  ← текущая
    │  Теги: system, meta
    │  Ящиков: 1, Записей: 3

Всего: 2 комнат(ы)
```

Вывод чистый и понятный: только ответ без технической трассировки, уверенности и статуса LLM. Внутренние шаги (L0-L3, контекст, матрицы) записываются в лог, но не показываются пользователю.

### С LLM

Если указать `api_key` в `data/config.yaml`, ответы будут формулироваться LLM на основе найденного контекста — более естественным языком, с учётом логических выводов и когнитивных матриц.

### MCP (Model Context Protocol)

```bash
# Запуск MCP-сервера
python3 main.py mcp

# В другом терминале — вызов через mcp_call.py
python3 mcp_call.py tools/list
python3 mcp_call.py tools/call cognicore_query '{"query": "кто я?"}'
python3 mcp_call.py tools/call cognicore_list_genes '{"type_filter": "person"}'
python3 mcp_call.py resources/read context://current
```

**Доступные MCP-инструменты:**

| Инструмент | Описание |
|-----------|----------|
| `cognicore_query(query)` | Задать вопрос когнитивной системе |
| `cognicore_add_knowledge(type, data)` | Добавить знание (ген/факт/правило) |
| `cognicore_recall(query)` | Извлечь контекст из памяти |
| `cognicore_list_genes(type_filter)` | Список генов |
| `cognicore_navigate_loci(room_id)` | Навигация по пространственной памяти |
| `cognicore_run_matrix(matrix_name)` | Запустить когнитивную матрицу |
| `cognicore_check_fact(subject, predicate, object)` | Проверить факт на противоречия |
| `cognicore_simulate_agent(agent_name, context)` | ToM симуляция |

**Подключение к Claude Desktop:**

```json
{
  "mcpServers": {
    "cognicore": {
      "command": "python3",
      "args": ["-m", "main", "mcp"],
      "cwd": "/path/to/CogniCoreNexus"
    }
  }
}
```

---

## Конфигурация

Файл `data/config.yaml`:

```yaml
# LLM (опционально — без LLM работает в символьном режиме)
llm:
  provider: "openai"              # openai | lmstudio | ollama | none
  endpoint: "https://openrouter.ai/api/v1"
  api_key: ""                     # или через OPENROUTER_API_KEY env
  model_name: "deepseek/deepseek-v4-flash"
  temperature: 0.7
  max_tokens: 2048

# Fallback-цепочка провайдеров (если указана — переопределяет llm.provider)
llm_providers:
  - type: "openai"
    endpoint: "https://openrouter.ai/api/v1"
    model: "deepseek/deepseek-v4-flash"
    timeout: 60
  - type: "lmstudio"
    endpoint: "http://localhost:1234/v1"
    model: "local-model"
    timeout: 30
  - type: "ollama"
    endpoint: "http://localhost:11434"
    model: "llama3.2"
    timeout: 60

memory:
  use_vectors: false              # Векторный поиск (опционально)
  vector_backend: "numpy"         # numpy | annoy | faiss | none
  search_threshold: 0.7           # Порог L0-L2 ранней остановки

cognition:
  working_memory_size: 20
  max_inference_steps: 50
  max_planning_depth: 5
```

**Если API-ключ не указан** — система пытается прочитать `OPENROUTER_API_KEY` из переменных окружения. Если и там пусто — работает в **символьном режиме** (память + логика, без LLM).

---

## Модули

### AAAK 2.0 — Сверхплотное кодирование

AAAK — это язык представления знаний на основе S-выражений (Lisp-style). Вместо:

```json
{"type": "VIOLATION", "id": "SRP", "cause": "multi_role", "severity": "high", "confidence": 0.95}
```

Вы пишете:

```lisp
(VIOLATION SRP
  :cause multi_role
  :severity high
  :confidence 0.95)
```

~40% экономии на типизации. Двусторонний словарь (`dictionary.yaml`) отображает короткие коды в полные имена. Ключи вроде `causes`, `contradicts` сжимаются до 3-4 символов.

**Формат поддерживает:**
- S-выражения с именованными полями (`:key value`)
- Вложенность любой глубины
- Списки с явным маркером `LIST`
- Числа, строки, булевы (`true`/`false`), `nil`
- Авто-сокращение ключей через словарь
- Версионирование формата (`_aaak_version`)

### Loci Memory — Пространственная память

Метод локусов (дворец памяти) из античной риторики, адаптированный для машин:

```
Palace → Wings → Rooms → Drawers → .aaak entries

data/loci/
├── wing_general/
│   ├── room_general/    (общая комната)
│   └── room_system/     (системная комната)
│       ├── room.json
│       └── drawer_001.aaak
```

Комнаты связаны в граф — BFS навигация от текущей комнаты. Поиск работает на 4 уровнях (L0-L3), останавливаясь при достаточной уверенности.

### Genome — Граф знаний

SQLite-база с 5 таблицами:

| Таблица | Назначение |
|---------|-----------|
| `genes` | Понятия с паспортом (purpose, domain, confidence) |
| `relations` | Отношения между генами (source → relation_type → target) |
| `loci_index` | Индекс комнат пространственной памяти |
| `sessions` | История запросов |
| `agents` | Состояния ToM-агентов |

Поиск: точное совпадение → ключевые слова → BFS по отношениям.

### Logic — Логический вывод

Forward chaining с рекурсивным backtracking. Стандартные правила:

```python
# Транзитивность is_a
is_a(X, Y) + is_a(Y, Z) → is_a(X, Z)

# Обнаружение противоречий
supports(X, Y) + contradicts(X, Y) → inconsistent(X, Y)

# Применимость решений
solves(X, Y) + has_problem(Z, Y) → applicable(X, Z)
```

### Theory of Mind — Ментальные модели

```python
agent = nexus.tom.register_agent("assistant",
    traits={"curiosity": 0.8, "cooperativeness": 0.9})
agent.add_belief("SOLID — это принципы ООП")
agent.add_desire("помочь пользователю")

prediction = nexus.tom.predict_action("assistant", "спроси про SOLID")
# → {"action": "pursue_помочь пользователю", "confidence": 0.78, ...}
```

### Cognitive Matrices — Сценарии рассуждений

Встроенные матрицы:

| Матрица | Описание | Триггеры |
|---------|----------|----------|
| `general_inquiry` | Общий запрос | ask, query, what, why, how |
| `knowledge_gap` | Заполнение пробелов | dont_know, unknown, gap |
| `code_review_solid` | Проверка SOLID | review_code, solid, refactor |
| `deep_analysis` | Глубокий анализ | analyze, deep, root_cause |
| `tom_simulation` | ToM симуляция | simulate, agent, perspective |

### Proactive Contradiction Detection

Система проверяет новые знания на противоречия ДО сохранения. Три уровня:

1. **Прямое отрицание** — ключевые пары (любит/ненавидит, хочет/не хочет) с object-aware matching
2. **Логические факты** — проверка через inference engine (`is_a` vs `not_is_a`)
3. **Семантический (LLM)** — LLM анализирует кандидаты на тонкие конфликты

При обнаружении конфликта возвращается структура с вариантами резолюции: `reject_new`, `replace_old`, `keep_both`, `merge`, `ask_user`.

---

## Структура проекта

```
cognicore_nexus/
│
├── main.py                 # Точка входа (cli | mcp | mcp-http)
├── seed.py                 # Заполнение начальными данными
├── load_prompt.py          # Загрузка внешнего промпта в память
├── mcp_call.py             # Однострочный MCP-клиент
├── _test_all.py            # 22 теста для всех модулей
├── requirements.txt        # Зависимости
│
├── core/
│   ├── nexus.py            # Ядро: process_query, L0-L3, add_knowledge
│   ├── config.py           # YAML-конфиг с валидацией
│   ├── utils.py            # Единый формат дат (ISO 8601)
│   └── contradiction_detector.py  # Детектор противоречий (3 уровня)
│
├── aaak/
│   ├── codec.py            # Кодек AAAK 2.0 (encode/decode/compress)
│   ├── dictionary.yaml     # Словарь сокращений (~80 записей)
│   └── domain_profiles/    # Доменные профили словаря
│
├── memory/
│   ├── genome/             # Граф знаний (SQLite)
│   │   ├── genome_manager.py  # CRUD гены + отношения + сессии
│   │   ├── gene.py            # Модель Gene + GenePassport
│   │   └── relation.py        # Модель Relation
│   └── loci/               # Пространственная память
│       ├── palace.py       # Дворец: крылья → комнаты → ящики
│       ├── room.py         # Комната с метаданными
│       └── drawer.py       # Ящик (.aaak файл)
│
├── logic/
│   ├── inference_engine.py # Forward chaining
│   └── rules.py            # Стандартные правила
│
├── cognition/
│   ├── cognitive_arch.py   # Когнитивная архитектура (матрицы)
│   ├── working_memory.py   # Рабочая память (deque)
│   └── procedural_memory.py # Процедурная память (YAML-матрицы)
│
├── llm/
│   ├── interface.py        # BaseLLM + LLMRouter + LLMFactory
│   ├── openai_api.py       # OpenAI-совместимые API
│   ├── lmstudio.py         # LM Studio
│   └── ollama.py           # Ollama
│
├── tom/
│   └── theory_of_mind.py   # MentalState + TheoryOfMind
│
├── symbols/
│   └── symbol_manager.py   # Символьное представление
│
├── tools/
│   └── tool_manager.py     # Регистрация и вызов инструментов
│
├── api/
│   ├── cli.py              # Интерактивный CLI
│   └── mcp_server.py       # MCP-сервер (официальный SDK)
│
├── data/
│   ├── config.yaml         # Конфигурация
│   ├── genome.db           # SQLite БД (генерируется)
│   ├── matrices/           # YAML-матрицы рассуждений
│   └── loci/               # AAAK-файлы локусов (генерируется)
│
└── references/             # Документация и референсы
```

---

## Тесты

```bash
python3 _test_all.py
```

Результат: 22 теста, 0 падений.

Тесты чистят genome.db после себя — после прогона не остаётся мусорных генов.

Покрытие:
- AAAK: encode/decode, вложенность, списки, булевы, словарь, повреждённые
- Genome: CRUD, отношения
- Contradiction detector: прямое отрицание, логические, семантические, резолюция, ложно-положительные
- Inference engine: forward chaining
- Working memory: CRUD, поиск, фокус
- Symbol manager: типы, отношения, BFS
- Theory of Mind: регистрация, предсказание, диалог
- Loci (Palace): навигация, поиск L0-L3
- Ядро process_query: полный цикл (символьный режим)
- MCP протокол: in-memory SDK транспорт (8 инструментов)
- Tool Manager: регистрация, вызов
- Config: загрузка, валидация
- Устойчивость: длинные запросы, Unicode, стресс-тест

---

## Разработка

### Добавление новой когнитивной матрицы

Создайте YAML-файл в `data/matrices/`:

```yaml
name: "bug_analysis"
description: "Анализ багов на основе принципов и паттернов"
triggers: ["bug", "issue", "defect", "error"]
steps:
  - action: "find_genes"
    params:
      type: "principle"
      tags: ["oop", "design"]
  - action: "loci_search"
    params:
      level: 3
  - action: "inference"
    params: {}
  - action: "llm_query"
    params:
      template: "Проанализируй баг {query} на основе принципов {genes}"
max_iterations: 2
```

### Добавление нового LLM-провайдера

1. Создайте класс, наследующий `BaseLLM` в `llm/`
2. Реализуйте метод `generate(prompt, system, temperature)`
3. Зарегистрируйте в `LLMFactory.PROVIDERS`

### Добавление нового MCP-инструмента

1. Добавьте `Tool(...)` в `list_tools()` (mcp_server.py)
2. Добавьте хендлер `_handle_*` с возвратом `dict`
3. Зарегистрируйте в `handler`-словаре `call_tool()`

---

## Лицензия

MIT

---

## Благодарности

Вдохновлено:
- Soar / ACT-R когнитивные архитектуры
- Метод локусов (Simonides of Ceos)
- Model Context Protocol (Anthropic)
- SOLID принципы (Robert C. Martin)