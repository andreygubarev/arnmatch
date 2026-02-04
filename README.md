# arnmatch

Parse AWS ARNs into structured data.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
[![PyPI](https://img.shields.io/pypi/v/arnmatch)](https://pypi.org/project/arnmatch/)

## Overview

Working with AWS at scale raises questions that are surprisingly hard to answer:

1. **What resource does this ARN represent?** - ARN formats vary across services with no consistent parsing rules
2. **What ARN formats exist?** - No single source documents all valid ARN patterns
3. **What resource types exist on AWS?** - Scattered across 300+ service documentation pages
4. **What CloudFormation type maps to this ARN?** - No direct ARN-to-CFN mapping exists

arnmatch answers these questions by:
- Parsing ARNs into structured components (service, region, account, resource type, resource ID)
- Providing a complete index of 2000+ resource types from 300+ AWS services
- Mapping ARNs to CloudFormation resource types (e.g., `arn:aws:lambda:...:function:X` → `AWS::Lambda::Function`)

Patterns are auto-generated from [AWS Service Authorization Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/).

## Features

- Zero runtime dependencies
- 300+ AWS services, 2000+ resource types
- Patterns auto-generated from AWS official documentation
- CLI and library interface
- CloudFormation resource type mapping
- Boto3 SDK service name mapping

## Installation

```bash
pip install arnmatch
```

## Quick Start

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
```

### Library

```python
from arnmatch import arnmatch

result = arnmatch("arn:aws:lambda:us-east-1:123456789012:function:my-function")

result.aws_service            # "lambda"
result.aws_region             # "us-east-1"
result.aws_account            # "123456789012"
result.resource_type          # "function"
result.resource_id            # "my-function"
result.resource_name          # "my-function"
result.cloudformation_resource  # "AWS::Lambda::Function"
result.aws_sdk_service        # "lambda"
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
| `attributes` | `dict[str, str]` | All captured attributes from the ARN |
| `aws_sdk_service` | `str \| None` | Primary boto3 client name |
| `cloudformation_resource` | `str \| None` | CloudFormation resource type |

Properties:

| Property | Description |
|----------|-------------|
| `resource_id` | Resource identifier (prefers attributes ending in `Id`, then `Name`, then last attribute) |
| `resource_name` | Resource name (prefers attributes ending in `Name`, falls back to `resource_id`) |
| `aws_sdk_services` | List of boto3 client names (e.g., `['elb', 'elbv2']` for elasticloadbalancing) |

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

## Versioning

[CalVer](https://calver.org/) format `YYYY.0M.MICRO` (e.g., `2026.02.0`).
