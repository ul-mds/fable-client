import httpx2 as httpx

from fable_client import FableError
from fable_client._client import BaseClient, GenericErrorResponse, ValidationErrorResponse, new_error_from_response
from tests.helpers import next_random_string


def test_validation_error():
    request = httpx.Request("POST", "http://test/match/")
    response = httpx.Response(
        httpx.codes.UNPROCESSABLE_CONTENT,
        json={"detail": [{"loc": ["body"], "msg": "field required", "type": "missing"}]},
        request=request,
    )
    error = new_error_from_response(response)

    assert isinstance(error, FableError)
    assert isinstance(error.error_response, ValidationErrorResponse)
    assert ": invalid request" in str(error)
    assert error.error_type == "validation"


def test_generic_error():
    request = httpx.Request("POST", "http://test/match/")
    response = httpx.Response(
        httpx.codes.INTERNAL_SERVER_ERROR.value,
        json={"detail": "fake internal server error"},
        request=request,
    )
    error = new_error_from_response(response)

    assert isinstance(error, FableError)
    assert isinstance(error.error_response, GenericErrorResponse)
    assert "fake internal server error" in str(error)
    assert error.error_type == "default"


def test_unhealthy_if_unavailable():
    client = BaseClient(base_url=f"http://{next_random_string()}")

    assert not client.is_healthy
