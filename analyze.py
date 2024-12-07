# analyze.py
import asyncio
from file_watcher.state_manager import DatabaseManager
from config.settings import Config
from agents_controller import AgentsController


async def main():
    print("Starting AI analysis...")
    print(f"Data retention period: {Config.DATA_RETENTION_PERIOD}")

    db_manager = DatabaseManager(Config.DB_PATH)
    await db_manager.initialize()

    try:
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
