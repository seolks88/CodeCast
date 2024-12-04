# main.py
import os
import sys
import asyncio
from file_watcher.differ import FileChangeHandler
from file_watcher.state_manager import DatabaseManager
from config.settings import Config


def is_subdirectory(path1, path2):
    """Check if path1 is a subdirectory of path2 or the same directory."""
    path1 = os.path.abspath(path1)
    path2 = os.path.abspath(path2)
    return path1.startswith(path2)


def get_unique_directories(directories):
    """Return a list of unique directories without duplicates."""
    abs_dirs = [os.path.abspath(d) for d in directories]
    sorted_dirs = sorted(abs_dirs, key=len, reverse=True)

    unique_dirs = []
    for current_dir in sorted_dirs:
        is_subdirectory_of_existing = any(is_subdirectory(current_dir, existing_dir) for existing_dir in unique_dirs)
        if not is_subdirectory_of_existing:
            unique_dirs.append(current_dir)

    return unique_dirs


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

    handler = FileChangeHandler()

    for watch_dir in unique_dirs:
        print(f"\nProcessing directory: {watch_dir}")
        await handler.scan_directory(watch_dir, db_manager)

    await db_manager.cleanup_old_data()
    print("All directory scans completed")


if __name__ == "__main__":
    asyncio.run(main())
