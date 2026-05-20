# Python API reference

## `arnmatch(arn: str) -> ARN`

Parse an ARN string and return structured data.

**Parameters**

- `arn` (`str`): A valid AWS ARN.

**Returns**

- `ARN`: A dataclass with parsed components and mappings.

**Raises**

- `ARNError`: If the ARN format is invalid, the service is unknown, or no pattern matches.

**Example**

```python
from arnmatch import arnmatch

resource = arnmatch("arn:aws:ec2:us-east-1:123456789012:instance/i-abc123")
print(resource.resource_type)  # instance
print(resource.resource_id)    # i-abc123
```

---

## `ARNError`

Exception raised when ARN parsing fails. Inherits from `ValueError`.

```python
from arnmatch import arnmatch, ARNError

try:
    resource = arnmatch("invalid")
except ARNError as e:
    print(e)  # Invalid ARN format: invalid
```

---

## `ARN`

Frozen dataclass that holds all parsed ARN data.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `aws_partition` | `str` | AWS partition, such as `aws`, `aws-cn`, or `aws-us-gov`. |
| `aws_service` | `str` | AWS service name from the ARN. |
| `aws_region` | `str` | AWS region; may be empty for global resources. |
| `aws_account` | `str` | AWS account ID; may be empty for some global or public resources. |
| `resource_type` | `str` | Canonical resource type from generated AWS patterns. |
| `resource_types` | `list[str]` | All known aliases for this resource type. |
| `attributes` | `dict[str, str]` | Captured attributes from the service-specific ARN pattern. |
| `aws_sdk_service` | `str \| None` | Primary boto3 client name for the resource service. |
| `cloudformation_resource` | `str \| None` | CloudFormation resource type, such as `AWS::Lambda::Function`. |
| `tagging_resource` | `str \| None` | Resource Groups Tagging API type. |

### Properties

#### `resource_id`

`str` — Resource identifier extracted with heuristics.

Priority:
1. Captured attribute ending in `Id` (checked from end).
2. Captured attribute ending in `Name`.
3. Last non-standard captured attribute.

```python
resource = arnmatch("arn:aws:iam::123456789012:role/Admin")
print(resource.resource_id)  # Admin
```

#### `resource_name`

`str` — Resource name extracted with heuristics.

Priority:
1. Captured attribute ending in `Name` (checked from end).
2. Falls back to `resource_id`.

```python
resource = arnmatch("arn:aws:s3:::my-bucket")
print(resource.resource_name)  # my-bucket
```

#### `aws_sdk_services`

`list[str]` — All boto3 client names mapped to the AWS service.

Some services map to multiple clients. For example, `elasticloadbalancing` returns `['elb', 'elbv2']`.

```python
resource = arnmatch("arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb")
print(resource.aws_sdk_services)  # ['elb', 'elbv2']
```

### Methods

#### `client(session=None)`

Return a boto3 client for the resource service.

**Parameters**

- `session` (`boto3.Session \| None`, optional): A boto3 Session. If `None`, a default session is created.

**Returns**

- `boto3.client`: A client for `aws_sdk_service`.

**Raises**

- `ValueError`: If no SDK service mapping exists for this ARN's service.

**Example**

```python
import boto3
from arnmatch import arnmatch

resource = arnmatch("arn:aws:lambda:us-east-1:123456789012:function:my-function")
session = boto3.Session(region_name=resource.aws_region)
client = resource.client(session=session)

client.get_function(FunctionName=resource.resource_name)
```

> **Note:** `client()` requires `boto3` to be installed in your environment. The parser itself has no runtime dependencies.
