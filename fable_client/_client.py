from json import JSONDecodeError
from typing import Literal, TypeVar, overload

import httpx2 as httpx
from fable_model import (
    ClientResultRequest,
    ClientResultResponse,
    ClientSubmissionRequest,
    EntityMaskRequest,
    EntityMaskResponse,
    EntityTransformRequest,
    EntityTransformResponse,
    HealthResponse,
    ServiceBaseInformation,
    SessionCreationRequest,
    SessionCreationResponse,
    SessionDeletionRequest,
    SessionGetResponse,
    SessionUpdateRequest,
    SessionUpdateResponse,
    VectorMatchRequest,
    VectorMatchResponse,
)
from pydantic import BaseModel, ValidationError

_MI = TypeVar("_MI", bound=BaseModel)
_MO = TypeVar("_MO", bound=BaseModel)


class GenericErrorResponse(BaseModel):
    detail: str


class ValidationErrorDetail(BaseModel):
    loc: list[str]
    msg: str
    type: str


class ValidationErrorResponse(BaseModel):
    detail: list[ValidationErrorDetail]


class FableError(httpx.HTTPError):
    def __init__(
        self, message: str, request: httpx.Request, error: GenericErrorResponse | ValidationErrorResponse | None = None
    ):
        super().__init__(message)
        self._request = request
        self.error_response = error

        self.error_type = "unknown"

        if isinstance(error, GenericErrorResponse):
            self.error_type = "default"

        if isinstance(error, ValidationErrorResponse):
            self.error_type = "validation"


def new_error_from_response(r: httpx.Response):
    error_response = None
    error_message = f"received status code {r.status_code}"

    # validation error (422 by default with FastAPI)
    if r.status_code == httpx.codes.UNPROCESSABLE_CONTENT:
        try:
            error_response = ValidationErrorResponse(**r.json())
            error_message += ": invalid request"
        except (ValidationError, JSONDecodeError):
            pass
    else:
        try:
            error_response = GenericErrorResponse(**r.json())
            error_message += f": {error_response.detail}"
        except (ValidationError, JSONDecodeError):
            pass

    return FableError(error_message, r.request, error_response)


class BaseClient:
    def __init__(self, client: httpx.Client | None = None, base_url: str | None = None):
        self._client = client or httpx.Client(base_url=base_url)

    def close(self):
        self._client.close()

    @overload
    def _request(
        self,
        path: str,
        model_in: _MI | None,
        model_out: type[_MO],
        method: Literal["POST", "GET", "PUT", "DELETE", "PATCH"] = "POST",
        expected_code: int = httpx.codes.OK,
    ) -> _MO: ...

    @overload
    def _request(
        self,
        path: str,
        model_in: _MI | None,
        model_out: None,
        method: Literal["POST", "GET", "PUT", "DELETE", "PATCH"] = "POST",
        expected_code: int = httpx.codes.OK,
    ) -> None: ...

    def _request(
        self,
        path: str,
        model_in: _MI | None,
        model_out: type[_MO] | None,
        method: Literal["POST", "GET", "PUT", "DELETE", "PATCH"] = "POST",
        expected_code: int = httpx.codes.OK,
    ) -> _MO | None:
        if model_in is not None:
            r = self._client.request(method, path, json=model_in.model_dump(mode="json"))
        else:
            r = self._client.request(method, path)

        if r.status_code != expected_code:
            raise new_error_from_response(r)

        if model_out is None:
            return None

        return model_out.model_validate(r.json())

    @property
    def health_endpoint(self) -> str:
        return "health"

    @property
    def is_healthy(self) -> bool:
        try:
            r = self._client.get(self.health_endpoint)
        except httpx.HTTPError:
            return False
        try:
            HealthResponse(**r.json())
        except ValidationError:
            return False
        return r.status_code == httpx.codes.OK

    @property
    def version(self) -> str:
        r = self._client.get("")
        r.raise_for_status()

        return ServiceBaseInformation(**r.json()).version


class PPRLClient(BaseClient):
    @property
    def health_endpoint(self) -> str:
        return "healthz"

    def match(self, request: VectorMatchRequest) -> VectorMatchResponse:
        return self._request("match", request, VectorMatchResponse)

    def transform(self, request: EntityTransformRequest) -> EntityTransformResponse:
        return self._request("transform", request, EntityTransformResponse)

    def mask(self, request: EntityMaskRequest) -> EntityMaskResponse:
        return self._request("mask", request, EntityMaskResponse)


class BrokerClient(BaseClient):
    def create_session(self, request: SessionCreationRequest) -> SessionCreationResponse:
        return self._request("session", request, SessionCreationResponse, expected_code=httpx.codes.CREATED)

    def get_session(self, session: str) -> SessionGetResponse:
        return self._request(f"session/{session}", None, SessionGetResponse, method="GET")

    def delete_session(self, request: SessionDeletionRequest) -> None:
        return self._request("session", request, None, method="DELETE", expected_code=httpx.codes.ACCEPTED)

    def refresh_session(self, request: SessionUpdateRequest) -> SessionUpdateResponse:
        return self._request("session", request, SessionUpdateResponse, method="PATCH")

    def submit(self, request: ClientSubmissionRequest) -> None:
        return self._request("session/submit", request, None, expected_code=httpx.codes.ACCEPTED)

    def result(self, request: ClientResultRequest) -> ClientResultResponse:
        return self._request("session/result", request, ClientResultResponse)
