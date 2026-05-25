"""
Tool Manager — регистрация и выполнение внешних инструментов.
Архитектура готова к расширению: вызов API, запуск кода, работа с файлами.
"""

from typing import Any, Callable, Dict, List, Optional


class Tool:
    """Описание и реализация одного инструмента."""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[..., Dict],
        parameters: Optional[Dict] = None,
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters or {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def execute(self, **kwargs) -> Dict:
        """Выполнить инструмент с переданными параметрами."""
        try:
            result = self.handler(**kwargs)
            return {"status": "ok", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def to_mcp_dict(self) -> Dict:
        """Представление инструмента для MCP-протокола."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters,
        }

    def __repr__(self) -> str:
        return f"Tool({self.name})"


class ToolManager:
    """
    Менеджер инструментов. Регистрирует и выполняет внешние действия.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Зарегистрировать встроенные инструменты."""

        def list_tools(**kwargs) -> Dict:
            return {"tools": [t.to_mcp_dict() for t in self._tools.values()]}

        def echo(**kwargs) -> Dict:
            return {"echoed": kwargs.get("message", "")}

        self.register(Tool(
            name="list_tools",
            description="Список доступных инструментов",
            handler=list_tools,
        ))

        self.register(Tool(
            name="echo",
            description="Эхо-тест инструмента",
            handler=echo,
            parameters={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Сообщение для эха"}
                },
                "required": ["message"],
            },
        ))

    def register(self, tool: Tool):
        """Зарегистрировать новый инструмент."""
        self._tools[tool.name] = tool

    def unregister(self, name: str):
        """Удалить инструмент."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[Tool]:
        """Получить инструмент по имени."""
        return self._tools.get(name)

    def execute(self, name: str, **kwargs) -> Dict:
        """Выполнить инструмент по имени."""
        tool = self.get(name)
        if not tool:
            return {"status": "error", "error": f"Инструмент '{name}' не найден"}
        return tool.execute(**kwargs)

    def list_tools(self) -> List[Dict]:
        """Список всех инструментов (в MCP-формате)."""
        return [t.to_mcp_dict() for t in self._tools.values()]

    def count(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"ToolManager({self.count()} tools)"