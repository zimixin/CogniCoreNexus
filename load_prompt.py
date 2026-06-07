#!/usr/bin/env python3
"""
Загружает полный промпт-спецификацию CogniCore Nexus в систему.
Создаёт гены для ключевых концептов и сохраняет весь текст в локусы.
"""
import sys
sys.path.insert(0, '.')

from core.nexus import CogniCoreNexus

nexus = CogniCoreNexus('data/config.yaml')

# Читаем промпт из файла
prompt_path = 'data/original_prompt.txt'
with open(prompt_path, 'r', encoding='utf-8') as f:
    prompt_text = f.read()

print(f"Промпт загружен: {len(prompt_text)} символов")
print()

# 1. Сохраняем полный текст промпта в локусы (в комнату Система)
print("=== Сохраняю промпт в пространственную память (Локусы) ===")
from aaak.codec import AAAKCodec, AAAKDictionary
from pathlib import Path
dict_path = Path('aaak/dictionary.yaml')
aaak_dict = AAAKDictionary(str(dict_path))
codec = AAAKCodec(aaak_dict)

compressed = codec.encode({
    "type": "PROMPT",
    "id": "cognicore_spec_v1",
    "title": "Полная спецификация CogniCore Nexus",
    "description": "Архитектура когнитивной системы: MCP-сервер, AAAK, Локусы, Геном, ToM",
    "length": len(prompt_text),
    "sections": [
        "architecture", "mcp_protocol", "loci_memory", "genome",
        "aaak_codec", "cognitive_matrices", "theory_of_mind",
        "llm_integration", "tools", "cli", "cross_platform"
    ]
})
nexus.palace.add_to_room("wing_general/room_system", compressed)
print(f"  AAAK-запись добавлена в Системную комнату")

# Сохраняем verbatim-текст рядом
verbatim_path = Path('data/loci/wing_general/room_system/verbatim_prompt_v1.txt')
verbatim_path.write_text(prompt_text, encoding='utf-8')
print(f"  Полный текст сохранён: {verbatim_path}")

# 2. Создаём гены для ключевых концептов из промпта
print()
print("=== Создаю гены для ключевых концептов ===")

genes = [
    {
        "type": "principle",
        "id": "cognicore_architecture",
        "name": "CogniCore Nexus Architecture",
        "passport": {
            "purpose": "Портативная гибридная когнитивная архитектура как MCP-сервер",
            "domain": "cognitive_architecture",
            "confidence": 0.98,
            "audience": "AI engineers",
            "cost": 0.5,
            "context_restrictions": "Python 3.10+, SQLite"
        },
        "full_text": "CogniCore Nexus — рефлексивный когнитивный двигатель. Отделяет долговременную память от LLM. Рабочая память + Когнитивные Локусы + Геном (граф знаний). Трёхслойная память с L0-L3 пробуждением. Совместимость с MCP протоколом.",
        "tags": ["architecture", "cognitive", "mcp", "memory", "genome"],
    },
    {
        "type": "principle",
        "id": "aaak_compression",
        "name": "AAAK 2.0 Superdense Representation",
        "passport": {
            "purpose": "Сверхплотное представление знаний через S-выражения",
            "domain": "knowledge_representation",
            "confidence": 0.95,
        },
        "full_text": "AAAK 2.0 — язык сверхплотного представления. Синтаксис: S-выражения с именованными полями (:field value). Кодек: encode(dict)->str, decode(str)->dict. Доменный словарь для замены частых терминов на короткие коды. Авто-генерация сокращений.",
        "tags": ["aaak", "codec", "compression", "s-expression"],
    },
    {
        "type": "principle",
        "id": "loci_memory_system",
        "name": "Cognitive Loci (Loci Memory) — Spatial Memory",
        "passport": {
            "purpose": "Пространственная память по методу локусов: Крылья→Комнаты→Ящики",
            "domain": "memory_architecture",
            "confidence": 0.97,
        },
        "full_text": "Когнитивные Локусы — пространственная память. Иерархия: Крылья (Wings) → Комнаты (Rooms) → Ящики (Drawers). Физически: папки в data/loci/. Каждый Ящик — файл .aaak. Навигация: BFS-граф связей между комнатами. L0-L3 стек пробуждения: точное совпадение, теги, семантика, полный обход.",
        "tags": ["loci", "spatial_memory", "rooms", "drawers", "bfs"],
    },
    {
        "type": "principle",
        "id": "genome_knowledge_graph",
        "name": "Genome — Knowledge Graph (Genes + Relations)",
        "passport": {
            "purpose": "Граф знаний в SQLite: гены с паспортами и 200+ типов отношений",
            "domain": "knowledge_graph",
            "confidence": 0.96,
        },
        "full_text": "Геном — граф знаний в SQLite (data/genome.db). Таблицы: genes (id, type, passport JSON, aaak_compressed, full_text, provenance), relations (source, target, relation_type, confidence). Поиск по имени, типу, ключевым словам. 200+ типов отношений: causes, contradicts, solves, is_a, depends_on.",
        "tags": ["genome", "sqlite", "knowledge_graph", "relations", "genes"],
    },
    {
        "type": "principle",
        "id": "mcp_server_protocol",
        "name": "MCP Server (Model Context Protocol)",
        "passport": {
            "purpose": "Совместимость с Model Context Protocol через JSON-RPC 2.0",
            "domain": "protocol",
            "confidence": 0.98,
        },
        "full_text": "MCP-сервер: JSON-RPC 2.0, транспорт stdio + HTTP (FastAPI). Методы: tools/list, tools/call, resources/list, resources/read. Инструменты: cognicore_query, cognicore_add_knowledge, cognicore_recall, cognicore_list_genes, cognicore_navigate_loci, cognicore_run_matrix, cognicore_simulate_agent. Ресурсы: context://current, genome://gene/{id}, loci://room/{room_id}.",
        "tags": ["mcp", "json-rpc", "server", "protocol", "tools", "resources"],
    },
    {
        "type": "principle",
        "id": "cognitive_matrices",
        "name": "Cognitive Matrices (Procedural Memory)",
        "passport": {
            "purpose": "Сценарии рассуждений: последовательность шагов-намерений",
            "domain": "cognitive_architecture",
            "confidence": 0.92,
        },
        "full_text": "Когнитивные матрицы — сценарии рассуждений. Каждый шаг: поиск в памяти, вызов правила, запрос к LLM, вызов инструмента. Примеры: general_inquiry, knowledge_gap, code_review_solid, deep_analysis, tom_simulation. Планировщик выбирает матрицу по цели.",
        "tags": ["matrices", "procedural_memory", "planning", "reasoning"],
    },
    {
        "type": "principle",
        "id": "theory_of_mind_module",
        "name": "Theory of Mind — Agent Modeling",
        "passport": {
            "purpose": "Ментальные модели агентов: убеждения, желания, вложенность",
            "domain": "cognitive_modeling",
            "confidence": 0.88,
        },
        "full_text": "ToM модуль: MentalState (beliefs, knowledge, desires, intentions, personality_traits). Вложенные модели ('я думаю, что ты думаешь...'). predict_action(): эвристика на основе черт личности. simulate_dialog(): симуляция диалога между агентами.",
        "tags": ["theory_of_mind", "agents", "modeling", "simulation", "beliefs"],
    },
    {
        "type": "principle",
        "id": "cross_platform_design",
        "name": "Cross-Platform Design (Termux/Linux/Windows/iOS)",
        "passport": {
            "purpose": "Кроссплатформенность без тяжёлых зависимостей",
            "domain": "engineering",
            "confidence": 0.95,
        },
        "full_text": "Единственное требование: Python 3.10+. SQLite — встроен. Файловая система — для AAAK. Векторный поиск — опционален (numpy/annoy). Зависимости: PyYAML, requests, numpy (опц.), fastapi (опц.). Никаких ChromaDB, Weaviate, Pinecone. Работает на Termux (Android).",
        "tags": ["cross-platform", "termux", "android", "minimal", "dependencies"],
    },
]

