# arnmatch

Parse AWS ARNs into structured data.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)

## Why

AWS ARN formats are inconsistent. This problem was unsolved. Now it's solved (for 2000+ resource types from 300+ services). You're welcome.

## Features

- Zero runtime dependencies
- 300+ AWS services, 2000+ resource types supported
- Patterns auto-generated from AWS official documentation
- CLI and library interface
- Extracts resource type, ID, and name with smart heuristics

## Installation

```bash
pip install arnmatch
```

## Quick Start

### CLI

```bash
$ uvx arnmatch "arn:aws:lambda:us-east-1:123456789012:function:my-function"
aws_service: lambda
aws_sdk_services: lambda
aws_region: us-east-1
aws_account: 123456789012
resource_type: function
resource_id: my-function
resource_name: my-function
```

### Library

```python
from arnmatch import arnmatch

arn = "arn:aws:lambda:us-east-1:123456789012:function:my-function"
result = arnmatch(arn)

print(result.aws_service)      # lambda
print(result.aws_sdk_services) # ['lambda']
print(result.aws_region)       # us-east-1
print(result.aws_account)      # 123456789012
print(result.resource_type)    # function
print(result.resource_id)      # my-function
print(result.resource_name)    # my-function
print(result.attributes)       # {'Partition': 'aws', 'Region': 'us-east-1', ...}
```

## API Reference

### `arnmatch(arn: str) -> ARN`

Parse an ARN string and return structured data.

Raises `ARNError` if the ARN format is invalid or no pattern matches.

### `ARN`

Dataclass with parsed ARN components:

| Field | Type | Description |
|-------|------|-------------|
| `aws_partition` | `str` | AWS partition (aws, aws-cn, aws-us-gov) |
| `aws_service` | `str` | AWS service name |
| `aws_region` | `str` | AWS region (may be empty for global resources) |
| `aws_account` | `str` | AWS account ID |
| `resource_type` | `str` | Canonical resource type from AWS docs |
| `resource_types` | `list[str]` | All known names for this resource type |
| `attributes` | `dict[str, str]` | All captured attributes from the pattern |

Properties:

| Property | Description |
|----------|-------------|
| `resource_id` | Resource identifier (prefers groups ending in `Id`, falls back to `Name`, then last group) |
| `resource_name` | Resource name (prefers groups ending in `Name`, falls back to `resource_id`) |
| `aws_sdk_services` | List of boto3 client names for this service (e.g., `['elb', 'elbv2']` for elasticloadbalancing) |

### `ARNError`

Exception raised when ARN parsing fails. Inherits from `ValueError`.

## Versioning

This project uses [CalVer](https://calver.org/) with format `YYYY.0M.MICRO` (e.g., `2026.01.0`).

## Development

Prerequisites: [uv](https://github.com/astral-sh/uv)

```bash
make lint       # Run ruff linter
make test       # Run pytest tests
make check      # Run lint and test
make build      # Build wheel and tarball
make publish    # Build and upload to PyPI
make clean      # Remove build artifacts
```

Regenerate patterns from AWS docs:

```bash
cd codegen && uv run codegen.py
```
