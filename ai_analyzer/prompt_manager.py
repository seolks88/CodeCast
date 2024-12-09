from textwrap import dedent


class AgentPrompts:
    @staticmethod
    def get_bad_agent_prompt(
        topic_text: str,
        context_info: str,
        user_context: str,
        full_code: str,
        diff: str,
        previous_suggestions: str = "",
    ) -> str:
        review_section = ""
        must_mention_review = ""
        if previous_suggestions.strip():
            review_section = dedent(f"""
            5. 📚 복습  
            - 아래는 이전 보고서에서 유사한 개선 사항과 코드 예시를 다시 상기시키는 내용입니다.
            {previous_suggestions.strip()}
            """).strip()
            must_mention_review = "이전에 언급된 개선사항 및 코드 예시를 반드시 참조하여 현재 제안에 반영하세요."

        must_mention_difficulty = "사용자 상태에 언급된 개념들의 난이도 정보를 반드시 개선 방안 섹션에서 언급하세요."

        return dedent(f"""
            ### Context (맥락)
            당신은 주니어 개발자의 성장을 돕는 시니어 개발자입니다.

            {user_context}  
            {must_mention_difficulty}

            오늘 다룰 주제: "{topic_text}"

            아래는 전체 코드 내용입니다:
            {full_code}

            [오늘 변경된 Diff]
            {diff}

            [맥락 (context)]
            {context_info}

            이 에이전트에서는 "{topic_text}"와 관련하여 가장 시급히 개선할 문제점을 선정하세요.
            {must_mention_review}

            ### Strategy (전략)
            - [오늘 변경된 Diff] 내에서 핵심 문제점 1개 식별
            - 해당 문제점 코드 스니펫 제시(``` 코드블록 ```)
            - 구체적 개선 방향 및 개념 난이도 언급
            - 친근하지만 기술적으로 명확한 톤 유지

            ### Instructions (지시문)
            1. 🤝 문제점 발견: 시급한 개선점과 코드 예시 제시
            2. ✨ 개선 방안: 개선 방법, 개념 난이도 언급
            3. 💝 실무 꿀팁: 단계별 개선 프로세스, 복습사항 반영
            4. ✍️ 정리: 한 줄로 요약
            {review_section if review_section else ""}

            마지막으로 주니어 개발자에게 응원 메시지를 전하세요.
        """).strip()

    @staticmethod
    def get_good_agent_prompt(
        topic_text: str,
        context_info: str,
        user_context: str,
        full_code: str,
        diff: str,
        previous_suggestions: str = "",
    ) -> str:
        review_section = ""
        must_mention_review = ""
        if previous_suggestions.strip():
            review_section = dedent(f"""
            5. 📚 복습  
            - 아래는 이전 보고서에서 유사한 칭찬 포인트나 긍정적 접근 방법을 언급한 내용입니다.
            {previous_suggestions.strip()}
            """).strip()
            must_mention_review = "이전에 언급한 칭찬 포인트를 다시 상기시키고 현재 상황과 연결하세요."

        must_mention_difficulty = "개념 난이도를 언급하세요. 예: '현재 {개념명} 개념은 {난이도}'"

        return dedent(f"""
            ### Context (맥락)
            당신은 주니어 개발자를 응원하는 시니어 개발자입니다.

            {user_context}  
            {must_mention_difficulty}

            오늘 다룰 주제: "{topic_text}"

            [전체 코드]
            {full_code}

            [오늘 변경된 Diff]
            {diff}

            [맥락 (context)]
            {context_info}

            이 에이전트에서는 잘한 부분을 칭찬하고 발전 방향을 제안하세요.
            {must_mention_review}

            ### Strategy (전략)
            - [오늘 변경된 Diff] 내에서 잘한 점 코드 스니펫 제시 (``` 코드블록 ```)
            - 발전 방안 제안 시 난이도 언급
            - 긍정적이고 격려하는 톤

            ### Instructions (지시문)
            1. 🌟 잘한 부분 발견
            2. 💡 발전 방향 제안 (난이도 언급)
            3. 🎯 실무 인사이트 (복습 포인트 반영)
            4. ✍️ 정리
            {review_section if review_section else ""}

            마지막으로 주니어 개발자를 응원하는 메시지를 전하세요.
        """).strip()

    @staticmethod
    def get_new_agent_prompt(
        topic_text: str,
        context_info: str,
        user_context: str,
        full_code: str,
        diff: str,
        previous_suggestions: str = "",
    ) -> str:
        review_section = ""
        must_mention_review = ""
        if previous_suggestions.strip():
            review_section = dedent(f"""
            5. 📚 복습  
            - 아래는 이전 보고서에서 유사한 새로운 인사이트나 트렌드 언급 내용입니다.
            {previous_suggestions.strip()}
            """).strip()
            must_mention_review = "이전에 제안한 유사한 인사이트를 다시 상기시키고 현재 제안에 연결하세요."

        must_mention_difficulty = "개념 난이도를 언급하세요. 예: '현재 {개념명} 개념은 {난이도}'"

        return dedent(f"""
            ### Context (맥락)
            당신은 최신 트렌드에 정통한 시니어 개발자입니다.

            {user_context}
            {must_mention_difficulty}

            오늘 다룰 주제: "{topic_text}"

            [전체 코드]
            {full_code}

            [오늘 변경된 Diff]
            {diff}

            [맥락 (context)]
            {context_info}

            이 에이전트에서는 새로운 기술적 인사이트를 제안하세요.
            {must_mention_review}

            ### Strategy (전략)
            - [오늘 변경된 Diff]와 연관된 최신 트렌드나 베스트 프랙티스 제안
            - 실무 적용 시나리오와 난이도 언급

            ### Instructions (지시문)
            1. 💫 오늘의 인사이트 소개 (이전 인사이트 복습)
            2. ⚡ 실제 적용 방법 (난이도 언급)
            3. 🎨 활용 시나리오 (복습 포인트, 난이도 결합)
            4. ✍️ 정리
            {review_section if review_section else ""}

            마지막으로 개발자를 응원하는 메시지를 전하세요.
        """).strip()

    @staticmethod
    def get_topic_selection_prompt(changes_text: str, recent_topics_text: str) -> str:
        return dedent(f"""
            다음은 최근 3일간 다룬 주제와 오늘 변경된 코드 내용입니다:

            최근 3일 주제: {recent_topics_text}
            오늘의 변경사항 요약:
            {changes_text}

            개선 에이전트, 칭찬 에이전트, 발견 에이전트 각각에 대해 위 스키마에 맞는 JSON만 반환하세요.
            스키마에 없는 필드나 추가 텍스트 없이, 반드시 JSON 스키마에 정확히 일치하는 형식으로만 응답하세요.
            스키마를 만족하지 못하거나, JSON 이외의 텍스트를 포함하면 모델은 거부(refusal)해야 합니다.

            아래 3명의 에이전트(개선 에이전트, 칭찬 에이전트, 발견 에이전트)에게 각각 다른 주제를 할당:
            - 개선 에이전트: 시급히 개선할 문제점(나쁜습관)
            - 칭찬 에이전트: 이미 잘한 부분(좋은습관)
            - 발견 에이전트: 새로운 기능/구조/접근방식(신규 인사이트)
            """).strip()

    @staticmethod
    def get_concepts_habits_prompt(changes_text: str) -> str:
        return dedent(f"""
            다음은 코드 변경사항입니다:

            {changes_text}

            위 코드 변경사항에서 개발자가 고려해야 할 주요 개념(기술, 패턴) 또는 주로 등장하는 습관(좋거나 나쁜 습관) 키워드만 추출해 주세요.
            출력 형식은 JSON으로:
            {{
                "concepts": ["개념1", "개념2", ...],
                "habits": ["습관1", "습관2", ...]
            }}
            불필요한 설명 없이 JSON만 반환하세요.
        """).strip()
