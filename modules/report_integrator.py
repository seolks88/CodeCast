# report_integrator.py
from model import ReportIntegratorInput, ReportIntegratorOutput


class ReportIntegrator:
    def _get_agent_emoji(self, agent_type: str) -> str:
        """에이전트 타입에 맞는 이모지 반환"""
        emojis = {"개선 에이전트": "🔧", "칭찬 에이전트": "👏", "발견 에이전트": "💡"}
        return emojis.get(agent_type, "📝")

    def _format_section_header(self, agent_type: str, topic: str) -> str:
        """섹션 헤더 포맷팅"""
        emoji = self._get_agent_emoji(agent_type)
        return f"## {emoji} [{agent_type}] {topic}"

    def _add_visual_separator(self) -> str:
        """시각적 구분선 추가"""
        return "\n\n---\n\n"

    def _format_empty_report(self) -> list:
        """분석 결과가 없을 때의 메시지 포맷팅"""
        return [
            "아직 분석할 만한 의미있는 변경사항이 없네요! 🎯",
            "",
            "💡 이럴 때는 이렇게 해보세요:",
            "1. 코드 변경사항을 좀 더 모아서 한 번에 분석해보기",
            "2. 이전 분석 리포트의 제안사항 검토해보기",
            "3. 새로운 기능이나 개선사항 구현 시작하기",
            "",
            "다음 번에는 더 풍성한 분석 결과로 찾아뵙겠습니다! 😊",
        ]

    def _format_report_header(self) -> list:
        """리포트 헤더 포맷팅"""
        return ["# 📊 일일 코드 분석 리포트", "", "안녕하세요! 오늘의 코드 변경사항을 분석한 결과를 공유드립니다.", ""]

    def _format_report_footer(self) -> list:
        """리포트 푸터 포맷팅"""
        return [
            "",
            "---",
            "",
            "### 💝 오늘의 한마디",
            "작은 변화가 모여 큰 발전이 됩니다. 오늘도 수고하셨습니다!",
            "",
            "이 리포트는 CodeCast 자동 분석 시스템을 통해 생성되었습니다.",
            "© 2024 CodeCast",
        ]

    def run(self, input: ReportIntegratorInput) -> ReportIntegratorOutput:
        """에이전트별 리포트를 통합하여 반환"""
        report_parts = self._format_report_header()

        if not input.agent_reports:
            report_parts.extend(self._format_empty_report())
        else:
            for rep in input.agent_reports:
                agent_type = rep["agent_type"]
                topic = rep["topic"]
                content = rep["report_content"]

                # 섹션 헤더 추가
                report_parts.append(self._format_section_header(agent_type, topic))
                report_parts.append("")

                # 컨텐츠 추가
                report_parts.append(content.strip())

                # 구분선 추가 (마지막 항목 제외)
                if rep != input.agent_reports[-1]:
                    report_parts.append(self._add_visual_separator())

        # 푸터 추가
        report_parts.extend(self._format_report_footer())

        return ReportIntegratorOutput(report="\n".join(report_parts))
