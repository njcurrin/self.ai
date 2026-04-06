import logging
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Text, JSON

from selfai_ui.internal.db import Base, get_db
from selfai_ui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])


####################
# CuratorJob DB Schema
####################


class CuratorJob(Base):
    __tablename__ = "curator_job"

    id = Column(Text, unique=True, primary_key=True)
    user_id = Column(Text)
    pipeline_id = Column(Text)

    # States: pending -> scheduled -> queued -> running -> completed | failed | cancelled
    status = Column(Text)
    priority = Column(Text, default="normal")  # "run_now" | "high" | "normal"

    # Unix timestamp — when set, the job is auto-approved at this time
    scheduled_for = Column(BigInteger, nullable=True)

    # Set when job is dispatched to a curator node
    curator_job_id = Column(Text, nullable=True)
    curator_url_idx = Column(BigInteger, nullable=True)

    error_message = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)

    # NEW — dataset linking
    dataset_name = Column(Text, nullable=True)
    created_knowledge_id = Column(Text, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class CuratorJobModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    pipeline_id: str
    status: str
    priority: str = "normal"

    scheduled_for: Optional[int] = None

    curator_job_id: Optional[str] = None
    curator_url_idx: Optional[int] = None

    error_message: Optional[str] = None
    meta: Optional[dict] = None

    # NEW
    dataset_name: Optional[str] = None
    created_knowledge_id: Optional[str] = None

    created_at: int
    updated_at: int


class CuratorJobForm(BaseModel):
    pipeline_id: str
    scheduled_for: Optional[int] = None
    priority: str = "normal"
    dataset_name: Optional[str] = None  # NEW


class CuratorJobStatusUpdate(BaseModel):
    status: str
    curator_job_id: Optional[str] = None
    curator_url_idx: Optional[int] = None
    error_message: Optional[str] = None


####################
# Table CRUD Class
####################


class CuratorJobTable:
    def insert_new_job(
        self, user_id: str, form_data: CuratorJobForm
    ) -> Optional[CuratorJobModel]:
        with get_db() as db:
            initial_status = "scheduled" if form_data.scheduled_for else "pending"
            job = CuratorJobModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "pipeline_id": form_data.pipeline_id,
                    "status": initial_status,
                    "priority": form_data.priority,
                    "scheduled_for": form_data.scheduled_for,
                    "dataset_name": form_data.dataset_name,  # NEW
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                }
            )
            try:
                result = CuratorJob(**job.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                return CuratorJobModel.model_validate(result) if result else None
            except Exception:
                return None

    def get_all_jobs(self) -> list[CuratorJobModel]:
        with get_db() as db:
            jobs = (
                db.query(CuratorJob)
                .order_by(CuratorJob.created_at.desc())
                .all()
            )
            return [CuratorJobModel.model_validate(j) for j in jobs]

    def get_job_by_id(self, id: str) -> Optional[CuratorJobModel]:
        try:
            with get_db() as db:
                job = db.query(CuratorJob).filter_by(id=id).first()
                return CuratorJobModel.model_validate(job) if job else None
        except Exception:
            return None

    def update_job_status(
        self, id: str, update: CuratorJobStatusUpdate
    ) -> Optional[CuratorJobModel]:
        try:
            with get_db() as db:
                fields: dict = {"status": update.status, "updated_at": int(time.time())}
                if update.curator_job_id is not None:
                    fields["curator_job_id"] = update.curator_job_id
                if update.curator_url_idx is not None:
                    fields["curator_url_idx"] = update.curator_url_idx
                if update.error_message is not None:
                    fields["error_message"] = update.error_message
                db.query(CuratorJob).filter_by(id=id).update(fields)
                db.commit()
                return self.get_job_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    def update_job_meta(self, id: str, meta: dict) -> Optional[CuratorJobModel]:
        try:
            with get_db() as db:
                job = db.query(CuratorJob).filter_by(id=id).first()
                if not job:
                    return None
                existing = job.meta or {}
                existing.update(meta)
                db.query(CuratorJob).filter_by(id=id).update(
                    {"meta": existing, "updated_at": int(time.time())}
                )
                db.commit()
                return self.get_job_by_id(id=id)
        except Exception as e:
            log.exception(e)
            return None

    # NEW
    def update_created_knowledge_id(self, id: str, knowledge_id: str) -> bool:
        try:
            with get_db() as db:
                db.query(CuratorJob).filter_by(id=id).update(
                    {"created_knowledge_id": knowledge_id, "updated_at": int(time.time())}
                )
                db.commit()
                return True
        except Exception as e:
            log.exception(e)
            return False

    def get_jobs_by_status(self, status: str) -> list[CuratorJobModel]:
        try:
            with get_db() as db:
                jobs = db.query(CuratorJob).filter_by(status=status).all()
                return [CuratorJobModel.model_validate(j) for j in jobs]
        except Exception:
            return []

    def get_due_scheduled_jobs(self) -> list[CuratorJobModel]:
        now = int(time.time())
        with get_db() as db:
            rows = (
                db.query(CuratorJob)
                .filter(
                    CuratorJob.status == "scheduled",
                    CuratorJob.scheduled_for <= now,
                )
                .order_by(CuratorJob.scheduled_for.asc())
                .all()
            )
            return [CuratorJobModel.model_validate(r) for r in rows]

    def delete_job_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(CuratorJob).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


CuratorJobs = CuratorJobTable()