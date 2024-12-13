# report_integrator.py
from model import ReportIntegratorInput, ReportIntegratorOutput
from datetime import datetime
import re


class ReportIntegrator:
    def _get_section_style(self, agent_type: str) -> dict:
        """각 섹션별 스타일 정보 반환"""
        styles = {
            "개선 에이전트": {"emoji": "🛠️"},
            "칭찬 에이전트": {"emoji": "✨"},
            "발견 에이전트": {"emoji": "🔍"},
        }
        return styles.get(agent_type, {"emoji": "📋"})

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
        header = ["## 📌 오늘의 주요 주제", ""]

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
            "🤖 <strong> CodeCast AI </strong> | 문의: support@codecast.ai | 버전: 1.0.0",
            "</div>",
        ]

    def _remove_single_backticks(self, text: str) -> str:
        """단일 백틱을 제거하는 함수"""
        # 3개의 연속된 백틱은 보존하기 위해 임시 토큰으로 대체
        temp_token = "TRIPLE_BACKTICK_TOKEN"
        text = text.replace("```", temp_token)

        # 단일 백틱 제거
        text = text.replace("`", "")

        # 임시 토큰을 다시 3개의 백틱으로 복원
        text = text.replace(temp_token, "```")

        return text

    def run(self, input: ReportIntegratorInput) -> ReportIntegratorOutput:
        """에이전트별 리포트를 통합하여 반환"""
        report_parts = ["## 📌 오늘의 주요 주제\n"]

        # 헤더에 주요 주제 추가
        if input.agent_reports:
            for rep in input.agent_reports:
                style = self._get_section_style(rep["agent_type"])
                report_parts.append(f"- {style['emoji']} **{rep['topic']}**")
            report_parts.append("")
        else:
            report_parts.extend(["> 현재 분석할 변경사항이 없습니다.", ""])

        # 빈 리포트 처리
        if not input.agent_reports:
            report_parts.extend(self._format_empty_report())
        else:
            # 각 에이전트 리포트 처리
            first_non_deep = True
            for rep in input.agent_reports:
                # 심층 분석 에이전트는 나중에 별도로 처리
                if rep["agent_type"] == "심층 분석 에이전트":
                    continue

                if not first_non_deep:
                    report_parts.append("\n<div class='section-divider'></div>\n")
                first_non_deep = False

                header = self._format_section_header(rep["agent_type"], rep["topic"])
                report_parts.append(header)
                report_parts.append("<<AGENT_SECTION_START>>")
                report_parts.append(rep["report_content"].strip())
                report_parts.append("<<AGENT_SECTION_END>>")

            # 심층 분석 에이전트 처리
            deep_analysis = next(
                (rep for rep in input.agent_reports if rep["agent_type"] == "심층 분석 에이전트"), None
            )

            if deep_analysis:
                report_parts.extend(
                    [
                        "\n<div class='section-divider'></div>\n",
                        f"## 🎯 심층 분석: {deep_analysis['topic']}\n",
                        "<<AGENT_SECTION_START>>",
                        deep_analysis["report_content"].strip(),
                        "<<AGENT_SECTION_END>>",
                    ]
                )

        # 푸터 추가
        report_parts.extend(
            [
                "\n## ✨ 마무리",
                "",
                "> *더 나은 코드를 위한 여정을 응원합니다*",
                ">",
                "> 작은 개선이 모여 큰 변화가 됩니다",
                "",
                "---",
                "",
                "<div class='footer'>",
                "  <div class='footer-content'>",
                "    <p>🤖 <strong>CodeCast AI</strong></p>",
                "    <p>분석 생성 시간: " + datetime.now().strftime("%Y-%m-%d %H:%M") + "</p>",
                "    <p>문의: support@codecast.ai</p>",
                "    <p>버전: 1.0.0</p>",
                "  </div>",
                "</div>",
            ]
        )

        # 최종 리포트 생성
        final_report = "\n".join(report_parts)

        # 코드 블록 이후 빈 줄 추가
        final_report = re.sub(r"(```)(\n)(?!\n)", r"\1\n\n", final_report)

        # 단일 백틱 제거
        final_report = self._remove_single_backticks(final_report)

        return ReportIntegratorOutput(report=final_report)
