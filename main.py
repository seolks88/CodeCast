# main.py
import os
import sys
import asyncio
from file_watcher.differ import FileChangeHandler
from file_watcher.state_manager import DatabaseManager
from config.settings import Config


def is_subdirectory(path1, path2):
    """path1이 path2의 하위 디렉토리인지 또는 같은 디렉토리인지 확인"""
    path1 = os.path.abspath(path1)
    path2 = os.path.abspath(path2)
    return path1.startswith(path2)


def get_unique_directories(directories):
    """중복되지 않는 디렉토리 목록을 반환합니다."""
    # 절대 경로로 변환하고 정렬 (긴 경로가 먼저 오도록)
    abs_dirs = [os.path.abspath(d) for d in directories]
    sorted_dirs = sorted(abs_dirs, key=len, reverse=True)

    unique_dirs = []
    for current_dir in sorted_dirs:
        # 이미 포함된 상위 디렉토리가 있는지 확인
        is_subdirectory_of_existing = any(is_subdirectory(current_dir, existing_dir) for existing_dir in unique_dirs)
        if not is_subdirectory_of_existing:
            unique_dirs.append(current_dir)

    return unique_dirs


async def scan_directory(directory, db_manager):
    """디렉토리 내 모든 파일을 비동기적으로 스캔합니다."""
    try:
        print(f"Starting scan of directory: {directory}")
        handler = FileChangeHandler(db_manager)

        scan_tasks = []
        for root, _, files in os.walk(directory):
            for filename in files:
                try:
                    file_path = os.path.join(root, filename)
                    print(f"Processing file: {file_path}")
                    scan_tasks.append(handler.check_file(file_path))
                except Exception as e:
                    print(f"Error processing {filename}: {e}")

        await asyncio.gather(*scan_tasks)
        print("Scan completed successfully")
    except Exception as e:
        print(f"Error during directory scan: {e}")
        sys.exit(1)


async def main():
    unique_dirs = get_unique_directories(Config.WATCH_DIRECTORIES)

    for watch_dir in unique_dirs:
        if not os.path.exists(watch_dir):
            try:
                os.makedirs(watch_dir)
                print(f"Created watch directory at {watch_dir}")
            except Exception as e:
                print(f"Error creating directory {watch_dir}: {e}")
                sys.exit(1)

    print("Starting scan of directories")
    print(f"Data retention period: {Config.DATA_RETENTION_PERIOD}")
    print(f"Directories to scan: {unique_dirs}")

    db_manager = DatabaseManager(Config.DB_PATH)
    await db_manager.initialize()

    for watch_dir in unique_dirs:
        print(f"\nProcessing directory: {watch_dir}")
        await scan_directory(watch_dir, db_manager)

    await db_manager.cleanup_old_data()
    print("All directory scans completed")


if __name__ == "__main__":
    asyncio.run(main())
