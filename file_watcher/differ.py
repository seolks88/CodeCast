# file_watcher/differ.py

import hashlib
import os
import platform
import aiofiles
import difflib
import asyncio
import sys

from config.settings import Config


class FileChangeHandler:
    def __init__(self):
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

    async def check_file(self, file_path, db_manager):
        """파일 변경을 비동기적으로 확인하고 변경사항 데이터와 diff를 반환합니다."""
        if not self._should_process_file(file_path):
            return None

        print(f"\nChecking file: {file_path}")
        file_info = await self.get_file_info(file_path)
        if file_info:
            # 기존 파일 정보 가져오기
            existing_info = await db_manager.get_file_info(file_path)
            if existing_info:
                old_content = existing_info["content"]
                diff = self._generate_diff(old_content, file_info["content"])
            else:
                # 새로운 파일의 경우 전체 내용을 diff로 간주
                diff = self._generate_initial_diff(file_info["content"])

            return file_path, file_info, diff
        else:
            return None

    async def _calculate_file_hash(self, file_path):
        """파일의 SHA-256 해시를 계산합니다."""
        hasher = hashlib.sha256()
        try:
            async with aiofiles.open(file_path, "rb") as f:
                while True:
                    chunk = await f.read(4096)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Error calculating hash for {file_path}: {e}")
            return ""

    def _generate_initial_diff(self, new_content):
        """새로운 파일의 전체 내용에 대한 diff를 생성합니다."""
        try:
            new_text = new_content.decode("utf-8", errors="ignore")
            diff_text = f"+{new_text}"  # 새로운 내용 전체를 추가된 것으로 표시
            return diff_text.encode("utf-8")
        except Exception as e:
            print(f"Error generating initial diff: {e}")
            return None

    def _generate_diff(self, old_content, new_content):
        """old_content와 new_content 간의 실제 변경사항에 대한 diff만 생성합니다."""
        try:
            old_text = old_content.decode("utf-8", errors="ignore")
            new_text = new_content.decode("utf-8", errors="ignore")

            # 실제 변경사항이 있는지 확인
            if old_text == new_text:
                return None

            old_lines = old_text.splitlines()
            new_lines = new_text.splitlines()

            diff_generator = difflib.unified_diff(old_lines, new_lines, fromfile="before", tofile="after", lineterm="")

            diff_lines = list(diff_generator)
            if not diff_lines:  # 실제 변경사항이 없는 경우
                return None

            diff_text = "\n".join(diff_lines)
            return diff_text.encode("utf-8")
        except Exception as e:
            print(f"Error generating diff: {e}")
            return None

    def _should_process_file(self, file_path):
        """파일을 처리해야 하는지 확인"""
        # 절대 경로로 변환
        abs_path = os.path.abspath(file_path)

        # 무시할 디렉토리 패턴 확인
        path_parts = abs_path.split(os.sep)
        for ignore_pattern in Config.IGNORE_PATTERNS:
            if ignore_pattern in path_parts:
                print(f"Ignoring file in {ignore_pattern}: {abs_path}")
                return False

        # 파일 확장자 확인
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in Config.SUPPORTED_EXTENSIONS:
            return False

        return True

    def _should_ignore_directory(self, dir_path):
        """디렉토리를 무시해야 하는지 확인"""
        path_parts = dir_path.split(os.sep)
        return any(pattern in path_parts for pattern in Config.IGNORE_PATTERNS)

    async def scan_directory(self, directory, db_manager):
        """디렉토리 내 모든 파일을 비동기적으로 스캔합니다."""
        try:
            print(f"Starting scan of directory: {directory}")
            scan_tasks = []

            for root, dirs, files in os.walk(directory, topdown=True):
                # 무시할 디렉토리 필터링 (dirs를 직접 수정)
                dirs[:] = [d for d in dirs if not self._should_ignore_directory(os.path.join(root, d))]

                for filename in files:
                    file_path = os.path.join(root, filename)
                    if self._should_process_file(file_path):
                        scan_tasks.append(self.check_file(file_path, db_manager))

            results = await asyncio.gather(*scan_tasks)
            for result in results:
                if result:
                    file_path, file_info, diff = result
                    await db_manager.save_file_change(file_path, file_info, diff)

            print("Scan completed successfully")
        except Exception as e:
            print(f"Error during directory scan: {e}")
            sys.exit(1)
