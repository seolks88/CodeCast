# analyze.py
import asyncio
import os
from ai_analyzer.code_analyzer import CodeAnalyzer
from file_watcher.state_manager import DatabaseManager
from config.settings import Config
from agents_controller import AgentsController


async def analyze_recent_changes(db_manager):
    """retention period 동안의 변경사항 분석"""
    print(f"\nRetrieving changes from the last {Config.DATA_RETENTION_PERIOD}")
    changes = db_manager.get_recent_changes()

    if not changes:
        print("No changes found to analyze")
        return {"status": "success", "analysis": "변경사항이 없습니다."}

    print(f"Found {len(changes)} changes to analyze")
    analyzer = CodeAnalyzer()
    analysis_result = await analyzer.analyze_changes(changes)

    if analysis_result.get("status") == "success":
        db_manager.save_analysis_results(analysis_result)
    return analysis_result


async def main():
    print("Starting AI analysis...")
    print(f"Data retention period: {Config.DATA_RETENTION_PERIOD}")

    db_manager = DatabaseManager(Config.DB_PATH)
    await db_manager.initialize()

    try:
        # 1. 코드 변경사항 분석
        # analysis_result = await analyze_recent_changes(db_manager)

        # print("\nAnalysis Results:")
        # if analysis_result.get("status") == "success":
        #     print(f"Analysis:\n{analysis_result.get('analysis', 'No analysis available')}")
        # else:
        #     print(f"Error: {analysis_result.get('error', 'Unknown error occurred')}")

        # 2. 에이전트 컨트롤러 호출 → 3개 에이전트 보고서 생성 & 메모리 반영
        controller = AgentsController(Config.DB_PATH)
        await controller.initialize()
        final_report = await controller.generate_daily_report()

        if final_report:
            # final_report를 analysis_results에 추가로 저장
            # 이렇게 하면 send_report.py가 가장 최근 레코드를 이메일로 보낼 수 있음
            db_manager.save_analysis_results({"status": "success", "analysis": final_report})
            print("\nFinal integrated daily report stored in analysis_results.")
        else:
            print("\nNo final report generated from agents.")

    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
