# arnmatch

Parse AWS ARNs into structured data.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)

## Features

- Zero runtime dependencies
- 355 AWS services supported
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
$ arnmatch "arn:aws:lambda:us-east-1:123456789012:function:my-function"
service: lambda
region: us-east-1
account: 123456789012
resource_type: function
resource_id: my-function
resource_name: my-function
```

### Library

```python
from arnmatch import arnmatch, ARNMatchError

arn = "arn:aws:lambda:us-east-1:123456789012:function:my-function"
result = arnmatch(arn)

print(result.service)        # lambda
print(result.region)         # us-east-1
print(result.account)        # 123456789012
print(result.resource_type)  # function
print(result.resource_id)    # my-function
print(result.resource_name)  # my-function
print(result.groups)         # {'Partition': 'aws', 'Region': 'us-east-1', ...}
```

## API Reference

### `arnmatch(arn: str) -> ARNMatch`

Parse an ARN string and return structured data.

Raises `ARNMatchError` if the ARN format is invalid or no pattern matches.

### `ARNMatch`

Dataclass with parsed ARN components:

| Field | Type | Description |
|-------|------|-------------|
| `partition` | `str` | AWS partition (aws, aws-cn, aws-us-gov) |
| `service` | `str` | AWS service name |
| `region` | `str` | AWS region (may be empty for global resources) |
| `account` | `str` | AWS account ID |
| `resource_type` | `str` | Canonical resource type from AWS docs |
| `resource_type_aliases` | `list[str]` | All known names for this resource type |
| `groups` | `dict[str, str]` | All captured groups from the pattern |

Properties:

| Property | Description |
|----------|-------------|
| `resource_id` | Resource identifier (prefers groups ending in `Id`, falls back to `Name`, then last group) |
| `resource_name` | Resource name (prefers groups ending in `Name`, falls back to `resource_id`) |

### `ARNMatchError`

Exception raised when ARN parsing fails. Inherits from `ValueError`.

## Development

Prerequisites: [uv](https://github.com/astral-sh/uv)

```bash
make lint       # Run ruff linter
make build      # Build wheel and tarball
make publish    # Build and upload to PyPI
make clean      # Remove build artifacts
```

Regenerate patterns from AWS docs:

```bash
cd codegen && uv run codegen.py
```
