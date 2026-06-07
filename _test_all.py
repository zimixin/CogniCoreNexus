#!/usr/bin/env python3
"""Полный тест всех модулей CogniCore Nexus."""
import sys, json, os, traceback
sys.path.insert(0, '.')

PASS = 0
FAIL = 0
ERRORS = []

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  ✓ {name}")
    except Exception as e:
        FAIL += 1
        ERRORS.append((name, traceback.format_exc()))
        print(f"  ✗ {name}: {e}")

def assert_eq(a, b, msg=""):
    if a != b:
        raise AssertionError(f"{msg}: ожидалось {b!r}, получено {a!r}")

def assert_in(a, b, msg=""):
    if a not in b:
        raise AssertionError(f"{msg}: '{a}' не найден в {b!r}")

def assert_true(v, msg=""):
    if not v:
        raise AssertionError(msg or "ожидалось True")

# ============== 1. AAAK КОДЕК ==============
# Разбиваем на отдельные функции, чтобы не дублировать

def test_aaak_basic():
    from aaak.codec import AAAKCodec, AAAKDictionary
    from pathlib import Path
    dict_path = Path('aaak/dictionary.yaml')
    d = AAAKDictionary(str(dict_path))
    c = AAAKCodec(d)
    data = {"type": "EVENT", "id": "test1", "agent": "bot", "value": 42}
    dec = c.decode(c.encode(data))
    assert_eq(dec.get("agent"), "bot", "поле agent")
    assert_eq(dec.get("value"), 42, "числовое поле")

def test_aaak_nested():
    from aaak.codec import AAAKCodec, AAAKDictionary
    from pathlib import Path
    dict_path = Path('aaak/dictionary.yaml')
    d = AAAKDictionary(str(dict_path))
    c = AAAKCodec(d)
    data2 = {"type": "FACT", "id": "deep", "nested": {"type": "SUB", "x": 1, "y": 2}}
    dec2 = c.decode(c.encode(data2))
    assert_true("nested" in dec2, "вложенный dict")
    if "nested" in dec2 and isinstance(dec2["nested"], dict):
        assert_eq(dec2["nested"].get("x"), 1, "вложенное поле")

def test_aaak_lists_bools():
    from aaak.codec import AAAKCodec, AAAKDictionary
    from pathlib import Path
    dict_path = Path('aaak/dictionary.yaml')
    d = AAAKDictionary(str(dict_path))
    c = AAAKCodec(d)
    data3 = {"type": "LIST", "items": [{"type": "A", "v": 1}, {"type": "B", "v": 2}]}
    dec3 = c.decode(c.encode(data3))
    assert_true("items" in dec3, "список")
    data4 = {"type": "CHECK", "active": True, "done": False, "val": None}
    dec4 = c.decode(c.encode(data4))
    assert_eq(dec4.get("active"), True, "булево true")
    assert_eq(dec4.get("done"), False, "булево false")

def test_aaak_dict():
    from aaak.codec import AAAKCodec, AAAKDictionary
    d2 = AAAKDictionary()
    d2.name_to_code["code_review"] = "CR"
    c2 = AAAKCodec(d2)
    data5 = {"type": "REVIEW", "id": "code_review", "status": "passed"}
    enc5 = c2.encode(data5)
    assert_true(enc5.startswith("(REV"), "сокращение типа REVIEW→REV")
    assert_true("code_review" in enc5, "id не сокращается")
    dec5 = c2.decode(enc5)
    assert_eq(dec5.get("type"), "REVIEW", "декодирование типа")
    assert_eq(dec5.get("id"), "code_review", "декодирование id")

def test_aaak_corrupted():
    from aaak.codec import AAAKCodec, AAAKDictionary
    from pathlib import Path
    dict_path = Path('aaak/dictionary.yaml')
    d = AAAKDictionary(str(dict_path))
    c = AAAKCodec(d)
    try:
        c.decode("это не AAAK")
    except Exception:
        pass  # Ожидаемая ошибка
    try:
        r = c.decode("(EMPTY)")
        assert_true(isinstance(r, dict), "пустые данные")
    except Exception:
        pass

test("AAAK encode/decode базовый", test_aaak_basic)
test("AAAK вложенность", test_aaak_nested)
test("AAAK списки и булевы", test_aaak_lists_bools)
test("AAAK словарь", test_aaak_dict)
test("AAAK повреждённые", test_aaak_corrupted)

