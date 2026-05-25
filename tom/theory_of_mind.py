"""
Theory of Mind — ментальные модели агентов.
Позволяет моделировать убеждения, знания, желания и прогнозировать действия.
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
import random


@dataclass
class MentalState:
    """
    Ментальное состояние агента.

    Поля:
    - beliefs: что агент считает правдой (id генов или символы)
    - knowledge: что агент точно знает
    - desires: чего агент хочет достичь
    - intentions: намерения агента
    - nested: вложенные модели ("я думаю, что ты думаешь...")
    """
    agent_id: str
    beliefs: Set[str] = field(default_factory=set)
    knowledge: Set[str] = field(default_factory=set)
    desires: Set[str] = field(default_factory=set)
    intentions: Set[str] = field(default_factory=set)
    nested: Dict[str, "MentalState"] = field(default_factory=dict)  # agent -> MentalState
    personality_traits: Dict[str, float] = field(default_factory=lambda: {
        "curiosity": 0.5,
        "conservatism": 0.5,
        "cooperativeness": 0.7,
        "assertiveness": 0.5,
    })

    def add_belief(self, belief: str):
        self.beliefs.add(belief)

    def add_knowledge(self, knowledge: str):
        self.knowledge.add(knowledge)

    def add_desire(self, desire: str):
        self.desires.add(desire)

    def add_intention(self, intention: str):
        self.intentions.add(intention)

    def has_belief(self, belief: str) -> bool:
        return belief in self.beliefs

    def set_nested_model(self, agent_name: str) -> "MentalState":
        """Создать вложенную модель другого агента."""
        if agent_name not in self.nested:
            self.nested[agent_name] = MentalState(agent_id=agent_name)
        return self.nested[agent_name]

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "beliefs": list(self.beliefs),
            "knowledge": list(self.knowledge),
            "desires": list(self.desires),
            "intentions": list(self.intentions),
            "personality_traits": self.personality_traits,
            "nested": {k: v.to_dict() for k, v in self.nested.items()},
        }

    def __repr__(self) -> str:
        return f"MentalState({self.agent_id}, beliefs={len(self.beliefs)}, desires={len(self.desires)})"


class TheoryOfMind:
    """
    Модуль Theory of Mind.
    Управляет ментальными моделями агентов и прогнозирует их действия.
    """

    def __init__(self):
        self.agents: Dict[str, MentalState] = {}

    def register_agent(self, agent_id: str,
                       traits: Optional[Dict[str, float]] = None) -> MentalState:
        """Зарегистрировать нового агента."""
        if agent_id not in self.agents:
            self.agents[agent_id] = MentalState(agent_id=agent_id)
            if traits:
                self.agents[agent_id].personality_traits.update(traits)
        return self.agents[agent_id]

    def get_agent(self, agent_id: str) -> Optional[MentalState]:
        """Получить ментальное состояние агента."""
        return self.agents.get(agent_id)

    def update_belief(self, agent_id: str, belief: str):
        """Обновить убеждение агента."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.add_belief(belief)

    def update_knowledge(self, agent_id: str, knowledge: str):
        """Обновить знание агента."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.add_knowledge(knowledge)

    def predict_action(self, agent_id: str, context: str = "") -> Dict:
        """
        Прогнозировать действие агента на основе его ментального состояния.

        Для MVP — эвристический подход на основе черт личности и желаний.
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return {
                "agent": agent_id,
                "action": "unknown",
                "confidence": 0.0,
                "reason": "Агент не зарегистрирован",
            }

        # Эвристика на основе черт личности
        curiosity = agent.personality_traits.get("curiosity", 0.5)
        conservatism = agent.personality_traits.get("conservatism", 0.5)
        cooperativeness = agent.personality_traits.get("cooperativeness", 0.7)
        assertiveness = agent.personality_traits.get("assertiveness", 0.5)

        possible_actions = []

        # Если есть желания — пытаемся их удовлетворить
        for desire in agent.desires:
            possible_actions.append({
                "action": f"pursue_{desire}",
                "confidence": 0.6 + 0.3 * assertiveness,
                "reason": f"Агент хочет '{desire}'",
            })

        # Если высокая любознательность — исследовать
        if curiosity > 0.7:
            possible_actions.append({
                "action": "explore",
                "confidence": 0.5 + 0.3 * curiosity,
                "reason": "Высокая любознательность",
            })

        # Если высокий консерватизм — сохранять статус-кво
        if conservatism > 0.7:
            possible_actions.append({
                "action": "maintain",
                "confidence": 0.5 + 0.3 * conservatism,
                "reason": "Высокий консерватизм",
            })

        # Если высокая кооперативность — сотрудничать
        if cooperativeness > 0.7:
            possible_actions.append({
                "action": "collaborate",
                "confidence": 0.5 + 0.3 * cooperativeness,
                "reason": "Высокая кооперативность",
            })

        # Действие по умолчанию
        if not possible_actions:
            possible_actions.append({
                "action": "wait",
                "confidence": 0.3,
                "reason": "Нет явных стимулов",
            })

        # Выбираем действие с наибольшей уверенностью
        best_action = max(possible_actions, key=lambda a: a["confidence"])

        return {
            "agent": agent_id,
            "action": best_action["action"],
            "confidence": best_action["confidence"],
            "reason": best_action["reason"],
            "all_possible": possible_actions,
            "mental_state": agent.to_dict(),
        }

    def simulate_dialog(self, agent_a: str, agent_b: str,
                        topic: str, turns: int = 3) -> List[Dict]:
        """
        Симулировать диалог между двумя агентами.
        Для MVP — простая симуляция на основе черт характера.
        """
        dialog = []
        current_speaker = agent_a

        for i in range(turns):
            speaker = self.get_agent(current_speaker)
            listener_name = agent_b if current_speaker == agent_a else agent_a
            listener = self.get_agent(listener_name)

            if not speaker or not listener:
                break

            # Простая эвристика генерации реплики
            cooperativeness = speaker.personality_traits.get("cooperativeness", 0.5)
            curiosity = speaker.personality_traits.get("curiosity", 0.5)

            if cooperativeness > 0.6:
                message = f"Я думаю, что по теме '{topic}' стоит рассмотреть..."
            elif curiosity > 0.6:
                message = f"А что ты знаешь о '{topic}'? Мне интересны детали."
            else:
                message = f"По поводу '{topic}' — моя позиция основана на имеющихся данных."

            dialog.append({
                "turn": i + 1,
                "speaker": current_speaker,
                "message": message,
                "mental_state_snapshot": {
                    "beliefs": list(speaker.beliefs),
                    "desires": list(speaker.desires),
                },
            })

            # Переключаем говорящего
            current_speaker = listener_name

        return dialog

    def list_agents(self) -> List[str]:
        """Список зарегистрированных агентов."""
        return list(self.agents.keys())

    def __repr__(self) -> str:
        return f"TheoryOfMind({len(self.agents)} agents)"