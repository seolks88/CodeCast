# report_integrator.py
from model import ReportIntegratorInput, ReportIntegratorOutput


class ReportIntegrator:
    def run(self, input: ReportIntegratorInput) -> ReportIntegratorOutput:
        """에이전트별 리포트를 통합하여 반환"""
        agent_reports = input.agent_reports
        report_parts = ["# 일일 통합 보고서", "", "아래는 각 에이전트별 분석 결과를 정리한 내용입니다.", ""]

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

        return ReportIntegratorOutput(report="\n".join(report_parts))
