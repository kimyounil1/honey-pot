from . import BaseModel, datetime
from typing import Optional, Literal, List


class AssessmentCreate(BaseModel):
    policy_instance_id: int  # DB id of InsurancePolicy for this user
    assessment_name: str


class AssessmentRead(BaseModel):
    id: int
    title: str
    insurer: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


class MessageRead(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    attachment: Optional[dict] = None


class MessageCreate(BaseModel):
    content: str


class MessageStateRead(BaseModel):
    state: Literal[
        "commencing",
        "classifying",
        "analyzing",
        "searching",
        "building",
        "done",
        "failed",
        "complete",
    ]


class UploadItem(BaseModel):
    upload_id: str
    filename: str
    file_type: Optional[str]
    file_size: Optional[int]
    upload_status: str
    ocr_status: Optional[str]
    created_at: datetime


class UploadList(BaseModel):
    uploads: List[UploadItem]
