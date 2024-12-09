# modules/new_agent_node.py
from model import AgentInput, AgentOutput
from ai_analyzer.prompt_manager import AgentPrompts
from datetime import datetime
from typing import List


class NewAgentNode:
    def __init__(self, llm_client, memory):
        self.llm_client = llm_client
        self.memory = memory

    async def run(self, input: AgentInput) -> AgentOutput:
        prompt = AgentPrompts.get_new_agent_prompt(
            input.topic_text, input.relevant_code, input.context_info, input.user_context
        )
        response = await self.llm_client.analyze_text(prompt)
        report_id = self._store_agent_report(input.agent_type, input.topic_text, response)
        self._update_concepts_and_habits_in_memory(input.concepts, input.habits, response)

        return AgentOutput(
            agent_type=input.agent_type, topic=input.topic_text, report_id=report_id, report_content=response
        )

    def _store_agent_report(self, agent_type: str, topic_text: str, response: str) -> int:
        topic_id = self.memory.add_topic(datetime.now().isoformat(), topic_text)
        return self.memory.add_agent_report(
            date=datetime.now().isoformat(),
            agent_type=agent_type,
            topic_id=topic_id,
            report_content=response,
            summary=f"{topic_text} 관련 {agent_type} 제안",
            code_refs=[],
            raw_topic_text=topic_text,
        )

    def _update_concepts_and_habits_in_memory(self, concepts: List[str], habits: List[str], response: str):
        for c in concepts:
            if c in response:
                current_diff = self.memory.get_concept_difficulty(c) or "basic"
                new_diff = "intermediate" if current_diff == "basic" else "advanced"
                self.memory.update_concept_difficulty(c, new_diff)

        for h in habits:
            if h in response:
                self.memory.record_habit_occurrence(h)
