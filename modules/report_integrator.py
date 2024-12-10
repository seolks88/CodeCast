# report_integrator.py
from model import ReportIntegratorInput, ReportIntegratorOutput


class ReportIntegrator:
    def run(self, input: ReportIntegratorInput) -> ReportIntegratorOutput:
        """에이전트별 리포트를 통합하여 반환"""
        agent_reports = input.agent_reports
        report_parts = ["# 일일 통합 보고서", "", "아래는 각 에이전트별 분석 결과를 정리한 내용입니다.", ""]

        if not agent_reports:
            # 에이전트 결과가 하나도 없는 경우 기본 메시지 추가
            report_parts.append("분석 가능한 변경 사항이 없거나, 에이전트 실행 결과가 없습니다.\n")
            report_parts.append("다음 기회에 더 풍부한 분석을 기대해주세요!\n")
        else:
            for rep in agent_reports:
                agent_type = rep["agent_type"]
                topic = rep["topic"]
                content = rep["report_content"]

                report_parts.append(f"## [{agent_type}] {topic}")
                report_parts.append("")
                report_parts.append(content.strip())
                report_parts.append("\n---\n")

            if report_parts[-1].strip() == "---":
                report_parts.pop()

        # 추가로 하단에 고정 메시지를 넣고 싶다면 여기서 추가
        report_parts.append("")
        report_parts.append("이 리포트는 CodeCast 자동 분석 시스템을 통해 생성되었습니다.")
        report_parts.append("© 2024 CodeCast")

        return ReportIntegratorOutput(report="\n".join(report_parts))
