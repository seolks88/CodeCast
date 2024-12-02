# config/settings.py
import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    # 메인 프로그램의 위치를 기준으로 경로 설정
    BASE_DIR = Path(__file__).parent.parent

    # 환경변수에서 감시 디렉토리 가져오기
    WATCH_DIRECTORIES = os.getenv("CODECAST_WATCH_DIRS", "").split(",")
    if not WATCH_DIRECTORIES or WATCH_DIRECTORIES == [""]:
        WATCH_DIRECTORIES = [str(BASE_DIR / "watched_directory")]

    # 환경변수에서 보관 기간 가져오기 (기본값 1분)
    retention_minutes = int(os.getenv("CODECAST_RETENTION_MINUTES", "1"))
    DATA_RETENTION_PERIOD = timedelta(minutes=retention_minutes)

    # 데이터베이스 파일 경로 (고정값 사용)
    DB_PATH = BASE_DIR / "file_history.db"

    # 최대 분석 결과 보관 개수 (기본값 10)
    MAX_ANALYSIS_RECORDS = int(os.getenv("CODECAST_MAX_ANALYSIS_RECORDS", "10"))
