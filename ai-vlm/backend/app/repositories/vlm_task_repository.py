from __future__ import annotations

from datetime import date
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from app.config import Settings


TASK_COLUMNS = (
    "id",
    "prompt_id",
    "task_input",
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


class VlmPromptNotFoundError(VlmRepositoryError):
    pass


class VlmTaskPromptUnavailableError(VlmRepositoryError):
    pass


class VlmTaskNotFoundError(VlmRepositoryError):
    pass


class VlmTaskExecutionUnavailableError(VlmRepositoryError):
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
            columns = ", ".join(f"task.`{column}`" for column in TASK_COLUMNS)

            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                        SELECT COUNT(*) AS total
                        FROM {escaped_table} AS task
                        WHERE COALESCE(task.`is_deleted`, 0) <> 1
                    """
                )
                total = int(cursor.fetchone()["total"])
                cursor.execute(
                    f"""
                        SELECT {columns}, prompt.`title` AS `prompt_title`
                        FROM {escaped_table} AS task
                        LEFT JOIN `vlm_prompt` AS prompt
                          ON prompt.`id` = task.`prompt_id`
                        WHERE COALESCE(task.`is_deleted`, 0) <> 1
                        ORDER BY task.`create_time` DESC, task.`id` DESC
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

    def list_task_items(
        self,
        *,
        task_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        connection = self._connect()
        try:
            offset = (page - 1) * page_size
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        SELECT `id`
                        FROM `vlm_tasks_list`
                        WHERE `id` = %s
                          AND COALESCE(`is_deleted`, 0) <> 1
                    """,
                    (task_id,),
                )
                if cursor.fetchone() is None:
                    raise VlmTaskNotFoundError("任务不存在")

                cursor.execute(
                    """
                        SELECT COUNT(*) AS total
                        FROM `vlm_tasks_item`
                        WHERE `task_id` = %s
                    """,
                    (task_id,),
                )
                total = int(cursor.fetchone()["total"])
                cursor.execute(
                    """
                        SELECT
                            `id`,
                            `task_id`,
                            `model_id`,
                            `task_input`,
                            `total_tokens`,
                            `input_tokens`,
                            `output_tokens`,
                            `cached_tokens`,
                            `task_status`,
                            `output_text`
                        FROM `vlm_tasks_item`
                        WHERE `task_id` = %s
                        ORDER BY `id` DESC
                        LIMIT %s OFFSET %s
                    """,
                    (task_id, page_size, offset),
                )
                rows = list(cursor.fetchall())
        except VlmTaskNotFoundError:
            raise
        except pymysql.MySQLError as exc:
            raise VlmRepositoryError("读取 VLM 任务明细失败") from exc
        finally:
            connection.close()

        return rows, total

    def get_task_execution_context(self, task_id: int) -> dict[str, Any]:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        SELECT
                            task.`id` AS `task_id`,
                            task.`prompt_id`,
                            prompt.`title` AS `prompt_title`,
                            prompt.`content` AS `prompt_content`,
                            task.`task_input`
                        FROM `vlm_tasks_list` AS task
                        LEFT JOIN `vlm_prompt` AS prompt
                          ON prompt.`id` = task.`prompt_id`
                        WHERE task.`id` = %s
                          AND COALESCE(task.`is_deleted`, 0) <> 1
                    """,
                    (task_id,),
                )
                row = cursor.fetchone()
        except pymysql.MySQLError as exc:
            raise VlmRepositoryError("读取任务执行上下文失败") from exc
        finally:
            connection.close()

        if row is None:
            raise VlmTaskNotFoundError("任务不存在")
        if (
            row["prompt_id"] is None
            or not row["prompt_content"]
            or not row["task_input"]
        ):
            raise VlmTaskExecutionUnavailableError(
                "任务缺少提示词模版或任务输入"
            )
        return row

    def create_task_item(
        self,
        *,
        task_id: int,
        model_id: str,
        task_input: str,
        total_tokens: int | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cached_tokens: int | None,
        task_status: int,
        output_text: str,
    ) -> dict[str, Any]:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        INSERT INTO `vlm_tasks_item` (
                            `task_id`,
                            `model_id`,
                            `task_input`,
                            `total_tokens`,
                            `input_tokens`,
                            `output_tokens`,
                            `cached_tokens`,
                            `task_status`,
                            `output_text`
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        task_id,
                        model_id,
                        task_input,
                        total_tokens,
                        input_tokens,
                        output_tokens,
                        cached_tokens,
                        task_status,
                        output_text,
                    ),
                )
                item_id = int(cursor.lastrowid)
            connection.commit()
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise VlmRepositoryError("保存 VLM 任务执行结果失败") from exc
        finally:
            connection.close()

        return {
            "id": item_id,
            "task_id": task_id,
            "model_id": model_id,
            "task_input": task_input,
            "total_tokens": total_tokens,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "task_status": task_status,
            "output_text": output_text,
        }

    def create_task(
        self,
        *,
        prompt_id: int,
        task_type: str,
        task_input: str,
        remarks: str,
    ) -> int:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        SELECT `vlm_type`, `is_closed`
                        FROM `vlm_prompt`
                        WHERE `id` = %s
                        FOR UPDATE
                    """,
                    (prompt_id,),
                )
                prompt = cursor.fetchone()
                if (
                    prompt is None
                    or bool(prompt["is_closed"])
                    or prompt["vlm_type"] != task_type
                ):
                    raise VlmTaskPromptUnavailableError(
                        "请选择同类型的可用提示词模版"
                    )

                cursor.execute(
                    """
                        INSERT INTO `vlm_tasks_list` (
                            `prompt_id`,
                            `task_input`,
                            `vlm_type`,
                            `create_time`,
                            `task_tokens`,
                            `task_accuracy`,
                            `remarks`,
                            `task_status`,
                            `is_deleted`,
                            `update_time`
                        )
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 0, 0, %s, 0, 0, NULL)
                    """,
                    (prompt_id, task_input, task_type, remarks),
                )
                task_id = int(cursor.lastrowid)
            connection.commit()
        except VlmTaskPromptUnavailableError:
            connection.rollback()
            raise
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise VlmRepositoryError("创建 VLM 任务失败") from exc
        finally:
            connection.close()

        return task_id

    def update_task(
        self,
        task_id: int,
        *,
        prompt_id: int,
        task_type: str,
        task_input: str,
        remarks: str,
        task_status: int,
    ) -> None:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        SELECT `prompt_id`
                        FROM `vlm_tasks_list`
                        WHERE `id` = %s
                          AND COALESCE(`is_deleted`, 0) <> 1
                        FOR UPDATE
                    """,
                    (task_id,),
                )
                task = cursor.fetchone()
                if task is None:
                    raise VlmTaskNotFoundError("任务不存在")

                cursor.execute(
                    """
                        SELECT `vlm_type`, `is_closed`
                        FROM `vlm_prompt`
                        WHERE `id` = %s
                        FOR UPDATE
                    """,
                    (prompt_id,),
                )
                prompt = cursor.fetchone()
                prompt_changed = prompt_id != task["prompt_id"]
                if (
                    prompt is None
                    or prompt["vlm_type"] != task_type
                    or (bool(prompt["is_closed"]) and prompt_changed)
                ):
                    raise VlmTaskPromptUnavailableError(
                        "请选择同类型的可用提示词模版"
                    )

                cursor.execute(
                    """
                        UPDATE `vlm_tasks_list`
                        SET
                            `prompt_id` = %s,
                            `task_input` = %s,
                            `vlm_type` = %s,
                            `remarks` = %s,
                            `task_status` = %s,
                            `update_time` = CASE
                                WHEN %s = 2
                                THEN COALESCE(`update_time`, CURRENT_TIMESTAMP)
                                ELSE NULL
                            END
                        WHERE `id` = %s
                          AND COALESCE(`is_deleted`, 0) <> 1
                    """,
                    (
                        prompt_id,
                        task_input,
                        task_type,
                        remarks,
                        task_status,
                        task_status,
                        task_id,
                    ),
                )
            connection.commit()
        except (VlmTaskNotFoundError, VlmTaskPromptUnavailableError):
            connection.rollback()
            raise
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise VlmRepositoryError("更新 VLM 任务失败") from exc
        finally:
            connection.close()

    def delete_task(self, task_id: int) -> None:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        UPDATE `vlm_tasks_list`
                        SET
                            `is_deleted` = 1,
                            `update_time` = CURRENT_TIMESTAMP
                        WHERE `id` = %s
                          AND COALESCE(`is_deleted`, 0) <> 1
                    """,
                    (task_id,),
                )
                if not cursor.rowcount:
                    raise VlmTaskNotFoundError("任务不存在")
            connection.commit()
        except VlmTaskNotFoundError:
            connection.rollback()
            raise
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise VlmRepositoryError("删除 VLM 任务失败") from exc
        finally:
            connection.close()

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

    def list_prompts(self) -> list[dict[str, Any]]:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        SELECT
                            `id`,
                            `title`,
                            `vlm_type`,
                            `content`,
                            `is_closed`,
                            `update_date`,
                            `create_by`
                        FROM `vlm_prompt`
                        ORDER BY `update_date` DESC, `id` DESC
                    """
                )
                rows = list(cursor.fetchall())
        except pymysql.MySQLError as exc:
            raise VlmRepositoryError("读取 VLM 提示词数据失败") from exc
        finally:
            connection.close()

        return rows

    def create_prompt(
        self,
        *,
        title: str,
        vlm_type: str,
        content: str,
        is_closed: bool,
        create_by: str,
    ) -> int:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        INSERT INTO `vlm_prompt` (
                            `title`,
                            `vlm_type`,
                            `content`,
                            `is_closed`,
                            `create_date`,
                            `update_date`,
                            `create_by`
                        )
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
                    """,
                    (title, vlm_type, content, int(is_closed), create_by),
                )
                prompt_id = int(cursor.lastrowid)
            connection.commit()
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise VlmRepositoryError("创建 VLM 提示词失败") from exc
        finally:
            connection.close()

        return prompt_id

    def update_prompt(
        self,
        prompt_id: int,
        *,
        title: str,
        vlm_type: str,
        content: str,
        is_closed: bool,
    ) -> None:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                        UPDATE `vlm_prompt`
                        SET
                            `title` = %s,
                            `vlm_type` = %s,
                            `content` = %s,
                            `is_closed` = %s,
                            `update_date` = CURRENT_TIMESTAMP
                        WHERE `id` = %s
                    """,
                    (title, vlm_type, content, int(is_closed), prompt_id),
                )
                if not cursor.rowcount:
                    cursor.execute(
                        "SELECT 1 FROM `vlm_prompt` WHERE `id` = %s",
                        (prompt_id,),
                    )
                    if cursor.fetchone() is None:
                        raise VlmPromptNotFoundError("提示词不存在")
            connection.commit()
        except VlmPromptNotFoundError:
            connection.rollback()
            raise
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise VlmRepositoryError("更新 VLM 提示词失败") from exc
        finally:
            connection.close()

    def delete_prompt(self, prompt_id: int) -> None:
        connection = self._connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM `vlm_prompt` WHERE `id` = %s",
                    (prompt_id,),
                )
                if not cursor.rowcount:
                    raise VlmPromptNotFoundError("提示词不存在")
            connection.commit()
        except VlmPromptNotFoundError:
            connection.rollback()
            raise
        except pymysql.MySQLError as exc:
            connection.rollback()
            raise VlmRepositoryError("删除 VLM 提示词失败") from exc
        finally:
            connection.close()