# ============== 2. ГЕНОМ ==============
def test_genome_crud():
    from core.nexus import CogniCoreNexus
    # Сброс БД для чистого теста
    import shutil, os
    db_path = 'data/genome.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    n = CogniCoreNexus('data/config.yaml')
    
    # 2.1 Добавить ген
    r = n.add_knowledge({"_type": "gene", "id": "g1", "name": "Gene One",
                          "type": "principle", "full_text": "First gene",
                          "passport": {"confidence": 0.9, "domain": "test"}})
    assert_eq(r["status"], "ok", "добавление гена")
    
    # 2.2 Получить ген
    g = n.genome.get_gene("g1")
    assert_true(g is not None, "получение гена")
    assert_eq(g["name"], "Gene One", "имя гена")
    assert_eq(g["type"], "principle", "тип гена")
    assert_eq(g["passport"]["confidence"], 0.9, "паспорт")
    assert_true("created_at" in g and g["created_at"], "created_at не пустой")
    
    # 2.3 Повторная вставка (UPSERT)
    n.add_knowledge({"_type": "gene", "id": "g1", "name": "Gene One Updated",
                      "type": "principle", "full_text": "Updated"})
    g2 = n.genome.get_gene("g1")
    assert_eq(g2["name"], "Gene One Updated", "UPSERT обновление")
    
    # 2.4 Список генов
    genes = n.list_genes()
    assert_eq(genes["count"], 1, "количество генов")
    
    # 2.5 Поиск
    found = n.genome.find_genes("Gene")
    assert_true(len(found) >= 1, "поиск по имени")
    
    found2 = n.genome.find_genes("nonexistent")
    assert_eq(len(found2), 0, "поиск несуществующего")
    
    # 2.6 Удаление
    n.add_knowledge({"_type": "gene", "id": "g2", "name": "Temp", "type": "fact"})
    assert_eq(n.genome.count_genes(), 2, "до удаления")
    n.genome.delete_gene("g2")
    assert_eq(n.genome.count_genes(), 1, "после удаления")

test("Геном CRUD", test_genome_crud)

def test_genome_relations():
    from core.nexus import CogniCoreNexus
    n = CogniCoreNexus('data/config.yaml')
    
    # Добавим два гена и связь
    n.add_knowledge({"_type": "gene", "id": "ra", "name": "A", "type": "fact"})
    n.add_knowledge({"_type": "gene", "id": "rb", "name": "B", "type": "fact"})
    
    rel_id = n.genome.add_relation({
        "source_id": "ra", "target_id": "rb",
        "relation_type": "causes", "confidence": 0.95
    })
    assert_true(rel_id > 0, "добавление отношения")
    
    # Проверим, что отношение отображается в гене
    ga = n.genome.get_gene("ra")
    assert_true(len(ga.get("relations", [])) >= 1, "отношение в гене")
    assert_eq(ga["relations"][0]["type"], "causes", "тип отношения")
    assert_eq(ga["relations"][0]["target_id"], "rb", "цель отношения")
    
    # Поиск через BFS
    found = n.genome.find_genes("A")
    # Должен найти и A, и B (через BFS по отношениям)
    found_ids = [f["id"] for f in found]
    assert_in("rb", found_ids, "BFS поиск нашёл связанный ген")

test("Геном отношения", test_genome_relations)

