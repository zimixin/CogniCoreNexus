# CogniCore Nexus

Гибридная когнитивная архитектура — MCP-сервер с L0-L3 памятью, графом знаний, логикой и Theory of Mind.

## Быстрый старт

```bash
# На Android/Termux:
pkg install python git -y
git clone https://github.com/zimixin/CogniCoreNexus
cd CogniCoreNexus
pip install -r requirements.txt
python3 seed.py                  # заполнить тестовыми данными
python3 main.py cli              # запустить CLI
```

## Команды CLI

| Команда | Описание |
|---|---|
| `/query <текст>` | Основной запрос с L0-L3 поиском |
| `/genes list` | Список всех генов |
| `/genes search <q>` | Поиск по генам |
| `/loci` | Пространственная память |
| `/loci go <room>` | Перейти в комнату |
| `/matrix list` | Когнитивные матрицы |
| `/matrix run <name>` | Запустить матрицу |
| `/help` | Полная справка |

## Структура

```
cognicore_nexus/
├── core/               # Ядро: nexus, config, utils
├── memory/             # Память: genome (SQLite), loci (AAAK), working_memory
├── aaak/               # AAAK суперплотное кодирование
├── logic/              # Логический вывод (forward chaining)
├── cognition/          # Когнитивные матрицы, планировщик
├── llm/                # Провайдеры LLM (OpenAI, LM Studio, Ollama)
├── tom/                # Theory of Mind
├── api/                # CLI + MCP сервер
├── data/               # Конфиг, геном (генерируется)
├── seed.py             # Начальные данные
└── main.py             # Точка входа
```

## LLM настройка

В `data/config.yaml` раскомментируй провайдеров и укажи API-ключ:
- OpenRouter: `endpoint: https://openrouter.ai/api/v1`
- LM Studio: локально на порту 1234
- Ollama: локально на порту 11434

Без LLM система работает в символическом режиме (память + логика).