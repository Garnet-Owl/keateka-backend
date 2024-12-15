from typing import Callable, Protocol


class TestContext(Protocol):
    test_data: dict


def prepare_test_data() -> Callable[[TestContext], None]:
    def step(context: TestContext) -> None:
        context.test_data = {
            "base_exception": {
                "all_fields": {
                    "message": "Test error",
                    "status_code": 400,
                    "error_code": "TEST_ERROR",
                    "details": {"field": "value"},
                },
                "required_fields": {
                    "message": "Test error",
                },
            },
            "validation_error": {
                "field_details": {
                    "field": "email",
                    "error": "invalid format",
                    "value": "invalid@email",
                },
                "multiple_fields": {
                    "errors": [
                        {"field": "email", "error": "invalid format"},
                        {"field": "phone", "error": "required"},
                    ],
                },
            },
        }

    return step
