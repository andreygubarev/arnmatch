# arnmatch — Auto-generated Python AWS ARN parser

[![CI](https://github.com/andreygubarev/arnmatch/actions/workflows/ci.yml/badge.svg)](https://github.com/andreygubarev/arnmatch/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/arnmatch)](https://pypi.org/project/arnmatch/)
[![Python versions](https://img.shields.io/pypi/pyversions/arnmatch)](https://pypi.org/project/arnmatch/)
[![License](https://img.shields.io/github/license/andreygubarev/arnmatch)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/arnmatch)](https://pypi.org/project/arnmatch/)

`arnmatch` is a zero-dependency Python library and CLI for parsing AWS ARNs
(Amazon Resource Names) into structured resource data. It identifies the AWS
service, region, account, resource type, resource ID, CloudFormation resource
type, Resource Groups Tagging API type, and boto3 SDK service name.

Most ARN parsers split an ARN into its six top-level fields. `arnmatch` goes
further: its service-specific matching engine is generated from the
[AWS Service Authorization Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/)
and related AWS service metadata, so it can recognize thousands of real AWS
resource formats instead of relying on a small manually maintained list.

## Why arnmatch?

| Capability | arnmatch |
| --- | --- |
| Parse AWS ARN partition, service, region, and account | Yes |
| Identify service-specific resource type | Yes |
| Extract resource ID and resource name | Yes |
| Map ARN to CloudFormation resource type | Yes |
| Map ARN to Resource Groups Tagging API type | Yes |
| Map ARN to boto3 SDK client name | Yes |
| AWS service coverage | 350+ services |
| ARN resource pattern coverage | 2,100+ patterns |
| Runtime dependencies for parsing | 0 |

## Common use cases

- Build AWS inventory, CSPM, cloud security, and asset management tooling.
- Normalize ARNs returned by different AWS APIs.
- Map discovered resources to CloudFormation resource types.
- Determine which boto3 client can operate on a resource.
- Extract AWS account IDs, regions, resource IDs, and resource names from ARNs.
- Validate that an ARN belongs to a known AWS service/resource pattern.

## Installation

```bash
pip install arnmatch
```

## Quick start

### CLI

```bash
$ arnmatch "arn:aws:lambda:us-east-1:123456789012:function:my-function"
aws_service: lambda
aws_sdk_service: lambda
aws_sdk_services: lambda
aws_region: us-east-1
aws_account: 123456789012
resource_type: function
resource_id: my-function
resource_name: my-function
cloudformation_resource: AWS::Lambda::Function
tagging_resource: AWS::Lambda::Function
```

### Python library

```python
from arnmatch import arnmatch

result = arnmatch("arn:aws:lambda:us-east-1:123456789012:function:my-function")

result.aws_service              # "lambda"
result.aws_region               # "us-east-1"
result.aws_account              # "123456789012"
result.resource_type            # "function"
result.resource_id              # "my-function"
result.resource_name            # "my-function"
result.cloudformation_resource  # "AWS::Lambda::Function"
result.tagging_resource         # "AWS::Lambda::Function"
result.aws_sdk_service          # "lambda"
```

## Examples

### Parse an AWS ARN

```python
from arnmatch import arnmatch

arn = "arn:aws:s3:::my-bucket"
resource = arnmatch(arn)

print(resource.aws_service)    # s3
print(resource.resource_type)  # bucket
print(resource.resource_name)  # my-bucket
```

### Map AWS ARN to CloudFormation resource type

```python
from arnmatch import arnmatch

resource = arnmatch("arn:aws:lambda:us-east-1:123456789012:function:my-function")

print(resource.cloudformation_resource)
# AWS::Lambda::Function
```

### Map AWS ARN to Resource Groups Tagging API type

```python
from arnmatch import arnmatch

resource = arnmatch("arn:aws:rds:us-east-1:123456789012:db:my-database")

print(resource.tagging_resource)
# rds:db
```

### Get a boto3 client from an AWS ARN

```python
from arnmatch import arnmatch

resource = arnmatch("arn:aws:lambda:us-east-1:123456789012:function:my-function")
client = resource.client()

client.get_function(FunctionName=resource.resource_name)
```

The parser itself has zero runtime dependencies. The optional `client()` helper
requires `boto3` to be installed in your application environment.

### Extract account, region, resource ID, and resource name

```python
from arnmatch import arnmatch

resource = arnmatch("arn:aws:iam::123456789012:role/Admin")

print(resource.aws_account)    # 123456789012
print(resource.aws_region)     # "" for global IAM resources
print(resource.resource_type)  # role
print(resource.resource_id)    # Admin
print(resource.resource_name)  # Admin
```

## How it works

`arnmatch` generates its parser data instead of hand-writing ARN definitions.
The generation pipeline collects and reconciles AWS resource metadata from:

1. AWS Service Authorization Reference ARN patterns
2. CloudFormation resource specifications
3. Resource Groups Tagging API resource mappings
4. botocore/boto3 service metadata
5. Project override rules for AWS documentation edge cases

The generated output is compiled into `src/arnmatch/arn_patterns.py`, giving the
runtime package fast local regex matching with no network calls and no runtime
dependencies.

```text
AWS docs + service metadata
        ↓
codegen pipeline
        ↓
generated ARN regex patterns and mappings
        ↓
zero-dependency Python parser
```

## Features

- Zero runtime dependencies for ARN parsing
- 350+ AWS services and 2,100+ generated ARN resource patterns
- Service-specific resource type detection
- Resource ID and resource name extraction
- CloudFormation resource type mapping
- Resource Groups Tagging API type mapping
- boto3 SDK service name mapping
- CLI and Python library interface
- No network calls during parsing

## API reference

### `arnmatch(arn: str) -> ARN`

Parse an ARN string and return structured data.

Raises `ARNError` if the ARN format is invalid, the AWS service is unknown, or
no service-specific pattern matches.

### `ARN`

Dataclass with parsed ARN components:

| Field | Type | Description |
| --- | --- | --- |
| `aws_partition` | `str` | AWS partition, such as `aws`, `aws-cn`, or `aws-us-gov` |
| `aws_service` | `str` | AWS service name from the ARN |
| `aws_region` | `str` | AWS region; may be empty for global resources |
| `aws_account` | `str` | AWS account ID; may be empty for some global/public resources |
| `resource_type` | `str` | Canonical resource type from generated AWS patterns |
| `resource_types` | `list[str]` | All known aliases for this resource type |
| `attributes` | `dict[str, str]` | Captured attributes from the service-specific ARN pattern |
| `aws_sdk_service` | `str \| None` | Primary boto3 client name for the resource service |
| `cloudformation_resource` | `str \| None` | CloudFormation resource type, such as `AWS::Lambda::Function` |
| `tagging_resource` | `str \| None` | Resource Groups Tagging API type |

Properties:

| Property | Description |
| --- | --- |
| `resource_id` | Resource identifier; prefers captured attributes ending in `Id`, then `Name`, then the last resource attribute |
| `resource_name` | Resource name; prefers captured attributes ending in `Name`, then falls back to `resource_id` |
| `aws_sdk_services` | All boto3 client names mapped to the AWS service, such as `['elb', 'elbv2']` for `elasticloadbalancing` |

Methods:

| Method | Description |
| --- | --- |
| `client(session=None)` | Return a boto3 client for the resource service. Pass an optional `boto3.Session`, or use the default session. Raises `ValueError` if no SDK mapping exists. |

### `ARNError`

Exception raised when ARN parsing fails. Inherits from `ValueError`.

## Development

Prerequisites: [uv](https://github.com/astral-sh/uv)

```bash
make lint       # Run ruff linter
make test       # Run pytest tests
make check      # Run lint and test
make generate   # Regenerate patterns from AWS docs
make build      # Build wheel and tarball
make publish    # Build and upload to PyPI
```

Regenerate ARN pattern data:

```bash
cd codegen
make clean
make
```

Then copy generated patterns into the package and build:

```bash
make build
```

## Contributing

Bug reports, missing ARN patterns, mapping corrections, and documentation
improvements are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for local setup
and contribution guidelines.

## Security

For vulnerability reports or security-sensitive issues, see
[SECURITY.md](SECURITY.md).

## License

`arnmatch` is licensed under the [Apache License 2.0](LICENSE).

## Versioning

`arnmatch` uses [CalVer](https://calver.org/) in the format `YYYY.MM.MICRO`, for
example `2026.3.3`.