for gene_data in genes:
    result = nexus.add_knowledge({"_type": "gene", **gene_data})
    print(f"  + {gene_data['id']}: {result['status']}")

# 3. Добавляем отношения между концептами
print()
print("=== Добавляю связи между концептами ===")
relations = [
    ("cognicore_architecture", "loci_memory_system", "contains"),
    ("cognicore_architecture", "genome_knowledge_graph", "contains"),
    ("cognicore_architecture", "aaak_compression", "uses"),
    ("cognicore_architecture", "mcp_server_protocol", "implements"),
    ("cognicore_architecture", "cognitive_matrices", "contains"),
    ("cognicore_architecture", "theory_of_mind_module", "contains"),
    ("loci_memory_system", "aaak_compression", "uses"),
    ("genome_knowledge_graph", "aaak_compression", "uses"),
    ("cognicore_architecture", "cross_platform_design", "satisfies"),
    ("cognitive_matrices", "theory_of_mind_module", "uses"),
    ("mcp_server_protocol", "cognitive_matrices", "exposes"),
]

for src, tgt, rel in relations:
    nexus.genome.add_relation({
        "source_id": src,
        "target_id": tgt,
        "relation_type": rel,
        "confidence": 0.9,
    })
    print(f"  {src} --[{rel}]--> {tgt}")

# 4. Добавляем факты в логический движок
print()
print("=== Добавляю логические факты ===")
facts = [
    ("has_component", "cognicore_nexus", "mcp_server"),
    ("has_component", "cognicore_nexus", "aaak_codec"),
    ("has_component", "cognicore_nexus", "loci_memory"),
    ("has_component", "cognicore_nexus", "genome"),
    ("has_component", "cognicore_nexus", "cognitive_arch"),
    ("has_component", "cognicore_nexus", "tom"),
    ("has_component", "cognicore_nexus", "llm_interface"),
    ("has_layer", "memory", "working_memory"),
    ("has_layer", "memory", "loci_memory"),
    ("has_layer", "memory", "genome"),
    ("implements", "mcp_server", "tools_list"),
    ("implements", "mcp_server", "tools_call"),
    ("implements", "mcp_server", "resources_list"),
    ("implements", "mcp_server", "resources_read"),
    ("supports", "cross_platform", "linux"),
    ("supports", "cross_platform", "windows"),
    ("supports", "cross_platform", "termux"),
    ("supports", "cross_platform", "ios"),
]

for pred, subj, obj in facts:
    nexus.inference_engine.add_fact(pred, subj, obj)
    print(f"  {pred}({subj}, {obj})")

# 5. Выполняем логический вывод
print()
print("=== Логический вывод ===")
inferences = nexus.inference_engine.forward_chain()
for i in inferences:
    print(f"  → {i}")

print()
print("========================================")
print("Промпт загружен в систему!")
print(f"  Генов создано: {len(genes)}")
print(f"  Связей: {len(relations)}")
print(f"  Фактов: {len(facts)}")
print(f"  Локусов: {len(nexus.palace.rooms)} комнат")
print(f"  Выводов: {len(inferences)}")
print(f"  Verbatim: data/loci/wing_general/room_system/verbatim_prompt_v1.txt")
print("========================================")