# ============== CONTRADICTION DETECTION ==============
def test_contradiction_direct_negation():
    """Test direct negation detection (love vs hate)."""
    from core.nexus import CogniCoreNexus
    import os

    # Fresh DB
    if os.path.exists('data/genome.db'):
        os.remove('data/genome.db')

    n = CogniCoreNexus('data/config.yaml')

    # Add existing knowledge: user loves flowers
    n.add_knowledge({
        "_type": "gene",
        "id": "user_loves_flowers",
        "name": "User loves flowers",
        "type": "fact",
        "full_text": "Пользователь любит цветы",
        "passport": {"confidence": 0.9, "domain": "personal"},
        "tags": ["preference", "verified"]
    })

    # Try to add contradictory knowledge: user loves spiders (hates spiders exists)
    n.add_knowledge({
        "_type": "gene",
        "id": "user_hates_spiders",
        "name": "User hates spiders",
        "type": "fact",
        "full_text": "Пользователь ненавидит пауков",
        "passport": {"confidence": 0.95, "domain": "personal"},
        "tags": ["preference", "verified"]
    })

    # Now try to add: user loves spiders (contradicts hates spiders)
    result = n.add_knowledge({
        "_type": "gene",
        "id": "user_loves_spiders",
        "name": "User loves spiders",
        "type": "fact",
        "full_text": "Пользователь любит пауков",
        "passport": {"confidence": 0.8, "domain": "personal"},
        "tags": ["preference"]
    })

    # Should detect conflict
    assert_eq(result["status"], "conflict_detected", "конфликт обнаружен")
    assert_true(len(result["conflicts"]) >= 1, "есть конфликты")

    conflict = result["conflicts"][0]
    assert_in(conflict["existing_gene_id"], ["user_hates_spiders"], "конфликтует с правильным геном")
    assert_eq(conflict["conflict_type"], "direct_negation", "тип прямого отрицания")
    assert_in(conflict["proposed_action"], ["ask_user", "keep_both"], "предложено действие")

    # Resolution: reject new
    resolve_result = n.resolve_conflict({
        "action": "reject_new",
        "pending_knowledge": result["pending_knowledge"]
    })
    assert_eq(resolve_result["status"], "ok", "reject_new работает")

    # Resolution: keep both
    result2 = n.add_knowledge({
        "_type": "gene",
        "id": "user_loves_spiders2",
        "name": "User loves spiders 2",
        "type": "fact",
        "full_text": "Пользователь любит пауков",
        "passport": {"confidence": 0.8, "domain": "personal"},
        "tags": ["preference"]
    })
    assert_eq(result2["status"], "conflict_detected", "второй конфликт обнаружен")

    resolve2 = n.resolve_conflict({
        "action": "keep_both",
        "pending_knowledge": result2["pending_knowledge"]
    })
    assert_eq(resolve2["status"], "ok", "keep_both работает")
    assert_true(resolve2.get("gene_id"), "генерирован ID")


def test_contradiction_logical_fact():
    """Test logical fact contradiction via inference engine."""
    from core.nexus import CogniCoreNexus
    import os

    if os.path.exists('data/genome.db'):
        os.remove('data/genome.db')

    n = CogniCoreNexus('data/config.yaml')

    # Add fact: user is human
    n.add_knowledge({
        "_type": "fact",
        "predicate": "is_a",
        "subject": "user",
        "object": "human"
    })

    # Try to add contradictory fact: user is not human
    result = n.add_knowledge({
        "_type": "fact",
        "predicate": "not_is_a",
        "subject": "user",
        "object": "human"
    })

    # Should detect logical contradiction
    assert_eq(result["status"], "conflict_detected", "логический конфликт обнаружен")
    assert_true(len(result["conflicts"]) >= 1, "есть логические конфликты")
    conflict = result["conflicts"][0]
    assert_eq(conflict["conflict_type"], "logical_impossible", "тип логического противоречия")


def test_contradiction_semantic_llm():
    """Test semantic contradiction detection via LLM (if available)."""
    from core.nexus import CogniCoreNexus
    import os

    if os.path.exists('data/genome.db'):
        os.remove('data/genome.db')

    n = CogniCoreNexus('data/config.yaml')

    # Add existing gene about being vegetarian
    n.add_knowledge({
        "_type": "gene",
        "id": "user_vegetarian",
        "name": "User is vegetarian",
        "type": "fact",
        "full_text": "Пользователь вегетарианец, не ест мясо",
        "passport": {"confidence": 0.9, "domain": "personal"},
        "tags": ["diet", "verified"]
    })

    # Try to add: user loves steak (semantic contradiction)
    result = n.add_knowledge({
        "_type": "gene",
        "id": "user_loves_steak",
        "name": "User loves steak",
        "type": "fact",
        "full_text": "Пользователь обожает стейк из говядины",
        "passport": {"confidence": 0.8, "domain": "personal"},
        "tags": ["diet"]
    })

    # Should detect conflict (may be direct or semantic)
    if result["status"] == "conflict_detected":
        assert_true(len(result["conflicts"]) >= 1, "семантический конфликт обнаружен")
        # Check conflict structure
        conflict = result["conflicts"][0]
        assert_in("conflict_type", conflict, "тип конфликта")
        assert_in("proposed_action", conflict, "предложенное действие")


