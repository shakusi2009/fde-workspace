from app.config import get_settings
from app.driver_schemas import (
    DriverCreate,
    DriverPage,
    DriverUpdate,
)
from app.repositories.driver_repository import DriverRepository


DRIVER_PAGE_SIZE = 10


class DriverService:
    def __init__(self, repository: DriverRepository) -> None:
        self.repository = repository

    def list_drivers(self, *, page: int, keyword: str) -> DriverPage:
        rows, total = self.repository.list_drivers(
            page=page,
            page_size=DRIVER_PAGE_SIZE,
            keyword=keyword.strip(),
        )
        return DriverPage(
            items=rows,
            total=total,
            page=page,
            page_size=DRIVER_PAGE_SIZE,
        )

    def create_driver(self, payload: DriverCreate) -> int:
        return self.repository.create_driver(**payload.model_dump())

    def update_driver(self, driver_id: int, payload: DriverUpdate) -> None:
        self.repository.update_driver(driver_id, **payload.model_dump())

    def delete_driver(self, driver_id: int) -> None:
        self.repository.delete_driver(driver_id)


driver_service = DriverService(DriverRepository(get_settings()))
