import asyncio
import os
from datetime import datetime
import importlib.util
import sys


async def run_file_scanner():
    print("\n=== 파일 스캔 시작 ===")
    try:
        scanner = importlib.import_module("file_scanner")
        await scanner.main()
    except Exception as e:
        print(f"파일 스캔 중 오류 발생: {e}")
        sys.exit(1)


async def run_report_workflow():
    print("\n=== 리포트 생성 시작 ===")
    try:
        workflow = importlib.import_module("report_workflow")
        await workflow.run_graph()
    except Exception as e:
        print(f"리포트 생성 중 오류 발생: {e}")
        sys.exit(1)


async def run_send_report():
    print("\n=== 이메일 발송 시작 ===")
    try:
        sender = importlib.import_module("send_report")
        await sender.main()
    except Exception as e:
        print(f"이메일 발송 중 오류 발생: {e}")
        sys.exit(1)


async def main():
    start_time = datetime.now()
    print(f"작업 시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 순차적으로 실행
        await run_file_scanner()
        await run_report_workflow()
        await run_send_report()

        end_time = datetime.now()
        duration = end_time - start_time
        print(f"\n=== 전체 작업 완료 ===")
        print(f"소요 시간: {duration}")
        print(f"완료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
