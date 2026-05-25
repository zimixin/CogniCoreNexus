#!/usr/bin/env python3
"""
MCP Call — однострочный клиент для CogniCore Nexus MCP (официальный SDK).

Вызывает инструмент/ресурс и выводит результат как JSON.

Использование:
  python3 mcp_call.py tools/list
  python3 mcp_call.py tools/call cognicore_query '{"query": "кто я?"}'
  python3 mcp_call.py resources/read context://current
  python3 mcp_call.py tools/call cognicore_list_genes '{"type_filter": "person"}'
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.shared.memory import create_connected_server_and_client_session
from api.mcp_server import CogniCoreMCP


async def run_once(method: str, params: dict) -> dict:
    """Выполнить один MCP запрос и вернуть результат как dict."""
    server = CogniCoreMCP(
        config_path=os.environ.get("COGNICORE_CONFIG", "data/config.yaml")
    )

    async with create_connected_server_and_client_session(server.app) as session:
        if method == "tools/list":
            result = await session.list_tools()
            return {"tools": [t.model_dump(mode="json") for t in result.tools]}

        elif method == "tools/call":
            name = params.get("name", "")
            args = params.get("arguments", {})
            call_result = await session.call_tool(name, args)
            texts = [
                json.loads(c.text) if c.type == "text" else c.text
                for c in call_result.content
            ]
            return {"result": texts[0] if len(texts) == 1 else texts}

        elif method == "resources/list":
            result = await session.list_resources()
            return {
                "resources": [
                    r.model_dump(mode="json", exclude_none=True)
                    for r in result.resources
                ]
            }

        elif method == "resources/read":
            uri = params.get("uri", "")
            result = await session.read_resource(uri)
            contents = []
            for c in result.contents:
                item = {"uri": str(c.uri), "mimeType": c.mimeType, "text": c.text}
                contents.append(item)
            return {"contents": contents}

        else:
            return {"error": f"Неизвестный метод: {method}"}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: mcp_call.py <method> [params]"}))
        sys.exit(1)

    method = sys.argv[1]
    params = {}

    if len(sys.argv) >= 3:
        if method == "tools/call":
            if len(sys.argv) < 4:
                print(json.dumps({"error": "tools/call requires name and arguments"}))
                sys.exit(1)
            params = {
                "name": sys.argv[2],
                "arguments": (
                    json.loads(sys.argv[3])
                    if sys.argv[3].startswith("{")
                    else {"query": sys.argv[3]}
                ),
            }
        elif method == "resources/read":
            params = {"uri": sys.argv[2]}
        else:
            try:
                params = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                params = {"query": sys.argv[2]}

    result = asyncio.run(run_once(method, params))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()