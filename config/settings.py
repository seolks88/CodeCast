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
    DATA_RETENTION_PERIOD = timedelta(seconds=retention_minutes)

    # 데이터베이스 파일 경로 (고정값 사용)
    DB_PATH = BASE_DIR / "file_history.db"  # 과거엔 사용, 지금은 사용 안할수도

    # 최대 분석 결과 보관 개수 (기본값 10)
    MAX_ANALYSIS_RECORDS = int(os.getenv("CODECAST_MAX_ANALYSIS_RECORDS", "10").strip())

    # Email settings
    SMTP_SERVER = os.getenv("CODECAST_SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("CODECAST_SMTP_PORT", "587"))
    SENDER_EMAIL = os.getenv("CODECAST_SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("CODECAST_SENDER_PASSWORD")
    RECIPIENT_EMAIL = os.getenv("CODECAST_RECIPIENT_EMAIL")

    DEFAULT_LLM_MODEL = os.getenv("CODECAST_DEFAULT_LLM_MODEL", "gpt-4o-mini")

    # 기본 지원 파일 확장자 (사용자가 .env에서 수정 가능)
    # 기본 지원 파일 확장자 (사용자가 .env에서 수정 가능)
    DEFAULT_SUPPORTED_EXTENSIONS = {
        # 일반적인 프로그래밍 언어
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",  # Python, JavaScript, TypeScript
        ".java",
        ".kt",
        ".scala",  # JVM 기반 언어
        ".c",
        ".cpp",
        ".h",
        ".hpp",  # C/C++
        ".cs",  # C#
        ".go",  # Go
        ".rb",  # Ruby
        ".php",  # PHP
        ".swift",  # Swift
        ".r",
        ".R",  # R
        ".m",
        ".mm",  # Objective-C
        # 웹 관련
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        # 설정 파일
        ".json",
        ".yml",
        ".yaml",
        ".xml",
        ".toml",
        # 쉘 스크립트
        ".sh",
        ".bash",
        ".zsh",
        # 기타 텍스트 파일
        ".md",
        ".txt",
        ".csv",
    }

    # 환경변수에서 지원 확장자 가져오기
    SUPPORTED_EXTENSIONS = set(
        os.getenv("CODECAST_SUPPORTED_EXTENSIONS", ",".join(DEFAULT_SUPPORTED_EXTENSIONS)).split(",")
    )

    # 무시할 디렉토리 패턴 (예측 가능한 순서를 위해 리스트 사용)
    DEFAULT_IGNORE_PATTERNS = [
        "node_modules",
        "venv",
        "env",
        ".git",
        "__pycache__",
        "build",
        "dist",
        ".idea",
        ".vscode",
        "coverage",
        "merge",
    ]

    # 환경변수에서 무시할 디렉토리 패턴 가져오기
    env_ignore_patterns = os.getenv("CODECAST_IGNORE_PATTERNS")
    if env_ignore_patterns:
        IGNORE_PATTERNS = set(pattern.strip() for pattern in env_ignore_patterns.split(",") if pattern.strip())
    else:
        IGNORE_PATTERNS = set(DEFAULT_IGNORE_PATTERNS)

    # Voyage, Cohere API 키 설정
    VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")

    # 토픽 선택기 최대 재시도 횟수 (중복 주제 발생시 재시도, 모든 시도 실패시 복습 모드로 전환)
    TOPIC_SELECTOR_MAX_RETRIES = int(os.getenv("TOPIC_SELECTOR_MAX_RETRIES", "1"))

    # OpenAI API 키 추가
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # gRPC 관련 환경 변수 설정
    os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "false"
    os.environ["GRPC_POLL_STRATEGY"] = "epoll1"
    os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
