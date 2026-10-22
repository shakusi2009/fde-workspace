from datetime import date, timedelta

from app.config import get_settings
from app.repositories.vlm_task_repository import VlmTaskRepository
from app.schemas import TrendPoint, VlmOverview, VlmTask, VlmTaskPage


TASK_PAGE_SIZE = 10
TASK_TYPE_LABELS = {
    "label": "标注",
    "lable": "标注",
    "dig": "挖掘",
}


class VlmService:
    def __init__(self, repository: VlmTaskRepository) -> None:
        self.repository = repository

    def get_overview(self) -> VlmOverview:
        today = date.today()
        days = [
            today - timedelta(days=offset)
            for offset in reversed(range(7))
        ]
        task_total, daily_counts = self.repository.get_task_overview(
            days[0],
            today + timedelta(days=1),
        )
        return VlmOverview(
            task_total=task_total,
            overall_accuracy=None,
            token_total=0,
            task_trend=[
                TrendPoint(label=day.strftime("%m-%d"), value=daily_counts.get(day, 0))
                for day in days
            ],
            token_trend=[
                TrendPoint(label=day.strftime("%m-%d"))
                for day in days
            ],
            data_status="ready",
        )

    def list_tasks(self, page: int) -> VlmTaskPage:
        rows, total = self.repository.list_tasks(page=page, page_size=TASK_PAGE_SIZE)
        items = [
            VlmTask(
                sequence=row["id"],
                task_type=TASK_TYPE_LABELS.get(row["vlm_type"], row["vlm_type"]),
                created_at=row["create_time"],
                token_usage=row["task_tokens"],
                accuracy=row["task_accuracy"],
                remark=row["remarks"] or "",
                task_status=row["task_status"],
                updated_at=row["update_time"],
            )
            for row in rows
        ]
        return VlmTaskPage(
            items=items,
            total=total,
            page=page,
            page_size=TASK_PAGE_SIZE,
        )


vlm_service = VlmService(VlmTaskRepository(get_settings()))
