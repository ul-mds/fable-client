[![PyPI](https://img.shields.io/pypi/v/fable-client?cacheSeconds=0)](https://pypi.org/project/fable-client/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fable-client?cacheSeconds=0)](https://pypi.org/project/fable-client/)
![Code Coverage](https://img.shields.io/badge/Coverage-92%25-green.svg)
[![License](https://img.shields.io/pypi/l/fable-client?cacheSeconds=0)](https://pypi.org/project/fable-client/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)

# FABLE Client

This package contains HTTP-based clients for working with the servers provided by
the [PPRL service](https://github.com/ul-mds/fable-pprl-service) and the
[Broker service](https://github.com/ul-mds/fable-broker) which are part of the FABLE
(**F**ederated **A**nonymized **B**loom filter **L**inkage **E**ngine) ecosystem.
It also contains a command-line application which uses the library to process CSV files.

## Installation

```bash
pip install fable-client
```

Weight estimation requires additional packages which are not shipped by default.
To add them, install this package using the following command.

```bash
pip install fable-client[faker]
```

## Library clients

The library exposes the `PPRLClient` class for entity pre-processing, masking, bit vector matching and weight
estimation.
Furthermore, there is the `BrokerClient` class for handling match sessions, accepting bit vectors from different
clients, querying matching tasks for workers in the background and providing results to these clients.
They follow the data models that are also used by the FABLE services themselves, which are exposed through the
[FABLE model package](https://github.com/ul-mds/fable-model).

### PPRL Client

The following demonstrates the four main tasks of the `PPRLClient`: transformation, masking, matching and weight
estimation.

#### Entity transformation

```python
import fable_client
from fable_model import (
    EntityTransformRequest,
    TransformConfig,
    EmptyValueHandling,
    AttributeValueEntity,
    GlobalTransformerConfig,
    NormalizationTransformer,
)
import json

client = fable_client.PPRLClient(base_url="http://localhost:8080")

response = client.transform(
    EntityTransformRequest(
        config=TransformConfig(
            empty_value=EmptyValueHandling.error,
        ),
        entities=[
            AttributeValueEntity(
                id="001",
                attributes={"first_name": "Müller", "last_name": "Ludenscheidt"},
            ),
        ],
        global_transformers=GlobalTransformerConfig(
            before=[NormalizationTransformer()],
        ),
    )
)

print(
    json.dumps(
        [entity.model_dump() for entity in response.entities],
        indent=2,
    )
)
```

```text
[
  {
    "id": "001",
    "attributes": {
      "first_name": "muller",
      "last_name": "ludenscheidt"
    }
  }
]
```

#### Entity masking

```python
import fable_client
from fable_model import (
    EntityMaskRequest,
    MaskConfig,
    HashConfig,
    HashFunction,
    HashAlgorithm,
    RandomHash,
    CLKFilter,
    AttributeValueEntity,
)
import json

client = fable_client.PPRLClient(base_url="http://localhost:8080")

response = client.mask(
    EntityMaskRequest(
        config=MaskConfig(
            token_size=2,
            hash=HashConfig(
                function=HashFunction(
                    algorithms=[HashAlgorithm.sha1],
                    key="s3cr3t_k3y",
                ),
                strategy=RandomHash(),
            ),
            filter=CLKFilter(hash_values=5, filter_size=256),
        ),
        entities=[
            AttributeValueEntity(
                id="001",
                attributes={"first_name": "muller", "last_name": "ludenscheidt"},
            ),
        ],
    )
)

print(
    json.dumps(
        [entity.model_dump() for entity in response.entities],
        indent=2,
    )
)
```

```text
[
  {
    "id": "001",
    "value": "SKkgqBHBCJJCANICEKSpWMAUBYCQEMLuZgEQGBKRC8A="
  }
]
```

#### Bit vector matching

```python
import fable_client
from fable_model import VectorMatchRequest, MatchConfig, SimilarityMeasure, BitVectorEntity
import json

client = fable_client.PPRLClient(base_url="http://localhost:8080")

response = client.match(
    VectorMatchRequest(
        config=MatchConfig(measures=[SimilarityMeasure.jaccard], thresholds=[0.8]),
        domain=[
            BitVectorEntity(id="001", value="SKkgqBHBCJJCANICEKSpWMAUBYCQEMLuZgEQGBKRC8A="),
        ],
        range=[
            BitVectorEntity(id="100", value="UKkgqBHBDJJCANICELSpWMAUBYCMEMLrZgEQGBKRC7A="),
            BitVectorEntity(id="101", value="H5DN45iUeEjrjbHZrzHb3AyQk9O4IgxcpENKKzEKRLE="),
        ],
    )
)

print(
    json.dumps(
        [match.model_dump() for match in response.matches],
        indent=2,
    )
)
```

```text
[
  {
    "domain": {
      "id": "001",
      "value": "SKkgqBHBCJJCANICEKSpWMAUBYCQEMLuZgEQGBKRC8A="
    },
    "range": {
      "id": "100",
      "value": "UKkgqBHBDJJCANICELSpWMAUBYCMEMLrZgEQGBKRC7A="
    },
    "similarities": [
      0.8536585365853658
    ],
    "aggregated_similarity": null
  }
]
```

#### Attribute weight estimation

```python
import fable_client
from fable_model import (
    AttributeValueEntity,
    BaseTransformRequest,
    TransformConfig,
    EmptyValueHandling,
    GlobalTransformerConfig,
    NormalizationTransformer,
)
import json

client = fable_client.PPRLClient(base_url="http://localhost:8080")

stats = fable_client.estimate.compute_attribute_stats(
    client,
    [
        AttributeValueEntity(
            id="001",
            attributes={"given_name": "Max", "last_name": "Mustermann", "gender": "m"},
        ),
        AttributeValueEntity(
            id="002",
            attributes={"given_name": "Maria", "last_name": "Musterfrau", "gender": "f"},
        ),
    ],
    BaseTransformRequest(
        config=TransformConfig(empty_value=EmptyValueHandling.skip),
        global_transformers=GlobalTransformerConfig(before=[NormalizationTransformer()]),
    ),
)

print(json.dumps(stats, indent=2))
```

```text
{
  "given_name": {
    "average_tokens": 5.0,
    "ngram_entropy": 2.9219280948873623
  },
  "last_name": {
    "average_tokens": 11.0,
    "ngram_entropy": 3.913977073182751
  },
  "gender": {
    "average_tokens": 2.0,
    "ngram_entropy": 2.0
  }
}
```

### Broker Client

The following demonstrates the five main tasks of the `BrokerClient`: creating sessions, refreshing sessions, deleting
sessions, submitting vectors from different clients and fetching matching results. For further explanation read the
documentation of the [Broker service repository](https://github.com/ul-mds/fable-broker).

#### Creating a session

```python
from datetime import datetime
from fable_client import BrokerClient
from fable_model import SessionCreationRequest, MatchConfig, SimilarityMeasure, SimilarityAggregator

client = BrokerClient(base_url="http://localhost:8081")

r = client.create_session(
    SessionCreationRequest(
        session="my-session-id",
        match_config=MatchConfig(
            measures=[SimilarityMeasure.jaccard, SimilarityMeasure.dice],
            thresholds=[0.9],
            aggregator=SimilarityAggregator.avg,
        ),
    ),
)

print(r.session)
print(datetime.fromtimestamp(r.expires_at))
print(r.token)
```

```text
my-session-id
2026-07-10 11:33:01
7beb3d4d3527b26984b867453f24c02a
```

#### Refreshing a session

```python
from datetime import datetime
from fable_client import BrokerClient
from fable_model import SessionUpdateRequest

client = BrokerClient(base_url="http://localhost:8081")

r = client.refresh_session(
    SessionUpdateRequest(
        session="my-session-id",
        token="7beb3d4d3527b26984b867453f24c02a",
    ),
)

print(r.session)
print(datetime.fromtimestamp(r.expires_at))
```

```text
my-session-id
2026-07-10 12:03:01
```

#### Deleting a session

```python
from fable_client import BrokerClient
from fable_model import SessionDeletionRequest

client = BrokerClient(base_url="http://localhost:8081")

client.delete_session(
    SessionDeletionRequest(
        session="my-session-id",
        token="7beb3d4d3527b26984b867453f24c02a",
    ),
)
```

#### Submitting vectors for different clients

```python
from fable_client import BrokerClient
from fable_model import ClientSubmissionRequest, MetaBitVectorEntity, BitVectorMetadata

client = BrokerClient(base_url="http://localhost:8081")

client.submit(
    ClientSubmissionRequest(
        session="my-session-id",
        client="my-client-id",
        vectors=[
            MetaBitVectorEntity(
                id="001",
                value="CE9stxXqVmVQkHiZAZfE9w==",
                metadata=[
                    BitVectorMetadata(
                        name="count",
                        value="10",
                    ),
                ],
            ),
        ],
    ),
)

client.submit(
    ClientSubmissionRequest(
        session="my-session-id",
        client="my-client-id-2",
        vectors=[
            MetaBitVectorEntity(
                id="001",
                value="DE/st1XqViVQkHiZCJfE9w==",
                metadata=[
                    BitVectorMetadata(
                        name="count",
                        value="5",
                    ),
                ],
            ),
        ],
    ),
)
```

#### Fetching results

```python
from fable_client import BrokerClient
from fable_model import ClientResultRequest

client = BrokerClient(base_url="http://localhost:8081")

r = client.result(
    ClientResultRequest(
        session="my-session-id",
        client="my-client-id",
    ),
)

match = r.matches[0]

print(match.vector.id)
print(match.similarities)
print(match.aggregated_similarity)
print(match.reference_metadata)
```

```text
True
1
001
[0.90625, 0.9508196721311475]
0.9285348360655737
[BitVectorMetadata(name='count', value='5')]
```

## Command line interface

The `fable` command exposes all the library's functions and adapts them to work with CSV files.
Running `fable --help` provides an overview of the command options.

```
$ fable --help
Usage: fable [OPTIONS] COMMAND [ARGS]...

  HTTP client for performing PPRL based on Bloom filters.

Options:
  --base-url TEXT                 base URL to HTTP-based PPRL service
  -b, --batch-size INTEGER RANGE  amount of bit vectors to match at a time  [x>=1]
  --timeout-secs INTEGER RANGE    seconds until a request times out  [x>=1]
  --delimiter TEXT                column delimiter for CSV files
  --encoding TEXT                 character encoding for files
  --help                          Show this message and exit.

Commands:
  estimate   Estimate attribute weights based on randomly generated data.
  mask       Mask a CSV file with entities.
  match      Match bit vectors from CSV files against each other.
  transform  Perform pre-processing on a CSV file with entities
```

The `fable` command works on two basic types of CSV files that follow a simple structure.
Entity files are CSV files that contain a column with a unique identifier and arbitrary additional columns which
contain values for certain attributes that identify an entity.
Each row is representative of a single entity.

```csv
id,first_name,last_name,date_of_birth,gender
001,Natalie,Sampson,1956-12-16,female
002,Eric,Lynch,1910-01-11,female
003,Pam,Vaughn,1983-10-05,male
004,David,Jackson,2006-01-27,male
005,Rachel,Dyer,1904-02-02,female
```

Bit vector files contain an ID column and a value column which contains a representative bit vector.
These bit vectors are generally generated by masking a record from an entity file.

```csv
id,value
001,0Dr8t+kE5ltI+xdM85fwx0QLrTIgvFN35/0YvODNdOE0AaUHPphikXYy4LlArE4UqfjPs+wKtT233R7lBzSp5mwkCjTzA1tl0N7s+sFeKyIrOiGk0gNIYvA=
002,QMEIkE9TN1Quv0K0QAIk1RZD3qF7nQh0IyOYqVDf8IQkyaLGcFjiLHsEgBpU8CRSCuATbWpjEwGi3dilizySQy4miGiJolilYmwKysjseq+IFsAU3T1IRjA=
003,BqFoNZhrAVBq9SV1wBK0dUZLHDM9hCBoO4XdKCzvasSUELQeAB8+DV5tAhDl5KCSJfDCB6JG4WSoCFbozXqBYSUMqEQJE0JwhpRK6oLOcRRoGwGESDBMZwA=
004,8C9KItMTwtz4oXQvo8G0t1bTnwspnghmJwyqqcL2RIHASb4XJHAqybMCXQBm5mq6h/kdxGbblxBjhy79jRUcI60haqZhNsst0n7OUAxM/UoZVumIilRIbCA=
005,CFk4I0sKwnRoiTEOQASy1QZfHCGB1GBgYQDcZwDDtIkGGLOmLRhrQyOSlQDUDoYTbvaBRVqbkRnqmYQbDTEGlG+2y60FMmBEKtxsr0I4I00oMpuoXAsDWmA=
```

Pre-processing is done with the `fable transform` command.
It requires a base transform request file, an entity file and an output file to write the pre-processed entities to.
Attribute and global transformer configurations can be provided, but at least one must be specified.

In this example, a global normalization transformer which is executed before all other attribute-specific transformers
is defined.
Date time reformatting is applied to the "date of birth" column in the input file.

_request.json_

```json
{
  "config": {
    "empty_value": "skip"
  },
  "attribute_transformers": [
    {
      "attribute_name": "date_of_birth",
      "transformers": [
        {
          "name": "date_time",
          "input_format": "%Y-%m-%d",
          "output_format": "%Y%m%d"
        }
      ]
    }
  ],
  "global_transformers": {
    "before": [
      {
        "name": "normalization"
      }
    ]
  }
}
```

```
$ fable transform ./request.json ./input.csv ./output.csv  
Transforming entities  [####################################]  100%
```

_output.csv_

```csv
id,first_name,last_name,date_of_birth,gender
001,natalie,sampson,19561216,female
002,eric,lynch,19100111,female
003,pam,vaughn,19831005,male
004,david,jackson,20060127,male
005,rachel,dyer,19040202,female
```

Masking is done with `fable mask` and its subcommands.
It requires a base mask request file, an entity file and an output file to write the masked entities to.

_request.json_

```json
{
  "config": {
    "token_size": 2,
    "hash": {
      "function": {
        "algorithms": ["sha256"],
        "key": "s3cr3t_k3y",
        "strategy": {
          "name": "random_hash"
        }
      }
    },
    "prepend_attribute_name": true,
    "filter": {
      "type": "clk",
      "filter_size": 512,
      "hash_values": 5,
      "padding": "_",
      "hardeners": [
        {
          "name": "permute",
          "seed": 727
        },
        {
          "name": "rehash",
          "window_size": 16,
          "window_step": 8,
          "samples": 2
        }
      ]
    }
  }
}
```

_input.csv_

```csv
id,first_name,last_name,date_of_birth,gender
001,natalie,sampson,19561216,female
002,eric,lynch,19100111,female
003,pam,vaughn,19831005,male
004,david,jackson,20060127,male
005,rachel,dyer,19040202,female
```

```
$ fable mask ./request.json ./input.csv ./output.csv
Masking entities  [####################################]  100%
```

_output.csv_

```csv
id,value
001,wAWgITvQ1/VACpRYC2EKrfCkWziyEhmyKwi5sMsFrAQVoIBygTQScPRoIIAto0AwS0ihlcAIFAcQRwccY5IOmQ==
002,cFCwQIABQ+TgSSdlGM/z54BEUgmYhA1GKtCxQAKAXFIWiPAFIQYaFArgM61pUAAeATwBlBEOEw4Oowe0rbcMGw==
003,IgK16AAISCRoCuVAb1UBZYBBhGgxSEkKeMkTUCKAx4IAsNGJBS4ShgBAGIapBIQWJLiBFEEKAIWAGYS8ZZGMKw==
004,ZlBkyoYIEWmeaxbPDNng5JjHACkCAJwjlBCJQBJ4ZBSyOAukACUahOAFQ20oNwTQEDRA005+VUUfsUQcKCGNxg==
005,cUekQFQkI7TpTcRwmcNDoodRRBshlSEiAUjBQiMlxBLTmODMJICmDmxgUqYKonQEMFD58QsogRQFIgYUwJDOHA==
```

Matching is done with the `fable match` command.
It allows the matching of multiple bit vector input files at once.
If more than two files are provided, the command will pick out pairs of files and matches their contents against one
another.

In this example, the bit vectors of two files are matched against each other.
The Jaccard index is used as a similarity measure and a match threshold of 70% is applied.

_request.json_

```json
{
  "config": {
    "measures": "jaccard",
    "thresholds": 0.7
  }
}
```

_domain.csv_

```csv
id,value
001,wAWgITvQ1/VACpRYC2EKrfCkWziyEhmyKwi5sMsFrAQVoIBygTQScPRoIIAto0AwS0ihlcAIFAcQRwccY5IOmQ==
002,cFCwQIABQ+TgSSdlGM/z54BEUgmYhA1GKtCxQAKAXFIWiPAFIQYaFArgM61pUAAeATwBlBEOEw4Oowe0rbcMGw==
003,IgK16AAISCRoCuVAb1UBZYBBhGgxSEkKeMkTUCKAx4IAsNGJBS4ShgBAGIapBIQWJLiBFEEKAIWAGYS8ZZGMKw==
004,ZlBkyoYIEWmeaxbPDNng5JjHACkCAJwjlBCJQBJ4ZBSyOAukACUahOAFQ20oNwTQEDRA005+VUUfsUQcKCGNxg==
005,cUekQFQkI7TpTcRwmcNDoodRRBshlSEiAUjBQiMlxBLTmODMJICmDmxgUqYKonQEMFD58QsogRQFIgYUwJDOHA==
```

_range.csv_

```csv
id,value
101,kUSyxIgtIDSAB7ZYDkFQRZpFoMkCjCCCbDTWAUJTRAAEBpspBX4PNUZKi1AIVCABAjg6EAoKuwVleeUYgRBYoQ==
102,IAA0YE4MGexIiYdEjwNzoOKmIA4CEHEiKQASYFPhxQTQlPAAgYW3AWBYmQJ8YMoaAj0ZkoOrFyUmFo52TDcIKw==
103,BFAwREkkQbTdzddgDHFWgMRJMyxAMW+jq2ASICMBtIEr+YDCBRUgxEDIsQpciO4mAK3h2cIbXFQCMlaVpJPZIQ==
104,wBWgITvQ2/VACpRYC2EKrfCkWxiyEhmyKwi5sMsFrBQVoIBygTQScPRoIIAto0AwS0ihldAIFAcQRwccY5IOmQ==
105,QCCwIKQAED5AjaZYmodDcZAEBKkIxgAiDfEUoDKEdgEAEJAMAwcfQEbQkaQ4ANAABqiUscAKPQZEMJxRhTGIGQ==
```

```
$ fable match request.json domain.csv range.csv output.csv
Matching bit vectors from domain.csv and range.csv  [####################################]  100%
```

_output.csv_

```csv
domain_id,domain_file,range_id,range_file,similarities,aggregated_similarity
001,domain.csv,104,range.csv,[0.9690721649484536],
```

Weight estimation is done with the `fable estimate` command.
It generates random data based off of user specification and computes estimates for attribute weights.
Data can be generated using [Faker](https://faker.readthedocs.io/).

*faker.json*

```json
{
  "seed": 727,
  "count": 5000,
  "locale": ["de_DE"],
  "generators": [
    {"function_name": "first_name_nonbinary", "attribute_name": "given_name"},
    {"function_name": "last_name", "attribute_name": "last_name"},
    {"function_name": "random_element", "attribute_name": "gender", "args": {"elements": ["m", "f"]}},
    {"function_name": "street_name", "attribute_name": "street_name"},
    {"function_name": "city", "attribute_name": "municipality"},
    {"function_name": "postcode", "attribute_name": "postcode"}
  ]
}
```

```
$ fable estimate faker faker.json faker-output.json
```

*faker-output.json*

```json
[
  {
    "attribute_name": "given_name",
    "weight": 7.657958943890718,
    "average_token_count": 7.5686
  },
  {
    "attribute_name": "last_name",
    "weight": 7.444573503220938,
    "average_token_count": 7.5204
  },
  {
    "attribute_name": "gender",
    "weight": 1.9999971146079947,
    "average_token_count": 2.0
  },
  {
    "attribute_name": "street_name",
    "weight": 7.605565770282046,
    "average_token_count": 16.2188
  },
  {
    "attribute_name": "municipality",
    "weight": 7.659422921807241,
    "average_token_count": 9.952
  },
  {
    "attribute_name": "postcode",
    "weight": 6.7812429085107,
    "average_token_count": 5.9464
  }
]
```

## Configuring pytest

In order to run integration tests, the FABLE PPRL and Broker services are needed.
The first option is to spin up the service independently and direct pytest to it.
Alternatively, pytest can start a Docker test container for the duration of the test run.
The following table shows all available configuration options.
These variables can be defined in `.env` or `.env.test`.

| **Environment variable**                    | **Description**                                                               | **Default** |
|---------------------------------------------|-------------------------------------------------------------------------------|-------------|
| PYTEST_PPRL_SERVICE_BASE_URL<sup>1)</sup>   | Base URL for the FABLE PPRL service                                           |             |
| PYTEST_PPRL_SERVICE_VERSION                 | Tag of the FABLE PPRL service image that will run inside the test container   |             |
| PYTEST_BROKER_SERVICE_BASE_URL<sup>1)</sup> | Base URL for the FABLE Broker service                                         |             |
| PYTEST_BROKER_SERVICE_VERSION               | Tag of the FABLE Broker service image that will run inside the test container |             |

<sup>1)</sup> If defined, pytest will not spin up a test container.

## License

MIT.
