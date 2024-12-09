# topic_selector.py (변경 후)
from model import TopicSelectorInput, TopicSelectorOutput
from typing import Dict, List, Optional

topic_selection_schema = {
    "type": "object",
    "properties": {
        "나쁜놈": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "relevant_code": {"type": "string"},
                "context": {"type": "string"},
            },
            "required": ["topic", "relevant_code", "context"],
            "additionalProperties": False,
        },
        "착한놈": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "relevant_code": {"type": "string"},
                "context": {"type": "string"},
            },
            "required": ["topic", "relevant_code", "context"],
            "additionalProperties": False,
        },
        "새로운놈": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "relevant_code": {"type": "string"},
                "context": {"type": "string"},
            },
            "required": ["topic", "relevant_code", "context"],
            "additionalProperties": False,
        },
    },
    "required": ["나쁜놈", "착한놈", "새로운놈"],
    "additionalProperties": False,
}


class TopicSelector:
    def __init__(self, llm_client, memory):
        self.llm_client = llm_client
        self.memory = memory
        self.max_retries = 3

    async def run(self, input: TopicSelectorInput) -> TopicSelectorOutput:
        changes = input.changes
        recent_topics = input.recent_topics
        recent_topic_texts = [t["raw_topic_text"] for t in recent_topics]

        for attempt in range(self.max_retries):
            data = await self._attempt_new_topics_selection(changes, recent_topic_texts)
            if data:
                # data는 dict 형태이므로 바로 TopicSelectorOutput에 넣는다.
                return TopicSelectorOutput(selected_topics=data)

        fallback = self._recover_with_review_mode(recent_topic_texts)
        return TopicSelectorOutput(selected_topics=fallback)

    async def _attempt_new_topics_selection(self, changes: List[Dict], recent_topic_texts: List[str]) -> Optional[Dict]:
        changes_text = self._summarize_changes_for_prompt(changes)
        recent_topics_text = ", ".join(recent_topic_texts) if recent_topic_texts else "없음"

        prompt = self._get_topic_selection_prompt(changes_text, recent_topics_text)
        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 JSON 파서입니다. 아래 JSON 스키마를 반드시 준수하는 올바른 JSON만 반환하세요.\n"
                    "JSON 이외의 텍스트, 추가 설명, 주석 없이 스키마에 맞는 JSON 객체만 출력하세요.\n"
                    "스키마에 맞지 않으면 거부(refusal)하세요."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        # JSON Schema를 사용한 response_format 지정
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "topic_selection_schema", "strict": True, "schema": topic_selection_schema},
        }

        parsed_data, refusal = await self.llm_client.parse_json(messages, response_format=response_format)

        if refusal:
            print(f"Topic selection attempt refused: {refusal}")
            return None

        if parsed_data is None:
            print("No parsed data returned from LLM.")
            return None

        # 여기서 parsed_data가 dict인지 확인 (parsed가 None이 아니었다면 dict일 가능성 큼)
        # parsed_data가 문자열일 경우 json.loads()로 디코딩
        if isinstance(parsed_data, str):
            import json

            try:
                parsed_data = json.loads(parsed_data)
            except json.JSONDecodeError:
                print("Invalid JSON content returned from LLM.")
                return None

        # 이제 parsed_data는 dict 형태라고 가정 가능
        if self._is_topic_overlapping(parsed_data, recent_topic_texts):
            print("Topic overlaps with recent topics.")
            return None

        return parsed_data

    def _summarize_changes_for_prompt(self, changes: List[Dict]) -> str:
        changes_summary = []
        for ch in changes:
            diff_excerpt = ch["diff"]
            if len(diff_excerpt) > 1000:
                diff_excerpt = diff_excerpt[:1000] + "..."
            changes_summary.append(f"파일: {ch['file_path']}\n변경사항:\n{diff_excerpt}")
        return "\n\n".join(changes_summary)

    def _is_topic_overlapping(self, data: Dict, recent_topic_texts: List[str]) -> bool:
        all_topics = [data["나쁜놈"]["topic"], data["착한놈"]["topic"], data["새로운놈"]["topic"]]
        if any(t in recent_topic_texts for t in all_topics):
            return True
        for t in all_topics:
            similar = self.memory.find_similar_topics(t, top_k=1)
            if similar and similar[0]["score"] < 0.8:
                return True
        return False

    def _recover_with_review_mode(self, recent_topic_texts: List[str]) -> Dict:
        fallback_topic = recent_topic_texts[0] if recent_topic_texts else "이전에 다룬 주제"
        dummy_code = "# 기존 코드 일부"
        dummy_context = f"이전에 '{fallback_topic}' 주제를 다룬 바 있습니다. 이번에는 복습하며 심화 제안을 드립니다."
        return {
            "나쁜놈": {"topic": fallback_topic + " 심화 개선점", "relevant_code": dummy_code, "context": dummy_context},
            "착한놈": {"topic": fallback_topic + " 접근 강화", "relevant_code": dummy_code, "context": dummy_context},
            "새로운놈": {
                "topic": fallback_topic + " 확장 아이디어",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
        }

    def _get_topic_selection_prompt(self, changes_text: str, recent_topics_text: str) -> str:
        return f"""
            아래는 최근 3일간 다룬 주제와 오늘 변경된 코드 내용입니다:

            최근 3일 주제: {recent_topics_text}
            오늘의 변경사항 요약:
            {changes_text}

            나쁜놈, 착한놈, 새로운놈 각각에 대해 위 스키마에 맞는 JSON을 반환하세요.
        """.strip()
