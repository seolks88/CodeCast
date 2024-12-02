# file_watcher/state_manager.py

import sqlite3
from datetime import datetime, timezone, timedelta
import os
from config.settings import Config
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

                for file_id, file_path, last_updated in outdated_files:
                    if os.path.exists(file_path):
                        # 파일이 존재하는 경우 last_updated만 업데이트
                        await conn.execute(
                            """
                            UPDATE files 
                            SET last_updated = ?
                            WHERE id = ?
                            """,
                            (current_time, file_id),
                        )
                        print(f"Updated last_updated for file: {file_path}")
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

    async def save_file_change(self, file_path, file_info, diff):
        """파일 변경사항과 diff를 데이터베이스에 저장합니다."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON;")
            try:
                # 파일 존재 여부 확인
                cursor = await conn.execute("SELECT id, file_hash FROM files WHERE file_path = ?", (file_path,))
                existing = await cursor.fetchone()
                current_time = self._get_current_time()

                if existing:
                    file_id, old_hash = existing
                    new_hash = file_info["hash"]

                    if old_hash != new_hash:
                        # 먼저 변경사항 저장
                        await self._update_file_changes(conn, file_id, diff, current_time)

                        # 그 다음 files 테이블 업데이트
                        await conn.execute(
                            """
                            UPDATE files 
                            SET file_hash = ?, content = ?, modified_at = ?, last_updated = ?
                            WHERE id = ?
                            """,
                            (new_hash, file_info["content"], current_time, current_time, file_id),
                        )
                else:
                    # 새로운 파일인 경우 먼저 files 테이블에 기본 레코드 생성
                    await conn.execute(
                        """
                        INSERT INTO files (file_path, file_hash, content, created_at, modified_at, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (file_path, file_info["hash"], file_info["content"], current_time, current_time, current_time),
                    )

                    # 파일 ID 가져오기
                    cursor = await conn.execute("SELECT id FROM files WHERE file_path = ?", (file_path,))
                    file_id = (await cursor.fetchone())[0]

                    # 변경사항 저장
                    await self._update_file_changes(conn, file_id, diff, current_time)

                await conn.commit()

            except Exception as e:
                print(f"Error saving file change: {e}")

    async def _update_file_changes(self, conn, file_id, diff, current_time):
        """file_changes 테이블을 업데이트합니다."""
        if diff:
            print(f"Updating file changes with diff of length {len(diff)} bytes")
            await conn.execute(
                """
                INSERT OR REPLACE INTO file_changes (file_id, diff, change_time)
                VALUES (?, ?, ?)
                """,
                (file_id, diff, current_time),
            )

    async def get_file_info(self, file_path):
        """파일의 기존 정보를 가져옵니다."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA foreign_keys = ON;")
            cursor = await conn.execute("SELECT content FROM files WHERE file_path = ?", (file_path,))
            result = await cursor.fetchone()
            if result:
                return {"content": result[0]}
            else:
                return None

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
        """분석 결과를 저장하고, 최신 N개의 레코드만 유지합니다."""
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
