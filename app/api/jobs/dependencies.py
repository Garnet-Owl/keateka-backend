from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.shared.database import get_db
from app.api.jobs import models, service


async def get_job_by_id(job_id: int, db: AsyncSession = Depends(get_db)) -> Optional[models.Job]:
    job_service = service.JobService(db)
    try:
        return await job_service.get_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