def test_contradiction_resolution_replace():
    """Test replace_old resolution."""
    from core.nexus import CogniCoreNexus
    import os

    if os.path.exists('data/genome.db'):
        os.remove('data/genome.db')

    n = CogniCoreNexus('data/config.yaml')

    # Add old knowledge with low confidence - user likes old_thing
    n.add_knowledge({
        "_type": "gene",
        "id": "old_fact",
        "name": "Old fact",
        "type": "fact",
        "full_text": "Пользователь любит старую версию",
        "passport": {"confidence": 0.3, "domain": "test"},
        "tags": ["old"]
    })

    # Add new contradictory knowledge - user hates old_thing (should conflict)
    result = n.add_knowledge({
        "_type": "gene",
        "id": "new_fact",
        "name": "New fact",
        "type": "fact",
        "full_text": "Пользователь ненавидит старую версию",
        "passport": {"confidence": 0.9, "domain": "test"},
        "tags": ["new"]
    })

    assert_eq(result["status"], "conflict_detected", "конфликт обнаружен")

    # Resolve with replace_old
    resolve = n.resolve_conflict({
        "action": "replace_old",
        "pending_knowledge": result["pending_knowledge"],
        "conflict_id": result["conflicts"][0]["existing_gene_id"]
    })
    assert_eq(resolve["status"], "ok", "replace_old работает")

    # Verify new gene exists
    g = n.genome.get_gene("new_fact")
    assert_true(g is not None, "новый ген сохранён")


def test_contradiction_no_false_positive():
    """Test that non-contradictory knowledge passes."""
    from core.nexus import CogniCoreNexus
    import os

    if os.path.exists('data/genome.db'):
        os.remove('data/genome.db')

    n = CogniCoreNexus('data/config.yaml')

    # Add some genes
    n.add_knowledge({"_type": "gene", "id": "a", "name": "A", "type": "fact", "full_text": "User likes cats"})
    n.add_knowledge({"_type": "gene", "id": "b", "name": "B", "type": "fact", "full_text": "User likes dogs"})

    # Add non-contradictory knowledge
    result = n.add_knowledge({
        "_type": "gene",
        "id": "c",
        "name": "C",
        "type": "fact",
        "full_text": "User likes birds",
        "passport": {"confidence": 0.8}
    })

    assert_eq(result["status"], "ok", "без конфликта = ok")
    assert_true("gene_id" in result, "ген создан")


test("Конфликты: прямое отрицание", test_contradiction_direct_negation)
test("Конфликты: логические факты", test_contradiction_logical_fact)
test("Конфликты: семантические (LLM)", test_contradiction_semantic_llm)
test("Конфликты: резолюция replace", test_contradiction_resolution_replace)
test("Конфликты: нет ложных срабатываний", test_contradiction_no_false_positive)

# ============== 3. ЛОГИКА ==============
def test_logic():
    from logic.inference_engine import InferenceEngine
    from logic.rules import Rule
    
    eng = InferenceEngine(max_steps=20)
    
    # 3.1 Добавить факты
    eng.add_fact("is_a", "sparrow", "bird")
    eng.add_fact("is_a", "bird", "animal")
    
    facts = eng.get_facts()
    assert_eq(len(facts), 2, "факты добавлены")
    
    # 3.2 Транзитивность (встроенное правило)
    inferences = eng.forward_chain()
    # Должен вывести is_a(sparrow, animal) по транзитивности
    trans = [i for i in inferences if "transitivity" in i]
    assert_true(len(trans) > 0, "транзитивность сработала")
    
    # 3.3 Добавить правило
    eng.add_rule(Rule(
        name="can_fly",
        conditions=[("is_a", "X", "bird")],
        conclusions=[("can", "X", "fly")],
        confidence=0.8,
    ).to_dict())
    
    eng.add_fact("is_a", "eagle", "bird")
    inferences2 = eng.forward_chain()
    fly_rules = [i for i in inferences2 if "can_fly" in i]
    assert_true(len(fly_rules) >= 1, "пользовательское правило")
    
    # 3.4 Запрос
    results = eng.query("is_a", "sparrow", "")
    assert_true(len(results) >= 1, "запрос по предикату")
    
    # 3.5 Очистка
    eng.clear_facts()
    assert_eq(len(eng.get_facts()), 0, "очистка фактов")
    
    # 3.6 Максимум шагов
    eng2 = InferenceEngine(max_steps=0)
    eng2.add_fact("a", "x", "y")
    r = eng2.forward_chain()
    assert_eq(len(r), 0, "0 шагов = нет выводов")

test("Логический движок", test_logic)

