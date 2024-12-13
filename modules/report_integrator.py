# report_integrator.py
from model import ReportIntegratorInput, ReportIntegratorOutput
from datetime import datetime
import re


class ReportIntegrator:
    def _get_agent_emoji(self, agent_type: str) -> str:
        """에이전트 타입에 맞는 이모지 반환"""
        emojis = {
            "개선 에이전트": "🛠️",  # 도구 이모지
            "칭찬 에이전트": "🌟",  # 반짝이는 별 이모지
            "발견 에이전트": "🔍",  # 돋보기 이모지
        }
        return emojis.get(agent_type, "📋")

    def _get_section_style(self, agent_type: str) -> dict:
        """각 섹션별 스타일 정보 반환"""
        styles = {
            "개선 에이전트": {"emoji": "🛠️", "color": "blue", "icon": "tools"},
            "칭찬 에이전트": {"emoji": "✨", "color": "green", "icon": "star"},
            "발견 에이전트": {"emoji": "🔍", "color": "purple", "icon": "search"},
        }
        return styles.get(agent_type, {"emoji": "📋", "color": "gray", "icon": "document"})

    def _format_section_header(self, agent_type: str, topic: str) -> str:
        """섹션 헤더를 더 세련되게 포맷팅"""
        style = self._get_section_style(agent_type)
        return f"""## {style['emoji']} {agent_type}
"""

    def _format_empty_report(self) -> list:
        """분석 결과가 없을 때의 메시지 포맷팅"""
        return [
            "# 🎯 분석 준비 중입니다",
            "",
            "### 잠시만 기다려주세요!",
            "",
            "> 더 나은 분석을 위해 다음 단계를 추천드립니다:",
            "",
            "1. 📦 코드 변경사항 모으기",
            "2. 📚 이전 분석 리포트 검토하기",
            "3. ✨ 새로운 개선사항 준비하기",
            "",
            "*더 풍성한 분석 결과로 곧 찾아뵙겠습니다* 💫",
        ]

    def _format_report_header(self, input: ReportIntegratorInput) -> list:
        """리포트 헤더를 더 구조화된 형태로 포맷팅"""
        header = ["# 📊 코드 분석 리포트", "", "## 📌 오늘의 주요 주제", ""]

        if input.agent_reports:
            for report in input.agent_reports:
                style = self._get_section_style(report["agent_type"])
                header.append(f"- {style['emoji']} **{report['topic']}**")
            header.append("")
        else:
            header.extend(["> 현재 분석할 변경사항이 없습니다.", ""])

        return header

    def _format_report_footer(self) -> list:
        """리포트 푸터를 더 세련되게 포맷팅"""
        return [
            "",
            "## ✨ 마무리",
            "",
            "> *더 나은 코드를 위한 여정을 응원합니다*",
            ">",
            "> 작은 개선이 모여 큰 변화가 됩니다",
            "",
            "---",
            "",
            "<div class='footer-meta' style='text-align: center;'>",
            "🤖 **CodeCast AI** | 문의: support@codecast.ai | 버전: 1.0.0",
            "</div>",
        ]

    def run(self, input: ReportIntegratorInput) -> ReportIntegratorOutput:
        """에이전트별 리포트를 통합하여 반환"""
        report_parts = self._format_report_header(input)

        if not input.agent_reports:
            report_parts.extend(self._format_empty_report())
        else:
            for idx, rep in enumerate(input.agent_reports):
                if idx > 0:
                    report_parts.append("\n<div class='section-divider'></div>\n")

                header = self._format_section_header(rep["agent_type"], rep["topic"])
                report_parts.append(header)

                # 컨텐츠 래핑
                report_parts.append("<<AGENT_SECTION_START>>")
                report_parts.append(rep["report_content"].strip())
                report_parts.append("<<AGENT_SECTION_END>>")

        # 푸터 추가
        report_parts.extend(self._format_report_footer())

        # report_parts를 하나의 문자열로 합침
        final_report = "\n".join(report_parts)

        # 3중 백틱으로 끝나는 라인 다음에 빈 줄 추가하기
        final_report = re.sub(r"(```)(\n)(?!\n)", r"\1\2\n", final_report)

        return ReportIntegratorOutput(report=final_report)
