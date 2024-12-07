# agents_controller.py (개선 후)
from datetime import datetime
from typing import List, Dict, Optional
import json

from file_watcher.state_manager import DatabaseManager
from memory.memory_system import MemorySystem
from ai_analyzer.llm_client import LLMClient
from ai_analyzer.prompt_manager import AgentPrompts
from model import TopicSelection


class AgentsController:
    """여러 에이전트를 제어하여 일일 리포트를 생성하는 컨트롤러 클래스."""

    MAX_TOPIC_SELECTION_RETRIES = 3  # 매직 넘버 제거

    def __init__(self, db_path: str):
        self.db_manager = DatabaseManager(db_path)
        self.memory = MemorySystem(db_path=db_path)
        self.llm_client = LLMClient()
        # 프롬프트 함수 맵핑
        self.prompts = {
            "나쁜놈": AgentPrompts.get_bad_agent_prompt,
            "착한놈": AgentPrompts.get_good_agent_prompt,
            "새로운놈": AgentPrompts.get_new_agent_prompt,
        }

    async def initialize(self):
        """데이터베이스 초기화."""
        await self.db_manager.initialize()

    async def generate_daily_report(self) -> Optional[str]:
        """최근 변경사항을 분석하여 에이전트 별 리포트를 생성하고 통합 리포트를 반환."""
        changes = self.db_manager.get_recent_changes()
        if not changes:
            print("No recent changes to analyze.")
            return None

        recent_topics = self.memory.get_recent_topics(days=3)
        new_topics = await self._select_new_topics(changes, recent_topics)
        if not new_topics:
            print("Failed to select new topics. Falling back to review mode.")
            return None

        concepts, habits = await self._extract_concepts_and_habits(changes)
        user_context = self._build_user_context(concepts, habits)

        agent_reports = await self._generate_agent_reports(new_topics, user_context, concepts, habits)
        final_report = self._integrate_reports(agent_reports)
        return final_report

    async def _generate_agent_reports(
        self, new_topics: Dict, user_context: str, concepts: List[str], habits: List[str]
    ) -> List[Dict]:
        """에이전트 타입별 리포트를 생성하는 로직을 별도 메서드로 분리."""
        agent_types = ["나쁜놈", "착한놈", "새로운놈"]
        agent_reports = []

        for agent_type in agent_types:
            topic_text = new_topics[agent_type]["topic"]
            prompt = self._build_prompt(agent_type, new_topics, user_context, topic_text)

            response = await self.llm_client.analyze_text(prompt)
            report_id = self._store_agent_report(agent_type, topic_text, response)

            self._update_concepts_and_habits_in_memory(concepts, habits, response)
            agent_reports.append(
                {
                    "agent_type": agent_type,
                    "topic": topic_text,
                    "report_id": report_id,
                    "report_content": response,
                }
            )
        return agent_reports

    def _build_prompt(self, agent_type: str, new_topics: Dict, user_context: str, topic_text: str) -> str:
        """프롬프트 생성을 담당하는 헬퍼 메서드."""
        relevant_code = new_topics[agent_type]["relevant_code"]
        context_info = new_topics[agent_type]["context"]
        return self.prompts[agent_type](topic_text, relevant_code, context_info, user_context)

    def _store_agent_report(self, agent_type: str, topic_text: str, response: str) -> int:
        """생성된 리포트를 DB에 저장."""
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
        """리포트 결과에 따라 개념 난이도나 습관 빈도수를 업데이트."""
        for c in concepts:
            if c in response:
                current_diff = self.memory.get_concept_difficulty(c) or "basic"
                new_diff = "intermediate" if current_diff == "basic" else "advanced"
                self.memory.update_concept_difficulty(c, new_diff)

        for h in habits:
            if h in response:
                self.memory.record_habit_occurrence(h)

    async def _select_new_topics(self, changes: List[Dict], recent_topics: List[Dict]) -> Dict:
        """새로운 주제 선정을 시도하고 실패 시 복습 모드로 대체."""
        recent_topic_texts = [t["raw_topic_text"] for t in recent_topics]
        for attempt in range(self.MAX_TOPIC_SELECTION_RETRIES):
            data = await self._attempt_new_topics_selection(changes, recent_topic_texts)
            if data:
                return data
        return self._recover_with_review_mode(recent_topic_texts)

    async def _attempt_new_topics_selection(self, changes: List[Dict], recent_topic_texts: List[str]) -> Optional[Dict]:
        changes_text = self._summarize_changes_for_prompt(changes)
        recent_topics_text = ", ".join(recent_topic_texts) if recent_topic_texts else "없음"

        prompt = AgentPrompts.get_topic_selection_prompt(
            changes_text=changes_text, recent_topics_text=recent_topics_text
        )
        messages = [{"role": "user", "content": prompt}]
        parsed_data, refusal = await self.llm_client.parse_json(messages, response_format=TopicSelection)

        if refusal:
            print(f"Topic selection attempt refused: {refusal}")
            return None

        # parsed_data는 TopicSelection 인스턴스
        data_dict = parsed_data.dict()

        # 중복 주제 체크 (텍스트/의미 유사도)
        if self._is_topic_overlapping(data_dict, recent_topic_texts):
            print("Topic overlaps with recent topics.")
            return None

        return data_dict

    def _is_topic_overlapping(self, data: Dict, recent_topic_texts: List[str]) -> bool:
        """주제가 최근 주제와 텍스트 혹은 의미적으로 겹치는지 체크."""
        all_topics = [data[agent]["topic"] for agent in ["나쁜놈", "착한놈", "새로운놈"]]
        # 텍스트 기반 중복 검사
        if any(t in recent_topic_texts for t in all_topics):
            return True
        # 의미적 유사도 검사
        for t in all_topics:
            similar = self.memory.find_similar_topics(t, top_k=1)
            if similar and similar[0]["score"] < 0.8:
                return True
        return False

    def _summarize_changes_for_prompt(self, changes: List[Dict]) -> str:
        """변경사항을 프롬프트용 텍스트로 정리."""
        changes_summary = []
        for ch in changes:
            diff_excerpt = ch["diff"]
            if len(diff_excerpt) > 1000:
                diff_excerpt = diff_excerpt[:1000] + "..."
            changes_summary.append(f"파일: {ch['file_path']}\n변경사항:\n{diff_excerpt}")
        return "\n\n".join(changes_summary)

    def _recover_with_review_mode(self, recent_topic_texts: List[str]) -> Dict:
        """새로운 주제 선정 실패 시 복습 모드로 전환."""
        fallback_topic = recent_topic_texts[0] if recent_topic_texts else "이전에 다룬 주제"
        dummy_code = "# 기존 코드 일부"
        dummy_context = f"이전에도 '{fallback_topic}'를 다룬 바 있습니다. 심화 관점 제안."

        return {
            "나쁜놈": {"topic": fallback_topic + " 심화 개선점", "relevant_code": dummy_code, "context": dummy_context},
            "착한놈": {"topic": fallback_topic + " 접근 강화", "relevant_code": dummy_code, "context": dummy_context},
            "새로운놈": {
                "topic": fallback_topic + " 확장 아이디어",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
        }

    def _clean_json_response(self, response: str) -> str:
        """프롬프트 응답에서 JSON 추출."""
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline:].strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
        return cleaned

    async def _extract_concepts_and_habits(self, changes: List[Dict]):
        """변경사항에서 개념/습관 추출."""
        changes_text = self._format_changes_for_concept_extraction(changes)
        prompt = AgentPrompts.get_concepts_habits_prompt(changes_text)
        response = await self.llm_client.analyze_text(prompt)
        json_str = self._clean_json_response(response)
        data = json.loads(json_str)
        return data.get("concepts", []), data.get("habits", [])

    def _format_changes_for_concept_extraction(self, changes: List[Dict]) -> str:
        """개념/습관 추출용 포맷."""
        return "\n".join(
            f"변경사항 {i}:\n파일: {ch['file_path']}\n변경사항:\n{ch['diff']}" for i, ch in enumerate(changes, start=1)
        )

    def _build_user_context(self, concepts: List[str], habits: List[str]) -> str:
        """사용자 상태(개념 난이도, 습관 빈도)를 반영한 Context 문자열 생성."""
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

    def _integrate_reports(self, agent_reports: List[Dict]) -> str:
        """에이전트별 리포트를 하나의 통합 리포트로 묶는다.

        각 에이전트 타입의 보고서를 마크다운 형식으로 깔끔하게 정리하고,
        상단에 전체 리포트의 개요를 보여주는 식으로 개선.
        """
        # 상단에 전체 리포트 개요 헤더 추가
        report_parts = [
            "# 일일 통합 보고서",
            "",
            "아래는 각 에이전트(나쁜놈, 착한놈, 새로운놈)별 분석 결과를 정리한 내용입니다.",
            "각 섹션은 해당 에이전트의 주제와 개선 사항, 혹은 칭찬 포인트, 새로운 인사이트를 포함합니다.",
            "",
        ]

        for rep in agent_reports:
            agent_type = rep["agent_type"]
            topic = rep["topic"]
            content = rep["report_content"]

            # 에이전트별 섹션 헤더 추가
            report_parts.append(f"## [{agent_type}] {topic}")
            report_parts.append("")
            report_parts.append(content.strip())
            report_parts.append("\n---\n")  # 구분선

        # 마지막 불필요한 구분선 제거
        if report_parts[-1].strip() == "---":
            report_parts.pop()

        return "\n".join(report_parts)