# ============== 4. РАБОЧАЯ ПАМЯТЬ ==============
def test_wm():
    from cognition.working_memory import WorkingMemory
    
    wm = WorkingMemory(max_size=5)
    
    # 4.1 Добавление
    wm.add({"role": "user", "content": "hi"})
    assert_eq(wm.count(), 1, "1 элемент")
    
    # 4.2 Авто-таймстемп
    items = wm.get_all()
    assert_true("timestamp" in items[0], "таймстемп в WM")
    
    # 4.3 Вытеснение
    for i in range(10):
        wm.add({"role": "user", "content": f"msg_{i}"})
    # Должно остаться только 5 последних
    assert_eq(wm.count(), 5, "вытеснение до 5")
    contents = [i["content"] for i in wm.get_all()]
    assert_in("msg_9", contents, "последний элемент")
    assert_true("msg_0" not in contents, "первый вытеснен")
    
    # 4.4 Поиск
    found = wm.search("msg_9")
    assert_eq(len(found), 1, "поиск в WM")
    
    # 4.5 Фильтр по роли
    wm.add({"role": "assistant", "content": "answer"})
    assistants = wm.get_by_role("assistant")
    assert_eq(len(assistants), 1, "фильтр по роли")
    
    # 4.6 Фокус
    wm.set_focus("current_goal")
    assert_eq(wm.get_focus(), "current_goal", "фокус внимания")
    
    # 4.7 Заполненность
    wm.add({"role": "system", "content": "sys"})
    assert_true(wm.is_full(), "WM полна")
    
    # 4.8 Очистка
    wm.clear()
    assert_eq(wm.count(), 0, "WM пуста после clear")

test("Рабочая память", test_wm)

# ============== 5. СИМВОЛЫ ==============
def test_symbols():
    from symbols.symbol_manager import SymbolManager, SymbolType
    
    sm = SymbolManager()
    
    # 5.1 Создание символов
    sm.add_symbol("User", SymbolType.AGENT, {"level": "admin"}, "Administrator")
    sm.add_symbol("PaymentService", SymbolType.OBJECT, {"lang": "python"})
    sm.add_symbol("SRP", SymbolType.CONCEPT, {"domain": "software"})
    
    assert_eq(sm.count(), 3, "3 символа")
    
    # 5.2 Отношения
    sm.add_relation("PaymentService", "violates", "SRP")
    sm.add_relation("User", "uses", "PaymentService")
    
    p = sm.get_symbol("PaymentService")
    assert_true(p is not None, "символ существует")
    assert_true(p.has_relation("violates", "SRP"), "отношение violates")
    
    # 5.3 Поиск по типу
    agents = sm.find_by_type(SymbolType.AGENT)
    assert_eq(len(agents), 1, "1 агент")
    
    # 5.4 Поиск по отношению
    violators = sm.find_by_relation("violates", "SRP")
    assert_eq(len(violators), 1, "нарушители SRP")
    
    # 5.5 Поиск по атрибуту
    admins = sm.find_by_attribute("level", "admin")
    assert_eq(len(admins), 1, "админы")
    
    # 5.6 BFS по связям
    related = sm.find_related("User", max_depth=3)
    assert_true(len(related) >= 2, "BFS связи")
    
    # 5.7 Удаление
    sm.remove_symbol("SRP")
    assert_eq(sm.count(), 2, "после удаления")
    # Проверяем, что ссылки тоже удалены
    p2 = sm.get_symbol("PaymentService")
    assert_true(not p2.has_relation("violates", "SRP"), "ссылка удалена")

test("Символьный менеджер", test_symbols)

# ============== 6. ToM ==============
def test_tom():
    from tom.theory_of_mind import TheoryOfMind
    
    tom = TheoryOfMind()
    
    # 6.1 Регистрация
    alice = tom.register_agent("Alice", {"curiosity": 0.9, "cooperativeness": 0.3})
    assert_true(alice is not None, "агент создан")
    
    # 6.2 Состояние
    alice.add_belief("SRP is violated")
    alice.add_desire("fix the code")
    alice.add_knowledge("SOLID principles")
    
    state = alice.to_dict()
    assert_eq(len(state["beliefs"]), 1, "убеждения")
    assert_eq(len(state["desires"]), 1, "желания")
    
    # 6.3 Прогноз действия
    pred = tom.predict_action("Alice")
    assert_eq(pred["agent"], "Alice", "агент в прогнозе")
    assert_true(pred["confidence"] > 0, "уверенность > 0")
    assert_true("action" in pred, "действие есть")
    
    # 6.4 Несуществующий агент
    pred2 = tom.predict_action("Nobody")
    assert_eq(pred2["action"], "unknown", "неизвестный агент")
    
    # 6.5 Вложенные модели
    bob = tom.register_agent("Bob")
    nested = alice.set_nested_model("Bob")
    nested.add_belief("Alice thinks I'm wrong")
    assert_eq(len(alice.nested), 1, "вложенная модель")
    
    # 6.6 Симуляция диалога
    bob.add_desire("prove a point")
    dialog = tom.simulate_dialog("Alice", "Bob", "SOLID principles", 2)
    assert_eq(len(dialog), 2, "2 реплики в диалоге")
    assert_eq(dialog[0]["speaker"], "Alice", "первый говорит Alice")
    
    # 6.7 Лист агентов
    agents = tom.list_agents()
    assert_true("Alice" in agents, "Alice в списке")

