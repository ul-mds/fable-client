import base64
import random
import string
import time
from collections.abc import Callable
from typing import Any

from fable_model import AttributeValueEntity, BitVectorEntity, BitVectorMetadata, MetaBitVectorEntity
from faker import Faker


def generate_person(person_id: str, faker: Faker):
    return AttributeValueEntity(
        id=person_id,
        attributes={
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "date_of_birth": faker.date_of_birth(minimum_age=18, maximum_age=120).strftime("%Y-%m-%d"),
            "gender": faker.random_element(["male", "female"]),
        },
    )


def next_random_string(charset=string.ascii_letters, length: int = 20):
    assert length > 0
    assert len(charset) > 0

    return "".join([random.choice(charset) for _ in range(length)])


def next_random_b64() -> str:
    return base64.b64encode(random.randbytes(16)).decode("utf-8")


def next_random_vec() -> BitVectorEntity:
    return BitVectorEntity(
        id=str(random.randint(0, 1_000_000)),
        value=next_random_b64(),
    )


def next_random_meta_vec() -> MetaBitVectorEntity:
    v = next_random_vec()
    return MetaBitVectorEntity(
        id=v.id,
        value=v.value,
        metadata=[BitVectorMetadata(name="value", value=str(random.randint(0, 100)))],
    )


def assert_eventually(func: Callable[[], Any], max_retries: int = 10, delay_millis: int = 1_000):
    e = None
    for _ in range(max_retries):
        try:
            func()
            return  # Return if everything went fine.
        except AssertionError as err:
            e = err

        time.sleep(delay_millis / 1_000)

    assert False, f"Callback failed after {max_retries} retries: {e}"
