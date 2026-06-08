"""Заполнение CogniCore Nexus данными (persistent — всё в genome.db)."""
import sys; sys.path.insert(0, '.')
import logging
logging.disable(logging.CRITICAL)

from core.nexus import CogniCoreNexus
from symbols.symbol_manager import SymbolType

n = CogniCoreNexus('data/config.yaml')

# ===== 1. ФАКТЫ (как гены типа 'fact') =====
facts_data = [
    ("fact_is_a_cognicore", "is_a(CogniCoreNexus, CognitiveArchitecture)", "CogniCore Nexus — это когнитивная архитектура"),
    ("fact_has_genome", "has_part(CogniCoreNexus, Genome)", "CogniCore Nexus содержит граф знаний Genome"),
    ("fact_has_palace", "has_part(CogniCoreNexus, Palace)", "CogniCore Nexus содержит пространственную память Palace"),
    ("fact_has_inference", "has_part(CogniCoreNexus, InferenceEngine)", "CogniCore Nexus содержит движок логического вывода"),
    ("fact_uses_sqlite", "uses(CogniCoreNexus, SQLite)", "Данные хранятся в SQLite"),
    ("fact_communicates_mcp", "communicates_via(CogniCoreNexus, MCP)", "Интеграция через Model Context Protocol"),
    ("fact_has_aaak", "encodes_via(CogniCoreNexus, AAAK)", "Знания кодируются в AAAK-формат"),
    ("fact_has_loci", "stores_in(CogniCoreNexus, Loci)", "Долговременная память в локусах"),
    ("fact_has_tom", "has_part(CogniCoreNexus, TheoryOfMind)", "Модуль Theory of Mind моделирует агентов"),
    ("fact_uses_yaml", "uses(CogniCoreNexus, YAML)", "Конфигурация в YAML-файлах"),
]
for fid, name, desc in facts_data:
    n.genome.add_gene({
        "id": fid, "name": name, "type": "fact",
        "passport": {"purpose": desc, "domain": "architecture", "confidence": 0.95},
        "full_text": desc,
        "tags": ["fact", "architecture"],
    })
print(f"✅ Фактов (как генов): {n.genome.count_genes(type_filter='fact')}")

# ===== 2. СИМВОЛЫ (как гены типа 'symbol') =====
symbols_data = [
    ("sym_cognicore", "cognicore", "Когнитивная архитектура CogniCore Nexus v2.0"),
    ("sym_aaak", "aaak", "Формат суперплотного кодирования AAAK 2.0"),
    ("sym_loci", "loci", "Пространственная память (3 комнаты)"),
    ("sym_genome", "genome", "Граф знаний SQLite (5 таблиц)"),
    ("sym_hermes", "hermes", "AI-ассистент на платформе Hermes Agent"),
    ("sym_user", "user_dmitry", "Пользователь системы — Дмитрий"),
    ("sym_goal_learn", "learn", "Цель: изучить когнитивные архитектуры"),
    ("sym_goal_build", "build", "Цель: разработать кросс-платформенную систему"),
]
for sid, name, desc in symbols_data:
    n.genome.add_gene({
        "id": sid, "name": name, "type": "symbol",
        "passport": {"purpose": desc, "domain": "symbol", "confidence": 0.9},
        "full_text": desc,
        "tags": ["symbol"],
    })
print(f"✅ Символов (как генов): {n.genome.count_genes(type_filter='symbol')}")

# ===== 3. АГЕНТЫ ToM (в genome.agents) =====
agents_data = [
    {
        "name": "hermes_agent",
        "beliefs": [
            "CogniCore Nexus это когнитивная архитектура",
            "Пользователь работает на Android Termux",
            "Нужно помогать с разработкой"
        ],
        "knowledge": [
            "Python модули системы",
            "API всех подсистем",
        ],
        "desires": [
            "помочь заполнить систему данными",
            "тестировать всё оборудование",
        ],
    },
    {
        "name": "system_analyst",
        "beliefs": [
            "Система использует L0-L3 поиск",
            "Данные хранятся в SQLite и файлах",
            "AAAK сжимает контекст для LLM"
        ],
        "knowledge": [
            "Архитектура модульная",
            "Есть fallback-цепочка провайдеров",
        ],
        "desires": [
            "проанализировать структуру данных",
            "найти узкие места",
        ],
    },
    {
        "name": "mentor",
        "beliefs": [
            "Пользователь учится разработке ИИ",
            "Проект на ранней стадии",
            "Важна кросс-платформенность"
        ],
        "knowledge": [
            "Python должен работать везде",
            "Termux ограничивает native-зависимости",
        ],
        "desires": [
            "обучить пользователя архитектуре",
            "предложить roadmap развития",
        ],
    },
]

