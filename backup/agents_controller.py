# agents_controller.py
from typing import Optional, List, 
from file_watcher.state_manager import DatabaseManager
from memory.memory_system import MemorySystem
from ai_analyzer.llm_client import LLMClient
from ai_analyzer.prompt_manager import AgentPrompts
from modules.topic_selector import TopicSelector
from backup.habit_analyzer import HabitAnalyzer
from modules.report_integrator import ReportIntegrator
from modules.bad_agent_node import BadAgentNode
from modules.good_agent_node import GoodAgentNode
from modules.new_agent_node import NewAgentNode

from model import (
    TopicSelectorInput,
    TopicSelectorOutput,
    HabitAnalyzerInput,
    HabitAnalyzerOutput,
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
            "개선 에이전트": AgentPrompts.get_bad_agent_prompt,
            "칭찬 에이전트": AgentPrompts.get_good_agent_prompt,
            "발견 에이전트": AgentPrompts.get_new_agent_prompt,
        }

        self.topic_selector = TopicSelector(self.llm_client, self.memory)
        self.habit_analyzer = HabitAnalyzer(self.llm_client)
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

        # full_code와 diff를 하나로 합침
        combined_full_code = "\n\n".join(ch["full_content"] for ch in changes)
        combined_diff = "\n\n".join(ch["diff"] for ch in changes)

        recent_topics = self.memory.get_recent_topics(days=3)

        # 토픽 선정
        ts_input = TopicSelectorInput(changes=changes, recent_topics=recent_topics)
        ts_output: TopicSelectorOutput = await self.topic_selector.run(ts_input)
        new_topics = ts_output.selected_topics
        if not new_topics:
            print("No new topics selected, fallback to review mode triggered.")
            return None

        # 개념/습관 추출
        ch_input = HabitAnalyzerInput(changes=changes)
        ch_output: HabitAnalyzerOutput = await self.habit_analyzer.run(ch_input)
        habits = ch_output.habits
        user_context = self._build_user_context(habits)

        def fetch_previous_suggestions(topic: str) -> str:
            similar_reports = self.memory.find_similar_reports(topic, top_k=2)
            if not similar_reports:
                return ""
            suggestions = []
            for rep in similar_reports:
                md = rep["metadata"]
                date_str = md.get("date", "이전 날짜 미상")
                raw_topic = md.get("raw_topic_text", "")
                summary = md.get("summary", "")

                report_id = md.get("report_id")
                if report_id:
                    report_data = self.memory.get_report_by_id(report_id)
                    report_content = report_data.get("report_content", "")
                    code_refs = report_data.get("code_references", [])

                    code_section = ""
                    if code_refs:
                        code_section = "\n  관련 코드 참조:\n" + "\n".join(f"    {cr}" for cr in code_refs)
                    else:
                        code_section = "\n  과거 보고서 내용 내 코드:\n" + report_content

                    suggestions.append(
                        f"- 과거 보고서 날짜: {date_str}\n  주제: {raw_topic}\n  요약: {summary}{code_section}"
                    )
                else:
                    suggestions.append(f"- 과거 보고서 날짜: {date_str}\n  주제: {raw_topic}\n  요약: {summary}")

            return "\n".join(suggestions)

        bad_prev = fetch_previous_suggestions(new_topics["개선 에이전트"]["topic"])
        good_prev = fetch_previous_suggestions(new_topics["칭찬 에이전트"]["topic"])
        new_prev = fetch_previous_suggestions(new_topics["발견 에이전트"]["topic"])

        bad_input = AgentInput(
            agent_type="개선 에이전트",
            topic_text=new_topics["개선 에이전트"]["topic"],
            context_info=new_topics["개선 에이전트"]["context"],
            user_context=user_context,
            habits=habits,
            full_code=combined_full_code,
            diff=combined_diff,
        )
        good_input = AgentInput(
            agent_type="칭찬 에이전트",
            topic_text=new_topics["칭찬 에이전트"]["topic"],
            context_info=new_topics["칭찬 에이전트"]["context"],
            user_context=user_context,
            habits=habits,
            full_code=combined_full_code,
            diff=combined_diff,
        )
        new_input = AgentInput(
            agent_type="발견 에이전트",
            topic_text=new_topics["발견 에이전트"]["topic"],
            context_info=new_topics["발견 에이전트"]["context"],
            user_context=user_context,
            habits=habits,
            full_code=combined_full_code,
            diff=combined_diff,
        )

        bad_result, good_result, new_result = await self._run_agents_concurrently_with_review(
            bad_input, bad_prev, good_input, good_prev, new_input, new_prev
        )

        ri_input = ReportIntegratorInput(agent_reports=[bad_result.dict(), good_result.dict(), new_result.dict()])
        ri_output: ReportIntegratorOutput = self.report_integrator.run(ri_input)
        final_report = ri_output.report
        return final_report

    async def _run_agents_concurrently_with_review(
        self,
        bad_input: AgentInput,
        bad_prev: str,
        good_input: AgentInput,
        good_prev: str,
        new_input: AgentInput,
        new_prev: str,
    ):
        # 비동기적으로 세 에이전트를 호출, previous_suggestions 전달
        import asyncio

        bad_task = asyncio.create_task(self.bad_agent_node.run(bad_input, previous_suggestions=bad_prev))
        good_task = asyncio.create_task(self.good_agent_node.run(good_input, previous_suggestions=good_prev))
        new_task = asyncio.create_task(self.new_agent_node.run(new_input, previous_suggestions=new_prev))

        results = await asyncio.gather(bad_task, good_task, new_task)
        return results[0], results[1], results[2]

    def _build_user_context(self, habits: List[str]) -> str:
        habit_str = self._habits_info_str(habits)
        return f"사용자 상태: 습관들: {habit_str}. 이 정보를 참고하여 보고서를 맞춤화."

    def _habits_info_str(self, habits: List[str]) -> str:
        infos = []
        for h in habits:
            occ = self.memory.get_habit_occurrences(h) or 0
            infos.append(f"'{h}' 습관({occ}회 지적)")
        return ", ".join(infos) if infos else "특별한 습관 없음"
