"""
Когнитивная архитектура — управление вниманием, целями, планированием.
Связывает рабочую память, процедурную память и ядро.
"""

from typing import Any, Dict, List, Optional, Tuple
from cognition.working_memory import WorkingMemory
from cognition.procedural_memory import ProceduralMemory


class CognitiveArchitecture:
    """
    Когнитивная архитектура, управляющая циклами восприятие-мышление-действие.

    Компоненты:
    - Рабочая память (WorkingMemory) — текущее состояние
    - Процедурная память (ProceduralMemory) — сценарии рассуждений
    - Планировщик (Planner) — выбор матриц под цели
    """

    def __init__(
        self,
        working_memory: WorkingMemory,
        procedural_memory: ProceduralMemory,
        max_inference_steps: int = 50,
        max_planning_depth: int = 5,
    ):
        self.wm = working_memory
        self.pm = procedural_memory
        self.max_inference_steps = max_inference_steps
        self.max_planning_depth = max_planning_depth
        self.current_goal: Optional[str] = None
        self.current_intention: Optional[str] = None
        self.execution_history: List[Dict] = []

    def select_matrix(self, query: str, context: Dict) -> Optional[Dict]:
        """
        Выбрать когнитивную матрицу на основе запроса и контекста.
        Возвращает матрицу или None.
        """
        # Проверяем, есть ли подходящая матрица
        matrix = self.pm.find_matching(query)
        if matrix:
            return matrix

        # Если ничего не подошло — используем general_inquiry
        general = self.pm.get("general_inquiry")
        return general

    def run_matrix(self, matrix: Dict, context: Dict, nexus: Any) -> Dict:
        """
        Выполнить когнитивную матрицу.
        Каждый шаг выполняется через соответствующую функцию.
        """
        steps = matrix.get("steps", [])
        max_iterations = matrix.get("max_iterations", 1)
        results = []
        status = "completed"

        for iteration in range(max_iterations):
            for step_idx, step in enumerate(steps):
                action = step.get("action", "")
                params = step.get("params", {})

                try:
                    result = self._execute_step(action, params, context, nexus)
                    results.append({
                        "step": step_idx + 1,
                        "iteration": iteration + 1,
                        "action": action,
                        "result": result,
                    })
                except Exception as e:
                    results.append({
                        "step": step_idx + 1,
                        "iteration": iteration + 1,
                        "action": action,
                        "error": str(e),
                    })
                    status = "error"
                    break

            if status == "error":
                break

        # Сохраняем в историю
        self.execution_history.append({
            "matrix": matrix.get("name", "unknown"),
            "results": results,
            "status": status,
        })

        return {"status": status, "steps": results}

    def _execute_step(self, action: str, params: Dict, context: Dict, nexus: Any) -> Any:
        """Выполнить один шаг матрицы."""
        if action == "loci_search":
            query = context.get("query", "")
            level = params.get("level", 2)
            if level == "all":
                results = nexus.palace.wake_up(query, level=3)
            else:
                results = nexus.palace.wake_up(query, level=level)
            return {"found": len(results), "results": results[:5]}

        elif action == "find_genes":
            query = context.get("query", "")
            max_distance = params.get("max_distance", 3)
            type_filter = params.get("type")
            results = nexus.genome.find_genes(query, max_distance=max_distance)
            if type_filter:
                results = [g for g in results if g.get("type") == type_filter]
            return {"found": len(results), "results": results[:5]}

        elif action == "inference":
            inferences = nexus.inference_engine.forward_chain(context)
            return {"new_facts": len(inferences), "inferences": inferences[:10]}

        elif action == "llm_query":
            if nexus.llm is None:
                return {"error": "LLM не подключена"}
            template = params.get("template", "Ответь на запрос: {query}")
            query = context.get("query", "")
            prompt = template.format(query=query, **context)

            response = nexus.llm.generate(
                prompt=prompt,
                system=nexus._build_system_prompt(context),
                temperature=0.7,
            )
            return {"response_length": len(response), "response": response[:500]}

        elif action == "tom_simulate":
            agent_name = params.get("agent_name", "default")
            context_str = context.get("query", "")
            prediction = nexus.tom.predict_action(agent_name, context_str)
            return {"prediction": prediction}

        elif action == "verify":
            check_contradictions = params.get("check_contradictions", False)
            verification = {"valid": True, "issues": []}

            if check_contradictions:
                # Проверяем противоречия
                contradictions = nexus.inference_engine.query("contradicts", "", "")
                if contradictions:
                    verification["issues"].append(
                        f"Найдено {len(contradictions)} противоречий"
                    )

            return verification

        else:
            return {"error": f"Неизвестное действие: {action}"}

    def set_goal(self, goal: str):
        """Установить текущую цель."""
        self.current_goal = goal
        self.wm.set_focus(goal)

    def clear_goal(self):
        """Сбросить цель."""
        self.current_goal = None
        self.wm.set_focus(None)

    def get_history(self) -> List[Dict]:
        """История выполнения матриц."""
        return self.execution_history

    def __repr__(self) -> str:
        return f"CognitiveArchitecture(goal={self.current_goal}, history={len(self.execution_history)})"