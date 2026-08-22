from pydantic import BaseModel


class PageParams(BaseModel):
    page: int = 1
    size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class PageResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
