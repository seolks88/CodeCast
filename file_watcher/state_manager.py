# file_watcher/state_manager.py

import sqlite3
from datetime import datetime, timezone, timedelta
import difflib
import os
from config.settings import Config
from file_watcher.differ import FileChangeHandler
import aiosqlite


class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.KST = timezone(timedelta(hours=9))
        self._initialized = False

    async def initialize(self):
        """데이터베이스 초기화를 수행합니다."""
        if not self._initialized:
            await self._setup_database()
            self._initialized = True
            print("Database initialized successfully")

    async def _setup_database(self):
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON;")
            await conn.executescript("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL UNIQUE,
                    file_hash TEXT NOT NULL,
                    content BLOB,
                    created_at TEXT DEFAULT (datetime('now')),
                    modified_at TEXT DEFAULT (datetime('now')),
                    last_updated TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS file_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER UNIQUE,
                    diff BLOB NOT NULL,
                    change_time TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
                );
            """)

    def _get_current_time(self):
        """현재 KST 시간을 ISO 형식 문자열로 반환합니다."""
        return datetime.now(self.KST).isoformat()

    def _parse_db_time(self, time_str):
        """데이터베이스의 시간 문자열을 datetime 객체로 변환합니다."""
        return datetime.fromisoformat(time_str)

    async def cleanup_old_data(self):
        """오래된 데이터를 정리합니다."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON;")
            current_time = self._get_current_time()
            retention_period = Config.DATA_RETENTION_PERIOD
            cutoff_time = (datetime.now(self.KST) - retention_period).isoformat()

            print(f"Current KST time: {current_time}")
            print(f"Data retention cutoff time: {cutoff_time}")

            try:
                # 1. 오래된 file_changes 삭제
                cursor = await conn.execute("DELETE FROM file_changes WHERE change_time < ?", (cutoff_time,))
                deleted_changes = cursor.rowcount
                print(f"Deleted {deleted_changes} old file_changes entries")

                # 2. retention period가 지난 files 처리
                cursor = await conn.execute(
                    """
                    SELECT id, file_path, last_updated 
                    FROM files 
                    WHERE last_updated < ?
                    """,
                    (cutoff_time,),
                )
                outdated_files = await cursor.fetchall()

                handler = FileChangeHandler(self)

                for file_id, file_path, last_updated in outdated_files:
                    if os.path.exists(file_path):
                        # 현재 파일 상태 읽기
                        file_info = await handler.get_file_info(file_path)
                        if file_info:
                            # files 테이블 업데이트
                            await conn.execute(
                                """
                                UPDATE files 
                                SET content = ?, 
                                    file_hash = ?,
                                    last_updated = ?
                                WHERE id = ?
                                """,
                                (file_info["content"], file_info["hash"], current_time, file_id),
                            )
                            print(f"Updated content for file: {file_path}")
                    else:
                        # 파일이 존재하지 않는 경우 files 테이블에서 삭제
                        await conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
                        print(f"Deleted record for non-existent file: {file_path}")

                await conn.commit()
                print("Cleanup completed successfully")

            except Exception as e:
                print(f"Error during cleanup: {str(e)}")
                import traceback

                traceback.print_exc()

    async def handle_file_change(self, file_path, file_info):
        """파일 변경을 비동기적으로 처리합니다."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON;")
            try:
                existing = await self._get_existing_file(conn, file_path)
                current_time = self._get_current_time()

                if existing:
                    await self._handle_existing_file(conn, existing, file_info, current_time)
                else:
                    await self._handle_new_file(conn, file_path, file_info, current_time)

                await conn.commit()

            except Exception as e:
                print(f"Error processing database task: {e}")
                import traceback

                traceback.print_exc()

    async def _get_existing_file(self, conn, file_path):
        """기존 파일 정보를 조회합니다."""
        cursor = await conn.cursor()
        await cursor.execute("SELECT id, content, file_hash, last_updated FROM files WHERE file_path = ?", (file_path,))
        return await cursor.fetchone()

    async def _handle_existing_file(self, conn, existing, file_info, current_time):
        """기존 파일의 변경사항을 처리합니다."""
        file_id, old_content, old_hash, last_updated = existing
        new_content = file_info["content"]
        new_hash = file_info["hash"]

        print(f"Found existing file record. Old hash: {old_hash}, New hash: {new_hash}")

        retention_period = Config.DATA_RETENTION_PERIOD
        time_since_last_update = (datetime.now(self.KST) - self._parse_db_time(last_updated)).total_seconds()

        if time_since_last_update >= retention_period.total_seconds():
            await self._update_after_retention_period(conn, file_id, new_hash, new_content, current_time)
        else:
            if new_hash != old_hash:
                print("File content changed within retention period, updating file_changes only.")
                old_content = old_content or b""
                new_content = new_content or b""

                diff = self._generate_diff(old_content, new_content)
                if diff and diff.strip():
                    await self._update_file_changes(conn, file_id, diff, current_time)
                    # 변경사항이 있을 때만 last_updated 업데이트
                    cursor = await conn.cursor()
                    await cursor.execute(
                        """
                        UPDATE files 
                        SET last_updated = ?
                        WHERE id = ?
                        """,
                        (current_time, file_id),
                    )
                else:
                    print("No actual content changes detected")
            else:
                print("File hash unchanged; no action taken.")

    async def _update_after_retention_period(self, conn, file_id, new_hash, new_content, current_time):
        """보존 기간이 지난 후 파일 업데이트를 처리합니다."""
        cursor = await conn.cursor()
        await cursor.execute("SELECT file_hash FROM files WHERE id = ?", (file_id,))
        result = await cursor.fetchone()
        current_hash = result[0] if result else None

        if current_hash != new_hash:
            print("Content changed after retention period. Updating the file record.")
            await cursor.execute(
                """
                UPDATE files 
                SET file_hash = ?, 
                    content = ?, 
                    modified_at = ?, 
                    last_updated = ?
                WHERE id = ?
                """,
                (new_hash, new_content, current_time, current_time, file_id),
            )
        else:
            print("No changes detected after retention period.")

    async def _update_file_changes(self, conn, file_id, diff, current_time):
        """file_changes 테이블을 업데이트합니다."""
        if diff:
            print(f"Updating file changes with diff of length {len(diff)} bytes")
            cursor = await conn.cursor()
            await cursor.execute(
                """
                INSERT OR REPLACE INTO file_changes (file_id, diff, change_time)
                VALUES (?, ?, ?)
                """,
                (file_id, diff, current_time),
            )

    async def _handle_new_file(self, conn, file_path, file_info, current_time):
        """새로운 파일을 처리합니다."""
        print("New file detected, adding to database...")
        new_content = file_info["content"] or b""

        # 새 파일 등록 시에는 전체 내용을 diff로 저장
        diff = self._generate_initial_diff(new_content)

        cursor = await conn.cursor()
        await cursor.execute(
            """
            INSERT INTO files (file_path, file_hash, content, created_at, modified_at, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (file_path, file_info["hash"], new_content, current_time, current_time, current_time),
        )
        file_id = cursor.lastrowid

        if diff:
            await self._update_file_changes(conn, file_id, diff, current_time)

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

    def update_last_checked(self, file_path):
        """파일의 마지막 검사 시간을 업데이트합니다."""
        conn = sqlite3.connect(self.db_path)
        try:
            current_time = self._get_current_time()
            conn.execute(
                """
                UPDATE files 
                SET last_updated = ?
                WHERE file_path = ?
                """,
                (current_time, file_path),
            )
            conn.commit()
            print(f"Updated last_checked time for {file_path} to {current_time}")
        except Exception as e:
            print(f"Error updating last_checked time: {e}")
        finally:
            conn.close()

    def get_recent_changes(self):
        """최근 변경사항 조회"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.file_path, fc.diff, fc.change_time
                FROM file_changes fc
                JOIN files f ON f.id = fc.file_id
                WHERE fc.change_time > datetime('now', '-1 day')
                ORDER BY fc.change_time DESC
            """)

            changes = []
            for row in cursor.fetchall():
                changes.append({"file_path": row[0], "diff": row[1].decode("utf-8"), "change_time": row[2]})
            return changes
        finally:
            conn.close()

    def save_analysis_results(self, result):
        """Save the analysis results and maintain only the most recent N records"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            # 테이블이 없을 때만 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)

            if result["status"] == "success":
                # 새로운 분석 결과 삽입
                cursor.execute(
                    """
                    INSERT INTO analysis_results (analysis)
                    VALUES (?)
                    """,
                    (result["analysis"],),
                )

                # 오래된 레코드 삭제 (최신 N개만 유지)
                cursor.execute(
                    """
                    DELETE FROM analysis_results 
                    WHERE id NOT IN (
                        SELECT id 
                        FROM analysis_results 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    )
                """,
                    (Config.MAX_ANALYSIS_RECORDS,),
                )

            conn.commit()
        finally:
            conn.close()
