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

        return dedent(f"""
            ### Context (맥락)
            당신은 주니어 개발자의 성장을 돕는 시니어 개발자입니다.

            {user_context}

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
            - 구체적 개선 방향과 습관 개선 방안 제시
            - 친근하지만 기술적으로 명확한 톤 유지

            ### Instructions (지시문)
            1. 🤝 문제점 발견: 시급한 개선점과 코드 예시 제시
            2. ✨ 개선 방안: 개선 방법, 습관 개선 방향 제시
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

        return dedent(f"""
            ### Context (맥락)
            당신은 주니어 개발자를 응원하는 시니어 개발자입니다.

            {user_context}

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
            - 좋은 습관을 더욱 발전시킬 수 있는 방안 제안
            - 긍정적이고 격려하는 톤

            ### Instructions (지시문)
            1. 🌟 잘한 부분 발견
            2. 💡 발전 방향 제안 (좋은 습관 강화)
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

        return dedent(f"""
            ### Context (맥락)
            당신은 최신 트렌드에 정통한 시니어 개발자입니다.

            {user_context}

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
            - 실무 적용 시나리오와 습관 형성 방안 제시

            ### Instructions (지시문)
            1. 💫 오늘의 인사이트 소개 (이전 인사이트 복습)
            2. ⚡ 실제 적용 방법 (새로운 습관 형성)
            3. 🎨 활용 시나리오 (복습 포인트 반영)
            4. ✍️ 정리
            {review_section if review_section else ""}

            마지막으로 개발자를 응원하는 메시지를 전하세요.
        """).strip()

    # 먼저 스키마 정의
    habit_update_schema = {
        "type": "object",
        "properties": {
            "updated_habits": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "improvement": {"type": "boolean"},
                        "remove": {"type": "boolean"},
                        "new_occurrences": {"type": "integer"},
                        "new_last_improved": {"type": "string", "description": "YYYY-MM-DD 형식의 날짜 또는 null"},
                    },
                    "required": ["name", "improvement", "remove", "new_occurrences", "new_last_improved"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["updated_habits"],
        "additionalProperties": False,
    }

    @staticmethod
    def get_habit_update_prompt(today: str, original_habits_content: str, final_report: str):
        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 JSON 파서입니다. 아래 JSON 스키마를 반드시 준수하는 올바른 JSON만 반환하세요.\n"
                    "JSON 이외의 텍스트, 추가 설명, 주석 없이 스키마에 맞는 JSON 객체만 출력하세요.\n"
                    "스키마에 맞지 않으면 거부(refusal)하세요."
                ),
            },
            {
                "role": "user",
                "content": dedent(f"""
                    다음은 현재 관리중인 습관 목록(habits.txt) 내용입니다:

                    ---습관 목록 시작---
                    {original_habits_content}
                    ---습관 목록 끝---

                    아래는 오늘의 최종 종합 보고서입니다:
                    ---보고서 시작---
                    {final_report}
                    ---보고서 끝---

                    지시사항:
                    - 상기 습관 목록과 오늘 날짜({today}), 종합 보고서를 참고하여, 습관 목록을 업데이트할 방안을 JSON 스키마에 맞추어 제안하세요.
                    
                    규칙:
                    - improvement가 true이면 new_last_improved를 {today}로 설정
                    - remove가 true이면 해당 습관은 삭제
                    - 신규 습관 발견 시 new_occurrences=1, new_last_improved={today}로 설정
                    - 1주일 이상 개선 없었고 이번에도 improvement가 false라면 remove=true로 설정
                    """).strip(),
            },
        ]

        response_format = {
            "type": "json_schema",
            "json_schema": {"name": "habit_update_schema", "strict": True, "schema": AgentPrompts.habit_update_schema},
        }

        return messages, response_format
