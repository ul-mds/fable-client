import time

import httpx2
import pytest
from fable_model import (
    ClientResultRequest,
    ClientSubmissionRequest,
    MatchConfig,
    SessionCreationRequest,
    SessionDeletionRequest,
    SessionUpdateRequest,
    SimilarityAggregator,
    SimilarityMeasure,
)

from tests.helpers import assert_eventually, next_random_meta_vec, next_random_string

pytestmark = pytest.mark.integration


@pytest.fixture
def session(broker_client):
    session_name = next_random_string()

    r = broker_client.create_session(
        SessionCreationRequest(
            session=session_name,
            match_config=MatchConfig(
                measures=[SimilarityMeasure.cosine, SimilarityMeasure.jaccard],
                thresholds=[0.9],
                aggregator=SimilarityAggregator.avg,
            ),
        ),
    )

    assert r.session.get_secret_value() == session_name

    yield r

    broker_client.delete_session(
        SessionDeletionRequest(
            session=session_name,
            token=r.token,
        ),
    )


@pytest.fixture
def clients(broker_client, session):
    client1, client2 = next_random_string(), next_random_string()

    broker_client.submit(
        ClientSubmissionRequest(
            session=session.session,
            client=client1,
            vectors=[next_random_meta_vec()],
        ),
    )

    broker_client.submit(
        ClientSubmissionRequest(
            session=session.session,
            client=client2,
            vectors=[next_random_meta_vec()],
        ),
    )

    return client1, client2


def test_refresh_session(broker_client, session):
    old_expires_at = session.expires_at

    # Sleep here for one second to be sure that the new expiration timestamp is bigger.
    time.sleep(1)

    r = broker_client.refresh_session(
        SessionUpdateRequest(
            session=session.session,
            token=session.token,
        ),
    )

    assert r.session == session.session
    assert old_expires_at < r.expires_at


def test_get_result(broker_client, session, clients):
    client1, _ = clients

    def _wait_for_matching_to_finish():
        r = broker_client.result(
            ClientResultRequest(
                session=session.session,
                client=client1,
            ),
        )
        assert r.finished

    assert_eventually(_wait_for_matching_to_finish)


def test_version(broker_base_url, broker_client):
    assert broker_client.version == httpx2.get(broker_base_url).json()["version"]


def test_healthiness(broker_client):
    assert broker_client.is_healthy
