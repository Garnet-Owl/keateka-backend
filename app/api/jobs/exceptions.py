from app.api.shared.exceptions import BaseAPIException


class JobNotFoundException(BaseAPIException):
    def __init__(self, job_id: int):
        super().__init__(
            message=f"Job with id {job_id} not found",
            status_code=404,
            error_code="JOB_NOT_FOUND",
        )


class JobStatusTransitionError(BaseAPIException):
    def __init__(self, current_status: str, new_status: str):
        super().__init__(
            message=f"Invalid status transition from {current_status} to {new_status}",
            status_code=400,
            error_code="INVALID_STATUS_TRANSITION",
        )


class JobSchedulingError(BaseAPIException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=400,
            error_code="SCHEDULING_ERROR",
        )


class JobAuthorizationError(BaseAPIException):
    def __init__(self, message: str = "Not authorized to perform this action"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="JOB_AUTHORIZATION_ERROR",
        )


class CleanerNotAvailableError(BaseAPIException):
    def __init__(self, cleaner_id: int):
        super().__init__(
            message=f"Cleaner {cleaner_id} is not available",
            status_code=400,
            error_code="CLEANER_NOT_AVAILABLE",
        )


class JobTrackingError(BaseAPIException):
    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=400,
            error_code="TRACKING_ERROR",
        )
