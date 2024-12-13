# topic_selector.py (변경 후)
from model import TopicSelectorInput, TopicSelectorOutput
from typing import Dict, List, Optional
from config.settings import Config
from ai_analyzer.llm_manager import LLMManager
from textwrap import dedent

# topic_selector.py
topic_selection_schema = {
    "type": "object",
    "properties": {
        "개선 에이전트": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "context": {"type": "string"},
                "related_files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["topic", "context", "related_files"],
            "additionalProperties": False,
        },
        "칭찬 에이전트": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "context": {"type": "string"},
                "related_files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["topic", "context", "related_files"],
            "additionalProperties": False,
        },
        "발견 에이전트": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "context": {"type": "string"},
                "related_files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["topic", "context", "related_files"],
            "additionalProperties": False,
        },
    },
    "required": ["개선 에이전트", "칭찬 에이전트", "발견 에이전트"],
    "additionalProperties": False,
}


class TopicSelector:
    def __init__(self, memory, llm_manager: LLMManager):
        self.memory = memory
        self.llm = llm_manager
        self.max_retries = Config.TOPIC_SELECTOR_MAX_RETRIES
        self.valid_agent_types = {"개선 에이전트", "칭찬 에이전트", "발견 에이전트"}

    @staticmethod
    def get_system_prompt() -> str:
        return dedent("""
            당신은 코드 변경사항을 분석하여 세 명의 코드 리뷰어를 위한 토픽을 선정하는 전문가입니다.
            
            # 리뷰어 특성
            1. 개선 에이전트 (나쁜놈)
               - "이봐, 이건 좀 아닌데..." 라고 말할만한 코���를 찾습니다
               - 개선이 필요한 패턴이나 잠재적 문제를 발견합니다
            
            2. 칭찬 에이전트 (좋은놈)
               - "오, 이건 정말 잘했네!" 라고 말할만한 코드를 찾습니다
               - 잘 작성된 코드나 좋은 설계 결정을 발견합니다
            
            3. 발견 에이전트 (새로운놈)
               - "이거 이렇게 해보면 어때?" 라고 제안할 내용을 찾습니다
               - 새로운 접근 방식이나 개선 아이디어를 제시합니다
            
            # 토픽 선정 원칙
            1. 구체성
               - 코드의 특정 부분이나 패���을 명확히 지정하세요
               - 예시: "함수 X의 매개변수 검증 로직" (O)
               - 예시: "전반적인 코드 구조" (X)
            
            2. 실용성
               - 실제로 적용 가능한 개선/칭찬/제안이어야 합니다
               - 예시: "캐시 도입으로 성능 개선" (O)
               - 예시: "전체 시스템 재설계" (X)
            
            3. 독립성
               - 각 리뷰어의 토픽이 서로 겹치지 않아야 합니다
               - 예시: 같은 함수를 다른 관점에서 보는 것은 가능
               - 예시: 같은 문제점을 지적하는 것은 불가
            
            4. 연관성
               - 변경된 코드와 직접 관련된 토픽만 선정하세요
               - 예시: 수정된 함수의 개선점 (O)
               - 예시: 수정되지 않은 코드의 문제점 (X)
            
            # 출력 형식
            다음 JSON 스키마를 정확히 준수하세요:
            {
              "개선 에이전트": {
                "topic": "구체적인 주제",
                "context": "왜 이 주제가 중요한지 설명",
                "related_files": ["관련 파일 경로"]
              },
              "칭찬 에이전트": { ... },
              "발견 에이전트": { ... }
            }
            
            추가 설명이나 주석 없이 순수 JSON만 반환하세요.
        """).strip()

    @staticmethod
    def get_user_prompt(changes_text: str, recent_topics_text: str, allow_duplicates: bool) -> str:
        base_prompt = dedent(f"""
            아래 코드 변경사항과 최근 주제를 바탕으로 세 명의 리뷰어에게 맞는 주제를 선정해주세요.
    
            ### 리뷰어 정보
            1. 개선 에이전트 (나쁜놈):
               - "이봐, 이건 좀 아닌데..." 라고 말할만한 코드 습관을 찾아내는 역할
               - 주목할 부분:
                 * 코드 냄새 (반복되는 코드, 쓸데없이 복잡한 로직)
                 * 위험한 코딩 습관 (예외처리 누락, 메모리 누수 위험)
                 * 유지보수하기 어려운 구조
                 * 성능 저하를 일으킬 수 있는 패턴
                 * 버그 유발 가능성이 높은 코드
    
            2. 칭찬 에이전트 (좋은놈):
               - "오, 이건 정말 잘했네!" 라고 칭찬할만한 코드를 발견하는 역할
               - 주목할 부분:
                 * 깔끔하고 읽기 쉬운 코드
                 * 영리한 문제 해결 방식
                 * 재사용성이 뛰어난 설계
                 * 효율적인 알고리즘 선택
                 * 센스있는 에러 처리
    
            3. 발견 에이전트 (새로운놈):
               - "이거 이렇게 해보면 어때?" 라고 새로운 관점을 제시하는 역할
               - 주목할 부분:
                 * 최신 언어 기능으로 개선할 부분
                 * 새로운 라이브러리로 대체 가능한 부분
                 * 더 현대적인 코딩 패턴 제안
                 * 테스트나 유지보수를 더 쉽게 만들 수 있는 방법
                 * 개발자 경험을 개선할 수 있는 제안
    
            ### 분석할 코드 변경사항
            {changes_text}
    
            ### 최근 리뷰 주제 목록
            {recent_topics_text}
            
            ### 중복 처리 규칙:
            {
            '''
            [중복 허용 모드]
            - 최근 주제와의 중복이 허용됩니다
            - 단, 각 리뷰어 간의 주제는 중복되지 않아야 합니다
            '''
            if allow_duplicates else
            '''
            [중복 방지 모드]
            - 최근 주제와 절대 중복되지 않아야 합니다
            - 유사어, 동일 개념, 포함 관계의 주제도 피해주세요
            - 완전히 새로운 관점의 주제를 선정해주세요
            '''
            }
    
            각 리뷰어의 주제에는 다음을 포함해주세요:
            1. topic: 구체적이고 명확한 리뷰 주제
            2. context: 왜 이 주제가 중요한지 설명
            3. related_files: 주제와 관련된 파일 경로 목록
        """).strip()

        return base_prompt

    async def run(self, input: TopicSelectorInput) -> TopicSelectorOutput:
        changes = input.changes
        recent_topics = input.recent_topics
        recent_topic_texts = [t["raw_topic_text"] for t in recent_topics]

        # 최대 시도 횟수만큼 반복
        for attempt in range(self.max_retries):
            print(f"[INFO] Attempting topic selection (attempt {attempt + 1}/{self.max_retries})")
            data = await self._attempt_new_topics_selection(changes, recent_topic_texts, allow_duplicates=False)

            if data:
                return TopicSelectorOutput(selected_topics=data)
            else:
                print(f"[INFO] Topic selection failed, retrying... (attempt {attempt + 1}/{self.max_retries})")

        # 모든 시도 실패 시 중복 허용 모드로 한 번 더 시도
        print("[INFO] All attempts failed, trying with duplicates allowed...")
        data = await self._attempt_new_topics_selection(changes, recent_topic_texts, allow_duplicates=True)

        if data:
            return TopicSelectorOutput(selected_topics=data)

        print("[WARNING] All topic selection attempts failed")
        return TopicSelectorOutput(selected_topics={})

    async def _attempt_new_topics_selection(
        self, changes: List[Dict], recent_topic_texts: List[str], allow_duplicates: bool
    ) -> Optional[Dict]:
        changes_text = self._summarize_changes_for_prompt(changes)
        recent_topics_text = ", ".join(recent_topic_texts) if recent_topic_texts else "없음"

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": self.get_user_prompt(changes_text, recent_topics_text, allow_duplicates)},
        ]

        try:
            parsed_data, error = await self.llm.aparse_json(
                messages=messages,
                json_schema=topic_selection_schema,
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            if error:
                print(f"[ERROR] Topic selection attempt failed: {error}")
                return None

            # 에이전트 타입 검증
            if not self.validate_agent_types(parsed_data):
                print("[ERROR] Invalid agent types in response")
                return None

            # allow_duplicates가 False일 경우에만 중복 체크
            if not allow_duplicates and self._is_topic_overlapping(parsed_data, recent_topic_texts):
                print("[INFO] Topic overlaps with recent topics.")
                return None

            return parsed_data

        except Exception as e:
            print(f"[ERROR] Unexpected error in topic selection: {str(e)}")
            return None

    def _summarize_changes_for_prompt(self, changes: List[Dict]) -> str:
        changes_summary = []
        for ch in changes:
            diff_excerpt = ch["diff"]
            changes_summary.append(f"파일: {ch['file_path']}\n변경사항:\n{diff_excerpt}")
        return "\n\n".join(changes_summary)

    def _is_topic_overlapping(self, data: Dict, recent_topic_texts: List[str]) -> bool:
        roles = ["개선 에이전트", "칭찬 에이전트", "발견 에이전트"]
        all_topics = [data[role]["topic"] for role in roles]
        if any(t in recent_topic_texts for t in all_topics):
            return True
        # 추가로 벡터 검색 등으로 유사도 검사 가능
        for role in roles:
            t = data[role]["topic"]
            c = data[role]["context"]
            combined_text = f"{t}\n\n[Context]: {c}"
            similar = self.memory.find_similar_topics(combined_text, top_k=1)
            if similar and similar[0]["score"] > 0.8:
                return True
        return False

    def validate_agent_types(self, data: dict) -> bool:
        """에이전트 타입 검증 - 정확히 세 개의 올바른 에이전트 타입이 있어야 함"""
        return set(data.keys()) == self.valid_agent_types
