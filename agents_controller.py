# agents_controller.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from file_watcher.state_manager import DatabaseManager
from memory.memory_system import MemorySystem
from ai_analyzer.llm_client import LLMClient
from ai_analyzer.prompt_manager import AgentPrompts
from modules.topic_selector import TopicSelector
from modules.concept_habit_analyzer import ConceptHabitAnalyzer
from modules.report_integrator import ReportIntegrator
from modules.bad_agent_node import BadAgentNode
from modules.good_agent_node import GoodAgentNode
from modules.new_agent_node import NewAgentNode

from model import (
    TopicSelectorInput,
    TopicSelectorOutput,
    ConceptHabitAnalyzerInput,
    ConceptHabitAnalyzerOutput,
    ReportIntegratorInput,
    ReportIntegratorOutput,
    AgentInput,
    AgentOutput,
)


class AgentsController:
    def __init__(self, db_path: str):
        self.db_manager = DatabaseManager(db_path)
        self.memory = MemorySystem(db_path=db_path)
        self.llm_client = LLMClient()
        self.prompts = {
            "나쁜놈": AgentPrompts.get_bad_agent_prompt,
            "착한놈": AgentPrompts.get_good_agent_prompt,
            "새로운놈": AgentPrompts.get_new_agent_prompt,
        }

        self.topic_selector = TopicSelector(self.llm_client, self.memory)
        self.concept_habit_analyzer = ConceptHabitAnalyzer(self.llm_client)
        self.report_integrator = ReportIntegrator()

        # 에이전트 노드
        self.bad_agent_node = BadAgentNode(self.llm_client, self.memory)
        self.good_agent_node = GoodAgentNode(self.llm_client, self.memory)
        self.new_agent_node = NewAgentNode(self.llm_client, self.memory)

    async def initialize(self):
        await self.db_manager.initialize()

    async def generate_daily_report(self) -> Optional[str]:
        changes = self.db_manager.get_recent_changes()
        if not changes:
            print("No recent changes to analyze.")
            return None

        recent_topics = self.memory.get_recent_topics(days=3)

        # 토픽 선정
        ts_input = TopicSelectorInput(changes=changes, recent_topics=recent_topics)
        ts_output: TopicSelectorOutput = await self.topic_selector.run(ts_input)
        new_topics = ts_output.selected_topics
        if not new_topics:
            print("No new topics selected, fallback to review mode triggered.")
            return None

        # 개념/습관 추출
        ch_input = ConceptHabitAnalyzerInput(changes=changes)
        ch_output: ConceptHabitAnalyzerOutput = await self.concept_habit_analyzer.run(ch_input)
        concepts, habits = ch_output.concepts, ch_output.habits
        user_context = self._build_user_context(concepts, habits)

        # 에이전트별 보고서 생성 각 노드 호출
        bad_input = AgentInput(
            agent_type="나쁜놈",
            topic_text=new_topics["나쁜놈"]["topic"],
            relevant_code=new_topics["나쁜놈"]["relevant_code"],
            context_info=new_topics["나쁜놈"]["context"],
            user_context=user_context,
            concepts=concepts,
            habits=habits,
        )
        good_input = AgentInput(
            agent_type="착한놈",
            topic_text=new_topics["착한놈"]["topic"],
            relevant_code=new_topics["착한놈"]["relevant_code"],
            context_info=new_topics["착한놈"]["context"],
            user_context=user_context,
            concepts=concepts,
            habits=habits,
        )
        new_input = AgentInput(
            agent_type="새로운놈",
            topic_text=new_topics["새로운놈"]["topic"],
            relevant_code=new_topics["새로운놈"]["relevant_code"],
            context_info=new_topics["새로운놈"]["context"],
            user_context=user_context,
            concepts=concepts,
            habits=habits,
        )

        # 비동기로 세 노드를 호출 (병렬 실행 가능)
        bad_result, good_result, new_result = await self._run_agents_concurrently(bad_input, good_input, new_input)

        # 리포트 통합
        ri_input = ReportIntegratorInput(agent_reports=[bad_result.dict(), good_result.dict(), new_result.dict()])
        ri_output: ReportIntegratorOutput = self.report_integrator.run(ri_input)
        final_report = ri_output.report
        return final_report

    async def _run_agents_concurrently(self, bad_input: AgentInput, good_input: AgentInput, new_input: AgentInput):
        # 비동기적으로 세 에이전트를 호출
        import asyncio

        bad_task = asyncio.create_task(self.bad_agent_node.run(bad_input))
        good_task = asyncio.create_task(self.good_agent_node.run(good_input))
        new_task = asyncio.create_task(self.new_agent_node.run(new_input))

        results = await asyncio.gather(bad_task, good_task, new_task)
        return results[0], results[1], results[2]

    def _build_user_context(self, concepts: List[str], habits: List[str]) -> str:
        concept_str = self._concepts_info_str(concepts)
        habit_str = self._habits_info_str(habits)
        return f"사용자 상태: 개념들: {concept_str}, 습관들: {habit_str}. 이 정보를 참고하여 보고서를 맞춤화."

    def _concepts_info_str(self, concepts: List[str]) -> str:
        infos = []
        for c in concepts:
            diff = self.memory.get_concept_difficulty(c) or "basic"
            if diff == "basic":
                self.memory.update_concept_difficulty(c, "basic")
            infos.append(f"'{c}' 개념({diff})")
        return ", ".join(infos) if infos else "특별한 개념 없음"

    def _habits_info_str(self, habits: List[str]) -> str:
        infos = []
        for h in habits:
            occ = self.memory.get_habit_occurrences(h) or 0
            infos.append(f"'{h}' 습관({occ}회 지적)")
        return ", ".join(infos) if infos else "특별한 습관 없음"
