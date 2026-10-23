from datetime import date, timedelta

from app.config import get_settings
from app.repositories.vlm_task_repository import VlmTaskRepository
from app.schemas import (
    TrendPoint,
    VlmOverview,
    VlmPrompt,
    VlmPromptCreate,
    VlmPromptUpdate,
    VlmTask,
    VlmTaskCreate,
    VlmTaskExecutionContext,
    VlmTaskItem,
    VlmTaskItemPage,
    VlmTaskPage,
    VlmTaskUpdate,
)
from app.services.agent_service import (
    AgentExecutionError,
    VlmAgentService,
    vlm_agent_service,
)


TASK_PAGE_SIZE = 10
TASK_TYPE_LABELS = {
    "label": "标注",
    "dig": "挖掘",
}


class VlmService:
    def __init__(
        self,
        repository: VlmTaskRepository,
        agent_service: VlmAgentService,
    ) -> None:
        self.repository = repository
        self.agent_service = agent_service

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
                prompt_id=row["prompt_id"],
                prompt_title=row["prompt_title"],
                task_input=row["task_input"],
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

    def create_task(self, payload: VlmTaskCreate) -> int:
        return self.repository.create_task(**payload.model_dump())

    def list_task_items(self, task_id: int, page: int) -> VlmTaskItemPage:
        rows, total = self.repository.list_task_items(
            task_id=task_id,
            page=page,
            page_size=TASK_PAGE_SIZE,
        )
        return VlmTaskItemPage(
            items=[VlmTaskItem(**row) for row in rows],
            total=total,
            page=page,
            page_size=TASK_PAGE_SIZE,
            task_id=task_id,
        )

    def get_task_execution_context(
        self,
        task_id: int,
    ) -> VlmTaskExecutionContext:
        return VlmTaskExecutionContext(
            **self.repository.get_task_execution_context(task_id)
        )

    def execute_task(self, task_id: int, model_id: str) -> VlmTaskItem:
        context = self.get_task_execution_context(task_id)
        try:
            result = self.agent_service.execute(
                prompt_content=context.prompt_content,
                task_input=context.task_input,
                model_id=model_id,
            )
            row = self.repository.create_task_item(
                task_id=task_id,
                model_id=model_id,
                task_input=context.task_input,
                total_tokens=result.total_tokens,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cached_tokens=result.cached_tokens,
                task_status=0,
                output_text=result.output_text,
            )
        except AgentExecutionError as exc:
            row = self.repository.create_task_item(
                task_id=task_id,
                model_id=model_id,
                task_input=context.task_input,
                total_tokens=None,
                input_tokens=None,
                output_tokens=None,
                cached_tokens=None,
                task_status=1,
                output_text=str(exc),
            )
        return VlmTaskItem(**row)

    def update_task(self, task_id: int, payload: VlmTaskUpdate) -> None:
        self.repository.update_task(task_id, **payload.model_dump())

    def delete_task(self, task_id: int) -> None:
        self.repository.delete_task(task_id)

    def list_prompts(self) -> list[VlmPrompt]:
        return [
            VlmPrompt(
                id=row["id"],
                title=row["title"],
                vlm_type=TASK_TYPE_LABELS.get(row["vlm_type"], row["vlm_type"]),
                content=row["content"],
                is_closed=bool(row["is_closed"]),
                update_date=row["update_date"],
                create_by=row["create_by"],
            )
            for row in self.repository.list_prompts()
        ]

    def create_prompt(self, payload: VlmPromptCreate) -> int:
        return self.repository.create_prompt(**payload.model_dump())

    def update_prompt(self, prompt_id: int, payload: VlmPromptUpdate) -> None:
        self.repository.update_prompt(prompt_id, **payload.model_dump())

    def delete_prompt(self, prompt_id: int) -> None:
        self.repository.delete_prompt(prompt_id)


vlm_service = VlmService(
    VlmTaskRepository(get_settings()),
    vlm_agent_service,
)
