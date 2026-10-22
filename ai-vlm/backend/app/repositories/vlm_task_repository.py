from __future__ import annotations

from datetime import date
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from app.config import Settings


TASK_COLUMNS = (
    "id",
    "vlm_type",
    "create_time",
    "task_tokens",
    "task_accuracy",
    "remarks",
    "task_status",
    "update_time",
)


class VlmRepositoryError(RuntimeError):
    pass


class VlmTaskRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._table_name: str | None = None

    def _connect(self) -> pymysql.Connection:
        if not self.settings.rds_configured:
            raise VlmRepositoryError("RDS 配置不完整")
        if self.settings.rds_engine not in {"mysql", "mariadb"}:
            raise VlmRepositoryError("当前仅支持 MySQL 兼容的 RDS 实例")

        ssl_mode = self.settings.volcengine_rds_ssl_mode.strip().lower()
        ssl = (
            None
            if ssl_mode in {"", "disable", "disabled"}
            else {"check_hostname": False}
        )

        try:
            return pymysql.connect(
                host=self.settings.volcengine_rds_host,
                port=int(self.settings.volcengine_rds_port),
                user=self.settings.volcengine_rds_username,
                password=self.settings.volcengine_rds_password,
                database=self.settings.volcengine_rds_database,
                charset="utf8mb4",
                cursorclass=DictCursor,
                connect_timeout=self.settings.volcengine_rds_connect_timeout,
                read_timeout=10,
                write_timeout=10,
                ssl=ssl,
            )
        except (ValueError, pymysql.MySQLError) as exc:
            raise VlmRepositoryError("无法连接 VLM RDS 数据库") from exc

    def _discover_table(self, connection: pymysql.Connection) -> str:
        if self._table_name is not None:
            return self._table_name

        placeholders = ", ".join(["%s"] * len(TASK_COLUMNS))
        query = f"""
            SELECT TABLE_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND COLUMN_NAME IN ({placeholders})
            GROUP BY TABLE_NAME
            HAVING COUNT(DISTINCT COLUMN_NAME) = %s
            ORDER BY TABLE_NAME
        """
        params = (
            self.settings.volcengine_rds_database,
            *TASK_COLUMNS,
            len(TASK_COLUMNS),
        )

        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                matches = [row["TABLE_NAME"] for row in cursor.fetchall()]
        except pymysql.MySQLError as exc:
            raise VlmRepositoryError("无法读取 VLM 任务表结构") from exc

        if not matches:
            raise VlmRepositoryError("未找到包含 VLM 任务字段的数据表")
        if len(matches) > 1:
            raise VlmRepositoryError("发现多个 VLM 任务数据表，无法确定唯一数据源")

        self._table_name = matches[0]
        return self._table_name

    def list_tasks(self, page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
        connection = self._connect()
        try:
            table_name = self._discover_table(connection)
            escaped_table = f"`{table_name.replace('`', '``')}`"
            offset = (page - 1) * page_size
            columns = ", ".join(f"`{column}`" for column in TASK_COLUMNS)

            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) AS total FROM {escaped_table}")
                total = int(cursor.fetchone()["total"])
                cursor.execute(
                    f"""
                        SELECT {columns}
                        FROM {escaped_table}
                        ORDER BY `create_time` DESC, `id` DESC
                        LIMIT %s OFFSET %s
                    """,
                    (page_size, offset),
                )
                rows = list(cursor.fetchall())
        except pymysql.MySQLError as exc:
            raise VlmRepositoryError("读取 VLM 任务数据失败") from exc
        finally:
            connection.close()

        return rows, total

    def get_task_overview(
        self,
        start_date: date,
        end_date: date,
    ) -> tuple[int, dict[date, int]]:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        SELECT COUNT(*) AS total
                        FROM `vlm_tasks_list`
                        WHERE COALESCE(`is_deleted`, 0) <> 1
                    """
                )
                total = int(cursor.fetchone()["total"])
                cursor.execute(
                    """
                        SELECT DATE(`create_time`) AS task_date, COUNT(*) AS total
                        FROM `vlm_tasks_list`
                        WHERE COALESCE(`is_deleted`, 0) <> 1
                          AND `create_time` >= %s
                          AND `create_time` < %s
                        GROUP BY DATE(`create_time`)
                        ORDER BY task_date
                    """,
                    (start_date, end_date),
                )
                daily_counts = {
                    row["task_date"]: int(row["total"])
                    for row in cursor.fetchall()
                }
        except pymysql.MySQLError as exc:
            raise VlmRepositoryError("读取 VLM 总览数据失败") from exc
        finally:
            connection.close()

        return total, daily_counts