for agent in agents_data:
    n.genome.save_agent(agent)
print(f"✅ Агентов ToM: {n.genome.count_agents()}")

# ===== 4. ДОП. ГЕНЫ (уже есть 29, добавим ещё) =====
extra_genes = [
    {"id": "concept_mcp", "name": "MCP Protocol", "type": "concept",
     "passport": {"purpose": "Model Context Protocol", "domain": "integration", "confidence": 0.95},
     "full_text": "Model Context Protocol (MCP) — протокол для интеграции LLM с внешними инструментами и источниками данных. Используется CogniCore Nexus для MCP-сервера.",
     "tags": ["protocol", "integration", "mcp"]},
    {"id": "concept_aaak", "name": "AAAK Codec", "type": "concept",
     "passport": {"purpose": "Сверхплотное кодирование знаний", "domain": "representation", "confidence": 0.9},
     "full_text": "AAAK (Automatic Architecture-Aware Knowledge) — формат суперплотного AAAK-кодирования знаний. Сериализует структурированные данные в компактные S-выражения.",
     "tags": ["codec", "compression", "representation"]},
    {"id": "concept_loci", "name": "Loci Memory", "type": "concept",
     "passport": {"purpose": "Пространственная долговременная память", "domain": "memory", "confidence": 0.9},
     "full_text": "Система пространственной памяти на основе метода локусов (дворец памяти). Хранит AAAK-записи в файловой системе: Крылья → Комнаты → Ящики.",
     "tags": ["memory", "spatial", "loci"]},
    {"id": "concept_tom", "name": "Theory of Mind", "type": "concept",
     "passport": {"purpose": "Ментальные модели агентов", "domain": "cognition", "confidence": 0.85},
     "full_text": "Theory of Mind — модуль ментальных моделей. Агенты имеют убеждения, знания, желания, намерения и черты личности. Поддерживает вложенные модели (рекурсия).",
     "tags": ["tom", "cognition", "agents"]},
    {"id": "principle_pure_python", "name": "Zero Native Deps", "type": "principle",
     "passport": {"purpose": "Кросс-платформенная работа без компиляции", "domain": "architecture", "confidence": 0.95},
     "full_text": "Принцип: все зависимости должны быть pure Python. Никаких native-расширений (бинарников). Обеспечивает работу на Android/Termux без chroot.",
     "tags": ["principle", "portability", "android"]},
]
for g in extra_genes:
    n.genome.add_gene(g)
print(f"✅ Генов всего: {n.genome.count_genes()}")

# ===== 5. ЗАПРОСЫ (сессии в genome.sessions) =====
queries = [
    "что такое cognicore nexus",
    "расскажи о памяти loci",
    "как работает AAAK codec",
    "какие агенты ToM есть в системе",
    "что такое символьный менеджер",
    "какие принципы архитектуры",
    "расскажи про MCP протокол",
    "как устроена база genome",
    "какие есть когнитивные матрицы",
    "кто разработчик системы",
]
for q in queries:
    result = n.process_query(q)
    print(f"  [{result['stopped_at']}] {q[:35]}... — conf={result['confidence']:.2f}")
print(f"✅ Сессий: {n.genome.count_sessions()}")

# ===== ИТОГО =====
print()
print("====== ИТОГО (persistent) ======")
print(f"Гены:    {n.genome.count_genes()}")
print(f"Матрицы: {n.procedural_memory.count()}")
print(f"Комнат:  {len(n.palace.rooms)}")
print(f"Факты:   {n.genome.count_genes(type_filter='fact')}")
print(f"Символы: {n.genome.count_genes(type_filter='symbol')}")
print(f"Агенты:  {n.genome.count_agents()}")
print(f"Сессии:  {n.genome.count_sessions()}")