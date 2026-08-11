import base64
import os
import uuid
from random import Random

import httpx2 as httpx
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from fable_client import BrokerClient, PPRLClient


@pytest.fixture(scope="session")
def network():
    with Network() as network:
        yield network


@pytest.fixture(scope="session")
def pprl_service_use_testcontainer():
    return not bool(os.environ.get("PYTEST_PPRL_SERVICE_BASE_URL", ""))


@pytest.fixture(scope="session")
def broker_service_use_testcontainer():
    return not bool(os.environ.get("PYTEST_BROKER_SERVICE_BASE_URL", ""))


@pytest.fixture(scope="session")
def pprl_base_url(network, pprl_service_use_testcontainer):
    if not pprl_service_use_testcontainer:
        yield os.environ["PYTEST_PPRL_SERVICE_BASE_URL"]
        return

    pprl_service_tag = os.environ["PYTEST_PPRL_SERVICE_VERSION"]

    container = (
        DockerContainer(f"ghcr.io/ul-mds/fable-pprl-service:{pprl_service_tag}")
        .with_exposed_ports(8080)
        .waiting_for(LogMessageWaitStrategy("Application startup complete"))
        .with_env("ROLE", "both")
        .with_network(network)
        .with_network_aliases("matcher")
    )

    with container:
        yield f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"


@pytest.fixture(scope="session")
def neo4j(network, broker_service_use_testcontainer):
    if broker_service_use_testcontainer:
        network_alias = "neo4j"

        container = (
            DockerContainer("neo4j:5.26.27-community")
            .with_env("NEO4J_AUTH", "none")
            .with_network(network)
            .with_network_aliases(network_alias)
            .waiting_for(LogMessageWaitStrategy("Started."))
        )

        with container:
            yield network_alias
    else:
        yield None


@pytest.fixture(scope="session")
def rabbitmq(network, broker_service_use_testcontainer):
    if broker_service_use_testcontainer:
        network_alias = "rabbitmq"

        container = (
            DockerContainer("rabbitmq:3.13.7")
            .with_network(network)
            .with_network_aliases(network_alias)
            .waiting_for(LogMessageWaitStrategy("Server startup complete"))
        )

        with container:
            yield network_alias
    else:
        yield None


@pytest.fixture(scope="session")
def redis(network, broker_service_use_testcontainer):
    if broker_service_use_testcontainer:
        network_alias = "redis"

        container = (
            DockerContainer("redis:8.6.4")
            .with_network(network)
            .with_network_aliases(network_alias)
            .waiting_for(LogMessageWaitStrategy("Ready to accept connections"))
        )

        with container:
            yield network_alias
    else:
        yield None


@pytest.fixture(scope="session")
def broker_worker(
    network,
    broker_service_use_testcontainer,
    pprl_service_use_testcontainer,
    pprl_base_url,
    rabbitmq,
    redis,
    neo4j,
):
    if broker_service_use_testcontainer:
        network_alias = "broker-worker"
        broker_service_tag = os.environ["PYTEST_BROKER_SERVICE_VERSION"]

        if pprl_service_use_testcontainer:
            pprl_base_url = "http://matcher:8080"

        container = (
            DockerContainer(f"ghcr.io/ul-mds/fable-broker:{broker_service_tag}")
            .with_command(["celery", "-A", "fable_broker.worker.celery", "worker", "--loglevel", "INFO"])
            .with_network(network)
            .with_network_aliases(network_alias)
            .waiting_for(LogMessageWaitStrategy("ready"))
            .with_env("AMQP_URL", f"amqp://guest:guest@{rabbitmq}:5672//")
            .with_env("REDIS_URL", f"redis://{redis}:6379/0")
            .with_env("NEO4J_URL", f"bolt://{neo4j}:7687")
            .with_env("PPRL_SERVICE_BASE_URL", pprl_base_url)
        )

        with container:
            yield network_alias
    else:
        yield None


@pytest.fixture(scope="session")
def broker_base_url(
    network,
    broker_service_use_testcontainer,
    pprl_service_use_testcontainer,
    pprl_base_url,
    rabbitmq,
    redis,
    neo4j,
):
    if not broker_service_use_testcontainer:
        yield os.environ["PYTEST_BROKER_SERVICE_BASE_URL"]
        return

    broker_service_tag = os.environ["PYTEST_BROKER_SERVICE_VERSION"]

    if pprl_service_use_testcontainer:
        pprl_base_url = "http://matcher:8080"

    container = (
        DockerContainer(f"ghcr.io/ul-mds/fable-broker:{broker_service_tag}")
        .with_command(
            [
                "uvicorn",
                "fable_broker.server:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8080",
                "--workers",
                "1",
                "--log-config",
                "config/logging.yaml",
            ]
        )
        .with_exposed_ports(8080)
        .with_env("AMQP_URL", f"amqp://guest:guest@{rabbitmq}:5672//")
        .with_env("REDIS_URL", f"redis://{redis}:6379/0")
        .with_env("NEO4J_URL", f"bolt://{neo4j}:7687")
        .with_env("PPRL_SERVICE_BASE_URL", pprl_base_url)
        .with_network(network)
        .with_network_aliases("broker-api")
        .waiting_for(LogMessageWaitStrategy("Application startup complete."))
    )

    with container:
        yield f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"


@pytest.fixture(scope="session")
def pprl_client(pprl_base_url):
    client = httpx.Client(base_url=pprl_base_url)

    assert client.get("healthz").status_code == httpx.codes.OK

    yield PPRLClient(client)

    client.close()


@pytest.fixture(scope="session")
def broker_client(broker_base_url):
    client = httpx.Client(base_url=broker_base_url, timeout=20)

    assert client.get("health").status_code == httpx.codes.OK

    yield BrokerClient(client)

    client.close()


@pytest.fixture(scope="session")
def rng_factory():
    def _rng():
        return Random(727)

    return _rng


@pytest.fixture()
def rng(rng_factory):
    return rng_factory()


@pytest.fixture(scope="session")
def uuid4_factory():
    def _uuid4():
        return str(uuid.uuid4())

    return _uuid4


@pytest.fixture(scope="session")
def base64_factory(rng_factory):
    rng = rng_factory()

    def _b64():
        return base64.b64encode(rng.randbytes(16)).decode("utf-8")

    return _b64


@pytest.fixture(scope="session", autouse=True)
def faker_session_locale():
    return ["en_US"]


@pytest.fixture(scope="session", autouse=True)
def faker_seed():
    return 727