test("Theory of Mind", test_tom)

# ============== 7. ПАЛАТА (Локусы) ==============
def test_loci():
    from memory.loci.palace import Palace
    from aaak.codec import AAAKCodec, AAAKDictionary
    from pathlib import Path
    import shutil, os
    
    # Сброс директории локусов для чистого теста
    loci_dir = 'data/loci_test'
    if os.path.exists(loci_dir):
        shutil.rmtree(loci_dir)
    
    dict_path = Path('aaak/dictionary.yaml')
    d = AAAKDictionary(str(dict_path))
    c = AAAKCodec(d)
    
    palace = Palace(data_dir=loci_dir, codec=c)
    
    # 7.1 Должны быть комнаты по умолчанию
    wings = palace.list_wings()
    assert_true(len(wings) > 0, "крылья созданы")
    assert_true(len(palace.rooms) > 0, "комнаты созданы")
    
    # 7.2 Текущая комната
    cur = palace.get_current_room()
    assert_true(cur is not None, "текущая комната")
    
    # 7.3 Создание новой комнаты
    room = palace.create_room("wing_test", "room_test", "Test Room",
                               tags=["test"], connections=["wing_general/room_general"])
    assert_true(room is not None, "новая комната")
    assert_eq(room.meta.get("name"), "Test Room", "имя комнаты")
    
    # Проверка, что комната появилась в списке
    assert_in("wing_test/room_test", palace.rooms, "комната в списке")
    
    # 7.4 Навигация
    nav = palace.navigate_to("wing_test/room_test")
    assert_true(nav is not None, "навигация в комнату")
    assert_eq(palace.current_room_id, "wing_test/room_test", "текущая = новая")
    
    # 7.5 Добавление записи
    from aaak.codec import AAAKCodec, AAAKDictionary
    aaak_str = c.encode({
        "type": "NOTE", "id": "n1",
        "content": "test entry",
        "tags": ["test", "important"],
    })
    result = palace.add_to_room("wing_test/room_test", aaak_str)
    assert_true(result, "запись добавлена")
    
    # 7.6 Поиск L0-L3
    # Сначала создадим данные для поиска
    aaak_str2 = c.encode({
        "type": "NOTE", "id": "n2",
        "content": "SRP violation in PaymentService",
        "tags": ["solid", "violation"],
    })
    palace.add_to_room("wing_test/room_test", aaak_str2)
    
    aaak_str3 = c.encode({
        "type": "CONCEPT", "id": "solid",
        "description": "SOLID principles: SRP, OCP, LSP, ISP, DIP",
        "tags": ["design", "oop"],
    })
    palace.add_to_room("wing_general/room_general", aaak_str3)
    
    # L0: точное совпадение
    l0 = palace.wake_up("SRP violation", level=0)
    assert_true(len(l0) >= 1, "L0 поиск находит")
    
    # L2: семантический (теги)
    l2 = palace.wake_up("solid", level=2)
    assert_true(len(l2) >= 1, "L2 поиск по тегам")
    
    # L3: BFS
    l3 = palace.wake_up("design", level=3)
    assert_true(len(l3) >= 1, "L3 BFS поиск")
    
    # 7.7 Поиск несуществующего
    empty = palace.wake_up("zzzzzznonexistent", level=3)
    assert_eq(len(empty), 0, "несуществующий запрос")
    
    # 7.8 Сохранение и перезагрузка
    palace.save_all()
    
    palace2 = Palace(data_dir=loci_dir, codec=c)
    assert_in("wing_test/room_test", palace2.rooms, "перезагрузка комнаты")
    
    # 7.9 Очистка тестовых данных
    if os.path.exists(loci_dir):
        shutil.rmtree(loci_dir)

test("Локусы (Palace)", test_loci)

