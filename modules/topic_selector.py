# topic_selector.py (변경 후)
from model import TopicSelectorInput, TopicSelectorOutput
from typing import Dict, List, Optional

topic_selection_schema = {
    "type": "object",
    "properties": {
        "개선 에이전트": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "relevant_code": {"type": "string"},
                "context": {"type": "string"},
            },
            "required": ["topic", "relevant_code", "context"],
            "additionalProperties": False,
        },
        "칭찬 에이전트": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "relevant_code": {"type": "string"},
                "context": {"type": "string"},
            },
            "required": ["topic", "relevant_code", "context"],
            "additionalProperties": False,
        },
        "발견 에이전트": {
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
    "required": ["개선 에이전트", "칭찬 에이전트", "발견 에이전트"],
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
            changes_summary.append(f"파일: {ch['file_path']}\n변경사항:\n{diff_excerpt}")
        return "\n\n".join(changes_summary)

    def _is_topic_overlapping(self, data: Dict, recent_topic_texts: List[str]) -> bool:
        roles = ["개선 에이전트", "칭찬 에이전트", "발견 에이전트"]

        # 먼저 topic만으로 recent_topics에 있는지 체크
        all_topics = [data[role]["topic"] for role in roles]
        if any(t in recent_topic_texts for t in all_topics):
            return True

        # topic + context를 합쳐서 유사도 검사
        for role in roles:
            t = data[role]["topic"]
            c = data[role]["context"]

            # topic과 context를 합쳐 하나의 텍스트로 구성
            combined_text = f"{t}\n\n[Context]: {c}"

            similar = self.memory.find_similar_topics(combined_text, top_k=1)
            if similar and similar[0]["score"] > 0.8:
                return True

        return False

    def _recover_with_review_mode(self, recent_topic_texts: List[str]) -> Dict:
        fallback_topic = recent_topic_texts[0] if recent_topic_texts else "이전에 다룬 주제"
        dummy_code = "# 기존 코드 일부"
        dummy_context = f"이전에 '{fallback_topic}' 주제를 다룬 바 있습니다. 이번에는 복습하며 심화 제안을 드립니다."
        return {
            "개선 에이전트": {
                "topic": fallback_topic + " 심화 개선점",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
            "칭찬 에이전트": {
                "topic": fallback_topic + " 접근 강화",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
            "발견 에이전트": {
                "topic": fallback_topic + " 확장 아이디어",
                "relevant_code": dummy_code,
                "context": dummy_context,
            },
        }

    def _get_topic_selection_prompt(self, changes_text: str, recent_topics_text: str) -> str:
        return f"""### 컨텍스트
아래는 최근 3일간 다룬 주제와 오늘 변경된 코드 내용입니다:

최근 3일 주제: 
---최근 3일 주제 시작---
{recent_topics_text}
---최근 3일 주제 끝---

오늘의 변경사항 요약:
---변경사항 시작---
{changes_text}
---변경사항 끝---

### 지시사항
1. 먼저 위 변경사항에서 사용된 주요 프로그래밍 언어(들)를 파악하세요.
2. 해당 언어(들)의 특성과 변경사항을 고려���여 각 에이전트의 역할에 맞는 주제를 선정해주세요:

- 개선 에이전트: 변경된 코드에서 발견된 해당 언어의 안티패턴이나 개선이 필요한 부분
- 칭찬 에이전트: 변경사항에서 잘 적용된 해당 언어의 패턴이나 더 개선할 수 있는 코딩 스타일
- 발견 에이전트: 변경된 코드에 적용 가능한 해당 언어의 최신 기능이나 더 나은 구현 방법

### 주의사항 (엄격한 중복 방지)
- 각 주제는 서로 중복되지 않아야 합니다
- 최근 3일간 다룬 주제와 절대 중복되지 않아야 합니다:
  * 동일한 주제는 물론, 단어만 다르고 의미가 비슷한 주제도 피해주세요
  * 다음과 같은 경우는 모두 중복으로 간주됩니다:
    - 동일 단어를 사용한 주제 ("코드 정리" vs "코드 정리하기")
    - 유사어를 사용한 주제 ("제거" vs "정리" vs "다루기" vs "관리")
    - 상위/하위 개념의 주제 ("주석 관리" vs "불필요한 주석")
    - 포함 관계의 주제 ("주석 제거" vs "주석 제거 및 정리")
  * 기존 주제와 관련된 모든 측면(제거, 개선, 관리, 다루기 등)을 피해주세요
- 완전히 새로운 관점이나 다른 영역의 주제를 선정하세요
- 변경된 코드의 프로그래밍 언어와 ���접적으로 연관된 주제를 선정하세요
- 구체적이고 실행 가능한 개선점을 담은 주제를 선정하세요
"""
