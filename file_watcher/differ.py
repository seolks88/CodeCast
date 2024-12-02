# file_watcher/differ.py

import hashlib
import os
import platform
import aiofiles


class FileChangeHandler:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.is_windows = platform.system() == "Windows"

    async def get_file_info(self, file_path):
        """파일 정보를 비동기적으로 추출합니다."""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None

        try:
            async with aiofiles.open(file_path, mode="rb") as f:
                content = await f.read()
                print(f"Read binary file content: {file_path}")
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            content = b""

        file_stat = os.stat(file_path)
        file_hash = await self._calculate_file_hash(file_path)

        return {
            "size": file_stat.st_size,
            "mtime": file_stat.st_mtime,
            "hash": file_hash,
            "content": content,
        }

    async def check_file(self, file_path):
        """파일 변경을 비동기적으로 확인하고 처리합니다."""
        print(f"\nChecking file: {file_path}")
        file_info = await self.get_file_info(file_path)
        if file_info:
            await self.db_manager.handle_file_change(file_path, file_info)

    async def _calculate_file_hash(self, file_path):
        """파일의 SHA-256 해시를 계산합니다."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return ""
