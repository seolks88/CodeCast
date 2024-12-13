# modules/deep_explainer_agent_node.py

from textwrap import dedent
from ai_analyzer.llm_manager import LLMManager


class DeepExplainerAgentNode:
    def __init__(self, llm_manager: LLMManager):
        self.llm = llm_manager

    @staticmethod
    def get_system_prompt() -> str:
        return dedent("""
            당신은 '쪽집개 선생님'이라는 별명을 가진 시니어 개발자입니다.
            주니어 개발자들이 한 단계 더 성장하는데 필요한 인사이트를 
            "아, 이런 시각으로 봐야 하는구나!" 하고 깨달을 수 있게 설명하는 것이 특기입니다.
            실제 만나서 대화하는 것처럼 사람처럼 자연스럽게 말해주세요.
            
            당신의 역할:
            - 복잡한 개념을 3줄 요약으로 먼저 설명하기
            - 경험에서 우러나온 핵심 통찰력 전달하기
            - 더 넓은 시야와 깊이 있는 관점 제시하기
            
            답변 작성 시 유의사항:
            - 첫 설명은 무조건 3줄 이내로 간단하게
            - 모든 설명에 실제 현장 경험 녹여내기
            - 중요한 부분은 "💡 깊이 보기" 형식으로 강조
            - 기술적 깊이와 함께 다양한 관점 제시하기
            
            답변 구조:
            1. 3줄 요약
            2. 💡 핵심 통찰 (최대 3개)
            3. 실제 코드와 패턴 비교
            4. 심화 관점 소개
               - 기술적 깊이 (성능/보안/최적화)
               - 설계적 관점 (아키텍처/디자인패턴)
               - 협업과 확장 (팀워크/유지보수/스케일링)
               - 비즈니스 임팩트 (가치/비용/위험)
            5. 더 깊이 있는 성장을 위한 방향 제시
        """).strip()

    @staticmethod
    def get_user_prompt(final_report: str, feedback: str = "") -> str:
        feedback_section = ""
        if feedback:
            feedback_section = f"""
            @@@ 이전 분석의 심각한 문제점 @@@
            {feedback}
            
            위 문제점들을 반드시 해결하여 다시 분석해주세요.
            """

        return dedent(f"""
            다음은 최종 리포트 내용입니다:

            @@@ 리포트 내용 시작 @@@
            {final_report}
            @@@ 리포트 내용 끝 @@@

            {feedback_section}

            위 리포트에서 가장 핵심적이고 심층적인 분석이 필요한 주제 하나를 선택하여,
            깊이 있는 인사이트를 전달해주세요.
            
            @@@ 분석 작성 지침 @@@
            주제 선택 기준:
            - 개발자의 성장에 핵심이 되는 주제
            - 기술적 깊이가 있는 주제
            - 실무 경험이 녹아있는 주제

            설명 방식:
            - 핵심을 3줄로 먼저 요약
            - 실제 경험에 기반한 통찰 제시
            - 다양한 관점으로 깊이 있게 분석
            - 실전 코드와 패턴으로 이해도 높이기

            @@@ 답변 구조 @@@
            반드시 아래 마크다운 양식을 그대로 사용해주세요:

            ## [주제명] 파헤치기 🔍
            
            ### 한눈에 보기 (3줄 요약) ⚡
            - 핵심 내용을 쏙쏙
            - 이해하기 쉽게
            - 명확하게
            
            ### 코드로 보는 실전 적용 🎯
            ```python
            [실전에서 시니어 개발자가 사용하는 간략한 코드 예시]
            ```
            
            ### 더 깊이 들어가기 🚀
            - [성능, 보안, 설계, 협업, 비즈니스 등 다양한 관점에서 놓치기 쉽지만 꼭 고려해야 할 부분을 딱 한가지 선정하여 예시와 함께 깊이있지만 쉽게 2-3줄에 나누어 작성해주세요]  
        """).strip()

    async def run(self, final_report: str, feedback: str = "") -> str:
        """
        최종 리포트에서 하나의 토픽을 추출하고,
        그 토픽에 대한 깊이 있는 설명을 친절하고 쉽게 이해할 수 있게 생성합니다.
        """
        system_prompt = self.get_system_prompt()
        user_prompt = self.get_user_prompt(final_report, feedback)

        response = await self.llm.agenerate(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1)
        return response.strip()
