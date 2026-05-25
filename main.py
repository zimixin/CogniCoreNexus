#!/usr/bin/env python3
"""
CogniCore Nexus — портативная гибридная когнитивная архитектура.
MCP протокол: "2024-11-05". Транспорт: stdio (primary), HTTP/SSE (опционально).

Использование:
    python main.py cli        — интерактивный CLI
    python main.py mcp        — MCP-сервер через stdio (основной транспорт)
    python main.py mcp-http   — MCP-сервер через HTTP/SSE (опционально, порт 9100)
"""

import asyncio
import sys
import os
import shutil
from pathlib import Path

# Добавляем корень проекта в путь
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.config import NexusConfig, Config, PROJECT_ROOT as CFG_ROOT


def bootstrap(config: Config):
    """Инициализация при первом запуске.

    1. Создаёт data/, data/loci/, data/matrices/, data/vectors/
    2. Создаёт и прогоняет _init_db()
    3. Создаёт дефолтные комнаты: "general" и "system" в loci_index
    4. Копирует дефолтный config.yaml если его нет
    5. Выводит в консоль: "CogniCore Nexus инициализирован. Запуск..."
    """
    base = CFG_ROOT / config.get("loci", "data_dir", default="data")
    print(f"[Bootstrap] Базовая директория: {base}")

    # 1. Создаём структуру директорий
    dirs = [
        base / "loci" / "wing_general" / "room_general",
        base / "loci" / "wing_general" / "room_system",
        base / "matrices",
        base / "vectors",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"[Bootstrap] ✓ {d}")

    # 2. Копируем дефолтные матрицы из aaak/ если есть
    src_matrices = CFG_ROOT / "data" / "matrices"
    if src_matrices.exists():
        for yaml_file in src_matrices.glob("*.yaml"):
            dst = base / "matrices" / yaml_file.name
            if not dst.exists():
                shutil.copy2(str(yaml_file), str(dst))
                print(f"[Bootstrap] ✓ матрица скопирована: {yaml_file.name}")

    # 3. Создаём loci_index записи в genome.db
    # (будет сделано при инициализации GenomeManager через nexus)

    # 4. Проверяем config.yaml
    if not config.config_path.exists():
        print(f"[Bootstrap] ⚠ config.yaml не найден, будет создан Config.load()")

    print("[Bootstrap] ✓ CogniCore Nexus инициализирован. Запуск...")


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    # Bootstrap при любом запуске
    cfg = Config(config_path="data/config.yaml")
    bootstrap(cfg)

    if command == "cli":
        from api.cli import CogniCoreCLI
        cli = CogniCoreCLI(config_path="data/config.yaml")
        cli.run()

    elif command == "mcp":
        from api.mcp_server import CogniCoreMCP
        server = CogniCoreMCP(config_path="data/config.yaml")
        await server.run_stdio()

    elif command == "mcp-http":
        from api.mcp_server import CogniCoreMCP
        server = CogniCoreMCP(config_path="data/config.yaml")
        await server.run_http()

    else:
        print(f"Неизвестная команда: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())