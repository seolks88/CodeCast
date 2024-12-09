import asyncio
import traceback
from file_watcher.state_manager import DatabaseManager
from config.settings import Config
from agents_controller import AgentsController


async def main():
    """메인 실행 함수: DB 초기화 -> 일일 리포트 생성 -> 결과 저장 순서로 진행."""
    print("Starting AI analysis...")
    print(f"Data retention period: {Config.DATA_RETENTION_PERIOD}")

    db_manager = DatabaseManager(Config.DB_PATH)
    await db_manager.initialize()

    try:
        controller = AgentsController(Config.DB_PATH)
        await controller.initialize()

        final_report = await controller.generate_daily_report()
        handle_analysis_result(db_manager, final_report)
    except Exception as e:
        print(f"Unexpected error during analysis: {e}")
        traceback.print_exc()


def handle_analysis_result(db_manager: DatabaseManager, report: str):
    """일일 리포트 분석 결과를 DB에 저장하고 사용자에게 피드백을 제공한다."""
    if report:
        db_manager.save_analysis_results({"status": "success", "analysis": report})
        print("Final integrated daily report stored in analysis_results.")
    else:
        print("No final report generated from agents.")


if __name__ == "__main__":
    asyncio.run(main())