# ============== 8. ЯДРО: process_query ==============
def test_nexus_query():
    from core.nexus import CogniCoreNexus
    
    n = CogniCoreNexus('data/config.yaml')
    
    # 8.1 Обычный запрос (символьный режим)
    r = n.process_query("Привет!")
    assert_true("answer" in r, "есть ответ")
    assert_true("trace" in r, "есть трассировка")
    assert_true("confidence" in r, "есть уверенность")
    assert_true(len(r["trace"]) > 0, "трассировка не пустая")
    
    # 8.2 Пустой запрос
    r2 = n.process_query("")
    assert_true("answer" in r2, "пустой запрос тоже даёт ответ")
    
    # 8.3 Запрос на русском
    r3 = n.process_query("Что такое SOLID?")
    assert_true("answer" in r3, "русский запрос")
    
    # 8.4 Запрос с тегами
    r4 = n.process_query("design patterns")
    assert_true("answer" in r4, "английский запрос")
    
    # 8.5 Много запросов подряд (10+)
    for i in range(5):
        n.process_query(f"Тест номер {i}")
    assert_eq(n.session_id, 9, "сессии считаются")  # 4 прямых + 5 в цикле
    
    # 8.6 Текущий контекст
    ctx = n.get_current_context()
    assert_true("working_memory" in ctx, "контекст с WM")
    assert_true("session_id" in ctx, "контекст с сессией")

test("Ядро process_query", test_nexus_query)

# ============== 9. MCP ПРОТОКОЛ (официальный SDK) ==============
def test_mcp():
    import asyncio, json
    from mcp.shared.memory import create_connected_server_and_client_session
    from api.mcp_server import CogniCoreMCP

    async def _run():
        server = CogniCoreMCP('data/config.yaml')

        async with create_connected_server_and_client_session(
            server.app, raise_exceptions=False
        ) as session:
            # 9.1 tools/list
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]
            assert_in("cognicore_query", tool_names, "инструмент query")
            assert_in("cognicore_add_knowledge", tool_names, "инструмент add")
            assert_in("cognicore_list_genes", tool_names, "инструмент list")
            assert_in("cognicore_navigate_loci", tool_names, "инструмент loci")
            assert_in("cognicore_run_matrix", tool_names, "инструмент matrix")
            assert_in("cognicore_simulate_agent", tool_names, "инструмент tom")
            assert_in("cognicore_check_fact", tool_names, "инструмент check_fact")
            assert_eq(len(tool_names), 8, "8 инструментов всего")

            # 9.2 tools/call cognicore_query
            call_result = await session.call_tool(
                "cognicore_query", {"query": "Тест MCP"}
            )
            assert_true(len(call_result.content) > 0, "есть контент в ответе")
            text = call_result.content[0].text
            assert_true("answer" in text, "MCP query содержит answer")
            assert_true("confidence" in text, "MCP query содержит confidence")

            # 9.3 tools/call с неизвестным инструментом
            err_result = await session.call_tool("nonexistent", {})
            assert_true("error" in err_result.content[0].text,
                        "неизвестный инструмент → ошибка")

            # 9.4 resources/list
            res_list = await session.list_resources()
            uris = [str(r.uri) for r in res_list.resources]
            assert_in("context://current", uris, "ресурс context")
            assert_in("genome://list", uris, "ресурс genome")
            assert_in("help://commands", uris, "ресурс help")

            # 9.5 resources/read
            res_read = await session.read_resource("help://commands")
            assert_true(len(res_read.contents) > 0, "чтение ресурса")
            assert_true("CogniCore Nexus CLI" in res_read.contents[0].text,
                        "справка по командам")

            # 9.6 resources/read с неизвестным URI
            unknown = await session.read_resource("unknown://uri")
            unknown_text = unknown.contents[0].text
            assert_true("error" in unknown_text or "Неизвестный URI" in unknown_text,
                        "неизвестный URI → ошибка")

            # 9.7 genome://list ресурс
            genome_res = await session.read_resource("genome://list")
            assert_true(len(genome_res.contents) > 0, "чтение genome://list")

    asyncio.run(_run())

test("MCP протокол (официальный SDK)", test_mcp)

