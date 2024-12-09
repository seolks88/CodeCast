# concept_habit_analyzer.py
from typing import Dict, Any, Tuple, List, Optional
import json
from ai_analyzer.llm_client import LLMClient
from model import ConceptHabitAnalyzerInput, ConceptHabitAnalyzerOutput


class ConceptHabitAnalyzer:
    """
    ConceptHabitAnalyzer 노드.

    변경사항(changes)을 입력받아 코드 변경 내에서 등장하는 기술적 개념 혹은
    개발자의 습관(좋거나 나쁜)을 추출하는 노드.

    LLM을 통해 JSON 스키마를 사용한 Structured Outputs로 개념, 습관 목록을 받아온다.
    """

    def __init__(self, llm_client: LLMClient):
        """
        Args:
            llm_client (LLMClient): LLM 호출용 클라이언트 인스턴스.
        """
        self.llm_client = llm_client
        # JSON Schema 정의
        self.concepts_habits_schema = {
            "type": "object",
            "properties": {
                "concepts": {"type": "array", "items": {"type": "string"}},
                "habits": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["concepts", "habits"],
            "additionalProperties": False,
        }

    async def run(self, input: ConceptHabitAnalyzerInput) -> ConceptHabitAnalyzerOutput:
        """
        개념/습관 추출 메서드.

        Args:
            input (ConceptHabitAnalyzerInput): 변경사항 정보를 담은 모델.

        Returns:
            ConceptHabitAnalyzerOutput: 추출된 개념 및 습관 리스트.
        """
        changes = input.changes
        changes_text = self._format_changes_for_concept_extraction(changes)
        prompt = self._get_concepts_habits_prompt(changes_text)

        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "concepts_habits_schema", "strict": True, "schema": self.concepts_habits_schema},
        }

        parsed_data, refusal = await self.llm_client.parse_json(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 JSON 파서입니다. 아래 JSON 스키마를 반드시 준수하는 올바른 JSON만 반환하세요.\n"
                        "JSON 이외의 텍스트, 추가 설명, 주석 없이 스키마에 맞는 JSON 객체만 출력하세요.\n"
                        "스키마에 맞지 않으면 거부(refusal)하세요."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format=response_format,
        )

        if refusal:
            # 모델이 스키마를 만족하는 JSON을 주지 않고 거부한 경우
            print("ConceptHabitAnalyzer: 모델이 거부했습니다. fallback으로 빈 리스트 반환")
            return ConceptHabitAnalyzerOutput(concepts=[], habits=[])

        if parsed_data is None:
            # parsed_data가 None이면 스키마 파싱 실패 or 응답 없음
            print("ConceptHabitAnalyzer: parsed_data is None. fallback to empty arrays.")
            return ConceptHabitAnalyzerOutput(concepts=[], habits=[])

        # parsed_data가 dict가 아닐 경우 문자열일 수 있으니 json.loads 시도
        if isinstance(parsed_data, str):
            try:
                parsed_data = json.loads(parsed_data)
            except json.JSONDecodeError:
                print("ConceptHabitAnalyzer: Invalid JSON in content. Returning empty arrays.")
                return ConceptHabitAnalyzerOutput(concepts=[], habits=[])

        # 이제 parsed_data는 dict 형태라고 가정 가능
        concepts = parsed_data.get("concepts", [])
        habits = parsed_data.get("habits", [])

        return ConceptHabitAnalyzerOutput(concepts=concepts, habits=habits)

    def _get_concepts_habits_prompt(self, changes_text: str) -> str:
        """개념/습관 추출용 프롬프트 생성 메서드."""
        return f"""
            다음은 코드 변경사항입니다:

            {changes_text}

            위 코드 변경사항에서 고려해야 할 주요 개념(기술, 패턴) 또는 습관(좋거나 나쁜 습관) 키워드만 추출해 주세요.
            반드시 위 스키마를 만족하는 JSON만 반환하고, JSON 이외의 텍스트나 불필요한 설명을 하지 마세요.
            스키마에 맞지 않으면 거부하세요.
            
            스키마:
            {{
                "concepts": ["개념1", "개념2", ...],
                "habits": ["습관1", "습관2", ...]
            }}
        """.strip()

    def _format_changes_for_concept_extraction(self, changes) -> str:
        """changes 리스트를 프롬프트용 텍스트로 변환하는 헬퍼 메서드."""
        return "\n".join(
            f"변경사항 {i}:\n파일: {ch['file_path']}\n변경사항:\n{ch['diff']}" for i, ch in enumerate(changes, start=1)
        )
