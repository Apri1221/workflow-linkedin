from pydantic import BaseModel, ConfigDict, Field
from typing import List
from pydantic.alias_generators import to_snake
from datetime import datetime
from utils.date_convert import gmt7now


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        # alias_generator=to_snake,
        populate_by_name=True,
        from_attributes=True,
        json_encoders={
            # custom output conversion for datetime
            datetime: gmt7now
        }
    )


class DataTask(BaseSchema):
    results: List[dict] | None = None
    state: dict | None = None
    next: dict | None = None

class DataSetup(BaseSchema):
    platforms: List[dict] | None = None
    result: dict
    state: dict | None = None

# new
class TaskResponse(BaseSchema):
    success: bool
    data: DataTask | None = None
    error: dict | str | None = None

class SetupResponse(BaseSchema):
    success: bool
    data: DataSetup
    error: dict | str | None = None