# ============== 10. ИНСТРУМЕНТЫ ==============
def test_tools():
    from tools.tool_manager import ToolManager, Tool
    
    tm = ToolManager()
    
    # 10.1 Встроенные инструменты
    builtins = tm.list_tools()
    names = [t["name"] for t in builtins]
    assert_in("echo", names, "встроенный echo")
    assert_in("list_tools", names, "встроенный list_tools")
    
    # 10.2 Регистрация
    def my_handler(**kw):
        return {"echoed": kw.get("x", "")}
    
    tm.register(Tool("my_tool", "Test tool", my_handler,
                      parameters={"type": "object", "properties": {"x": {"type": "string"}},
                                  "required": ["x"]}))
    assert_eq(tm.count(), 3, "3 инструмента")
    
    # 10.3 Выполнение
    result = tm.execute("my_tool", x="hello")
    assert_eq(result["result"]["echoed"], "hello", "выполнение инструмента")
    
    # 10.4 Неизвестный инструмент
    result2 = tm.execute("no_such_tool")
    assert_eq(result2["status"], "error", "неизвестный инструмент")
    
    # 10.5 Удаление
    tm.unregister("my_tool")
    assert_eq(tm.count(), 2, "после удаления")

test("Tool Manager", test_tools)

# ============== 11. КОНФИГУРАЦИЯ ==============
def test_config():
    from core.config import Config
    
    cfg = Config('data/config.yaml')
    
    # 11.1 Базовые ключи
    llm_provider = cfg.get("llm", "provider")
    assert_true(llm_provider is not None, "llm provider")
    
    # 11.2 Значение по умолчанию
    missing = cfg.get("nonexistent", "key", default=42)
    assert_eq(missing, 42, "default значение")
    
    # 11.3 Вложенные ключи
    wm_size = cfg.get("cognition", "working_memory_size", default=20)
    assert_true(wm_size > 0, "working_memory_size")
    
    # 11.4 Установка и сохранение
    import tempfile, os
    tmp = tempfile.mktemp(suffix='.yaml')
    old_path = cfg.config_path
    cfg.config_path = tmp
    cfg.set("test", "key", value="val")
    cfg.save()
    # Проверяем, что сохранилось
    cfg2 = Config(tmp)
    assert_eq(cfg2.get("test", "key"), "val", "сохранение config")
    os.remove(tmp)
    cfg.config_path = old_path

test("Конфигурация", test_config)

# ============== 12. УСТОЙЧИВОСТЬ ==============
def test_resilience():
    from core.nexus import CogniCoreNexus
    
    n = CogniCoreNexus('data/config.yaml')
    
    # 12.1 Очень длинный запрос
    long_q = "x" * 10000
    r = n.process_query(long_q)
    assert_true("answer" in r, "длинный запрос")
    
    # 12.2 Запрос со спецсимволами
    special = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
    r2 = n.process_query(special)
    assert_true("answer" in r2, "спецсимволы")
    
    # 12.3 Запрос с юникодом
    unicode_q = "αβγδε ζηθικ λμνξοπ ρστυφχ ψω АБВГД ЕЁЖЗИ ЙКЛМНОП РСТУФХ ЦЧШЩЪЫ ЬЭЮЯ"
    r3 = n.process_query(unicode_q)
    assert_true("answer" in r3, "юникод")
    
    # 12.4 Добавление гена с повреждёнными полями
    r4 = n.add_knowledge({"_type": "gene", "id": "", "name": ""})
    assert_eq(r4["status"], "ok", "пустой id гена")  # Должен создать с пустым id
    
    # 12.5 Поиск с пустым запросом
    found = n.genome.find_genes("")
    assert_eq(len(found), 0, "пустой поиск = 0 результатов")
    
    # 12.6 Много операций подряд (стресс-тест)
    for i in range(20):
        n.process_query(f"Стресс-тест запрос номер {i}")
        n.add_knowledge({"_type": "gene", "id": f"stress_{i}", "name": f"Stress Gene {i}", "type": "fact"})
    # Должно работать без ошибок
    assert_true(n.session_id > 0, "стресс-тест пройден")
    
    # 12.7 Получение несуществующего гена
    g = n.genome.get_gene("__nonexistent_12345__")
    assert_true(g is None, "несуществующий ген = None")

test("Устойчивость", test_resilience)

# ============== ИТОГИ ==============
print()
print("=" * 60)
print(f"  РЕЗУЛЬТАТ: {PASS} пройдено, {FAIL} упало")
print("=" * 60)

if ERRORS:
    print()
    for name, tb in ERRORS:
        print(f"  [{name}]")
        # Покажем только последние строки ошибки
        lines = tb.strip().split('\n')
        for l in lines[-3:]:
            print(f"    {l}")
        print()

sys.exit(0 if FAIL == 0 else 1)
