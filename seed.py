#!/usr/bin/env python3
"""Seed CogniCore Nexus with initial knowledge graph.

Run ONCE after cloning the repo:
    cd ~/cognicore_nexus && pip install -r requirements.txt && python3 seed.py

This populates genome.db with principles, patterns, facts about the user,
relations between them, and AAAK entries in spatial memory (loci).
No API key needed — runs in symbolic mode.
"""
import sys
sys.path.insert(0, '.')

from core.nexus import CogniCoreNexus

n = CogniCoreNexus('data/config.yaml')

print("Загрузка генов...")

genes = [
    # --- Принципы ---
    {"id": "solid", "name": "SOLID", "type": "principle",
     "passport": {"purpose": "Принципы ООП", "domain": "programming", "confidence": 0.95},
     "full_text": "Пять принципов ООП: SRP, OCP, LSP, ISP, DIP",
     "tags": ["oop", "design", "architecture"]},
    {"id": "dry", "name": "DRY", "type": "principle",
     "passport": {"purpose": "Don't Repeat Yourself", "domain": "programming", "confidence": 0.9},
     "full_text": "Каждая часть знания должна иметь единственное представление",
     "tags": ["design", "best-practice"]},
    {"id": "kiss", "name": "KISS", "type": "principle",
     "passport": {"purpose": "Keep It Simple, Stupid", "domain": "design", "confidence": 0.85},
     "full_text": "Простота — ключ к надёжности",
     "tags": ["design", "simplicity"]},
    # --- Паттерны ---
    {"id": "singleton", "name": "Singleton", "type": "pattern",
     "passport": {"purpose": "Одиночка", "domain": "programming", "confidence": 0.9},
     "full_text": "Гарантирует единственный экземпляр класса",
     "tags": ["pattern", "creational"]},
    {"id": "factory", "name": "Factory Method", "type": "pattern",
     "passport": {"purpose": "Фабричный метод", "domain": "programming", "confidence": 0.85},
     "full_text": "Интерфейс создания объектов с выбором класса подклассами",
     "tags": ["pattern", "creational"]},
    {"id": "observer", "name": "Observer", "type": "pattern",
     "passport": {"purpose": "Наблюдатель", "domain": "programming", "confidence": 0.85},
     "full_text": "Механизм подписки для уведомления объектов об изменениях",
     "tags": ["pattern", "behavioral"]},
    # --- Пользователь (generic) ---
    {"id": "user_generic", "name": "User", "type": "person",
     "passport": {"purpose": "System user", "domain": "personal", "confidence": 0.99},
     "full_text": "System user. Android/Termux development hobbyist. Pure Python without native dependencies.",
     "tags": ["user", "personal"]},
    {"id": "hobby_dev", "name": "Development hobby", "type": "fact",
     "passport": {"purpose": "Hobby", "domain": "personal", "confidence": 0.9},
     "full_text": "Android/Termux development. Pure Python without native dependencies.",
     "tags": ["hobby", "development"]},
    {"id": "tool_hermes", "name": "Hermes Agent", "type": "fact",
     "passport": {"purpose": "Инструмент", "domain": "development", "confidence": 0.95},
     "full_text": "CLI AI-агент для Android/Termux",
     "tags": ["tool", "ai", "cli"]},
    {"id": "project_nexus", "name": "CogniCore Nexus", "type": "fact",
     "passport": {"purpose": "Проект", "domain": "development", "confidence": 0.95},
     "full_text": "Гибридная когнитивная архитектура с MCP-сервером, L0-L3 памятью, графом знаний",
     "tags": ["project", "architecture", "ai"]},
]
for g in genes:
    n.genome.add_gene(g)
print(f"  ✓ {len(genes)} генов")

print("Загрузка отношений...")
relations = [
    ("solid", "is_a", "principle"),
    ("dry", "is_a", "principle"),
    ("singleton", "related_to", "solid"),
    ("factory", "related_to", "solid"),
    ("user_generic", "uses", "tool_hermes"),
    ("user_generic", "creates", "project_nexus"),
    ("project_nexus", "uses", "solid"),
    ("project_nexus", "uses", "dry"),
    ("dry", "conflicts_with", "kiss"),
]
for subj, rel, obj in relations:
    n.genome.add_relation({
        "source_id": subj, "target_id": obj,
        "relation_type": rel, "confidence": 0.85,
        "description": f"{subj} {rel} {obj}"
    })
print(f"  ✓ {len(relations)} отношений")

print("Загрузка локусов...")
entries = [
    "CogniCore Nexus v2.0 — стабильная версия от 2026-05-25",
    "LLM chain: OpenRouter -> LM Studio -> Ollama (fallback)",
    "БД: SQLite (5 таблиц: genes, relations, loci_index, sessions, agents)",
]
for i, content in enumerate(entries):
    aaak = n.codec.encode({
        "id": f"seed_entry_{i}",
        "type": "loci_memo",
        "content": content,
        "tags": ["seed"],
        "time": "2026-05-25T08:00:00+0000"
    })
    n.palace.add_to_room("wing_general/room_system", aaak)
print(f"  ✓ {len(entries)} записей в локусах")

print()
print(f"Итого: {n.genome.count_genes()} генов, {len(n.palace.rooms)} комнат")
print("Готово. Запускай: python3 main.py cli")
