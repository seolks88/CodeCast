# agents_controller.py
from datetime import datetime
from typing import List, Dict
import json

from file_watcher.state_manager import DatabaseManager
from memory.memory_system import MemorySystem
from ai_analyzer.llm_client import LLMClient
from ai_analyzer.prompt_manager import AgentPrompts


class AgentsController:
    def __init__(self, db_path: str):
        self.db_manager = DatabaseManager(db_path)
        self.memory = MemorySystem(db_path=db_path)
        self.llm_client = LLMClient()  # 기존 llm_client 사용
        # 나쁜놈, 착한놈, 새로운놈 각각의 프롬프트 템플릿(앞서 정의한 프롬프트 구조 이용)
        self.prompts = {
            "나쁜놈": AgentPrompts.get_bad_agent_prompt,
            "착한놈": AgentPrompts.get_good_agent_prompt,
            "새로운놈": AgentPrompts.get_new_agent_prompt,
        }

    async def initialize(self):
        await self.db_manager.initialize()

    def _format_changes(self, changes: List[Dict]) -> str:
        formatted = []
        for i, ch in enumerate(changes, start=1):
            formatted.append(f"변경사항 {i}:\n파일: {ch['file_path']}\n변경사항:\n{ch['diff']}")
        return "\n".join(formatted)

    async def generate_daily_report(self):
        changes = self.db_manager.get_recent_changes()
        if not changes:
            print("No recent changes to analyze.")
            return None

        recent_topics = self.memory.get_recent_topics(days=3)
        recent_topic_texts = [t["raw_topic_text"] for t in recent_topics]

        new_topics = await self._select_new_topics(changes, recent_topic_texts)

        concepts, habits = await self._extract_concepts_and_habits(changes)
        user_context = self._build_user_context(concepts, habits)

        agent_types = ["나쁜놈", "착한놈", "새로운놈"]
        agent_reports = []

        for agent_type in agent_types:
            topic_text = new_topics[agent_type]["topic"]
            relevant_code = new_topics[agent_type]["relevant_code"]
            context_info = new_topics[agent_type]["context"]

            prompt = self.prompts[agent_type](topic_text, relevant_code, context_info, user_context)

            response = await self.llm_client.analyze_text(prompt)
            topic_id = self.memory.add_topic(datetime.now().isoformat(), topic_text)

            report_id = self.memory.add_agent_report(
                date=datetime.now().isoformat(),
                agent_type=agent_type,
                topic_id=topic_id,
                report_content=response,
                summary=f"{topic_text} 관련 {agent_type} 제안",
                code_refs=[],
                raw_topic_text=topic_text,
            )

            agent_reports.append(
                {"agent_type": agent_type, "topic": topic_text, "report_id": report_id, "report_content": response}
            )

            for c in concepts:
                if c in response:
                    current_diff = self.memory.get_concept_difficulty(c) or "basic"
                    new_diff = "intermediate" if current_diff == "basic" else "advanced"
                    self.memory.update_concept_difficulty(c, new_diff)

            for h in habits:
                if h in response:
                    self.memory.record_habit_occurrence(h)

        final_report = self._integrate_reports(agent_reports)
        return final_report

    def _clean_json_response(self, response: str) -> str:
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        return cleaned

    async def _select_new_topics(self, changes, recent_topic_texts, max_retries=3):
        changes_summary = []
        for ch in changes:
            file_path = ch["file_path"]
            diff_excerpt = ch["diff"]
            if len(diff_excerpt) > 1000:
                diff_excerpt = diff_excerpt[:1000] + "..."
            changes_summary.append(f"파일: {file_path}\n변경사항:\n{diff_excerpt}")
        changes_text = "\n\n".join(changes_summary)

        recent_topics_text = ", ".join(recent_topic_texts) if recent_topic_texts else "없음"

        prompt = AgentPrompts.get_topic_selection_prompt(
            changes_text=changes_text, recent_topics_text=recent_topics_text
        )

        for attempt in range(max_retries):
            response = await self.llm_client.analyze_text(prompt)
            json_str = self._clean_json_response(response)
            try:
                data = json.loads(json_str)

                if not all(k in data for k in ["나쁜놈", "착한놈", "새로운놈"]):
                    raise ValueError("응답 JSON에 필요한 키가 없습니다.")

                all_topics = [data["나쁜놈"]["topic"], data["착한놈"]["topic"], data["새로운놈"]["topic"]]

                # 텍스트 기반 비교
                if any(t in recent_topic_texts for t in all_topics):
                    raise ValueError("텍스트 기반으로 겹치는 주제 발견")

                # 의미적 유사도 검사
                for t in all_topics:
                    similar = self.memory.find_similar_topics(t, top_k=1)
                    if similar and similar[0]["score"] < 0.8:
                        raise ValueError("의미적으로 유사한 기존 주제와 겹치는 주제 발견")

                # 문제 없이 통과하면 주제 반환
                return data

            except Exception as e:
                print(f"토픽 선정 시도 {attempt+1}/{max_retries} 실패: {str(e)}")
                # 계속 재시도

        # 여기까지 왔다면 max_retries 모두 실패
        print("최대 재시도 횟수 도달. 새로운 주제 선정이 어렵습니다. 복습 모드로 전환합니다.")
        return self._recover_with_review_mode(recent_topic_texts)

    def _recover_with_review_mode(self, recent_topic_texts):
        # 이미 다뤘던 주제 중 하나를 골라 복습/심화 주제로 선정
        # 최근 주제 중 하나를 선택
        fallback_topic = recent_topic_texts[0] if recent_topic_texts else "이전에 다룬 주제"
        dummy_code = "# 기존 코드 일부"
        dummy_context = f"이전에도 '{fallback_topic}'를 다룬 바 있습니다. 이번에는 해당 주제를 복습하면서 더 심화된 관점(테스트 전략, 성능 최적화, 보안 강화 등)에서 제안합니다."

        # 복습 모드에서는 기존 주제를 약간 변형
        return {
            "나쁜놈": {
                "topic": fallback_topic + " 심화 개선점",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
            "착한놈": {
                "topic": fallback_topic + " 접근 강화",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
            "새로운놈": {
                "topic": fallback_topic + " 확장 아이디어",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
        }

    def _build_context_from_similar_reports(self, similar_reports):
        context_summaries = []
        for rep in similar_reports:
            meta = rep["metadata"]
            summary = meta.get("summary", "")
            context_summaries.append(summary)
        return "\n".join(context_summaries)

    def _integrate_reports(self, agent_reports):
        integrated = []
        for rep in agent_reports:
            integrated.append(f"### {rep['agent_type']} - {rep['topic']}\n{rep['report_content']}\n")
        return "\n".join(integrated)

    async def _extract_concepts_and_habits(self, changes: List[Dict]):
        changes_text = self._format_changes(changes)
        prompt = AgentPrompts.get_concepts_habits_prompt(changes_text)

        response = await self.llm_client.analyze_text(prompt)
        json_str = self._clean_json_response(response)
        data = json.loads(json_str)

        return data.get("concepts", []), data.get("habits", [])

    def _build_user_context(self, concepts: List[str], habits: List[str]) -> str:
        concept_info = []
        for c in concepts:
            diff = self.memory.get_concept_difficulty(c)
            if not diff:
                self.memory.update_concept_difficulty(c, "basic")
                diff = "basic"
            concept_info.append(f"'{c}' 개념({diff})")

        habit_info = []
        for h in habits:
            occ = self.memory.get_habit_occurrences(h)
            if occ is None:
                occ = 0
            habit_info.append(f"'{h}' 습관({occ}회 지적)")

        concept_str = ", ".join(concept_info) if concept_info else "특별한 개념 없음"
        habit_str = ", ".join(habit_info) if habit_info else "특별한 습관 없음"

        return (
            f"사용자 상태: 개념들: {concept_str}, 습관들: {habit_str}. 이 정보를 참고하여 보고서를 더욱 맞춤화해주세요."
        )
