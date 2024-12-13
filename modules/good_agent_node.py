# modules/good_agent_node.py
from model import AgentInput, AgentOutput
from ai_analyzer.prompt_manager import AgentPrompts
from datetime import datetime


class GoodAgentNode:
    def __init__(self, llm_client, memory):
        self.llm_client = llm_client
        self.memory = memory

    async def run(self, input: AgentInput) -> AgentOutput:
        prompt = AgentPrompts.get_good_agent_prompt(
            input.topic_text, input.context_info, input.user_context, input.full_code, input.diff
        )
        response = await self.llm_client.analyze_text(prompt)
        report_id = self._store_agent_report(input.agent_type, input.topic_text, input.context_info, response)
        return AgentOutput(
            agent_type=input.agent_type, topic=input.topic_text, report_id=report_id, report_content=response
        )

    def _store_agent_report(self, agent_type: str, topic_text: str, context: str, response: str) -> int:
        topic_id = self.memory.add_topic(datetime.now().isoformat(), topic_text, context)
        return self.memory.add_agent_report(
            date=datetime.now().isoformat(),
            agent_type=agent_type,
            topic_id=topic_id,
            report_content=response,
            summary=f"{topic_text} 관련 {agent_type} 제안",
            code_refs=[],
            raw_topic_text=topic_text,
        )
