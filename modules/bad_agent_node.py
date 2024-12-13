# modules/bad_agent_node.py
from model import AgentInput, AgentOutput
from ai_analyzer.prompt_manager import AgentPrompts
from datetime import datetime
from ai_analyzer.llm_manager import LLMManager
from config.settings import Config


class BadAgentNode:
    def __init__(self, memory, model=Config.DEFAULT_LLM_MODEL):
        self.llm = LLMManager(model=model)
        self.memory = memory

    async def run(self, input: AgentInput) -> AgentOutput:
        print(f"[INFO] BadAgentNode run: {input.topic_text}")
        system_prompt, user_prompt = AgentPrompts.get_bad_agent_prompts(
            topic_text=input.topic_text,
            context_info=input.context_info,
            user_context=input.user_context,
            full_code=input.full_code,
            diff=input.diff,
            feedback=input.feedback,
            missing_points=input.missing_points,
            current_report=input.current_report,
        )
        response = await self.llm.agenerate(prompt=user_prompt, system_prompt=system_prompt, temperature=0.4)
        report_id = self._store_agent_report(input.agent_type, input.topic_text, input.context_info, response)
        print(f"[INFO] BadAgentNode completed: {report_id}")
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
