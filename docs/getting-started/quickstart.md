# Quickstart

This guide shows you how to parse an AWS ARN, extract resource details, and map them to CloudFormation and boto3.

## Prerequisites

- Python 3.10 or later
- `arnmatch` installed (`pip install arnmatch`)

## Parse an ARN with the CLI

Run arnmatch with any valid AWS ARN:

```bash
arnmatch "arn:aws:lambda:us-east-1:123456789012:function:my-function"
```

Output:

```text
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

## Parse an ARN in Python

```python
from arnmatch import arnmatch

result = arnmatch("arn:aws:lambda:us-east-1:123456789012:function:my-function")

print(result.aws_service)              # lambda
print(result.aws_region)               # us-east-1
print(result.aws_account)              # 123456789012
print(result.resource_type)            # function
print(result.resource_id)              # my-function
print(result.cloudformation_resource)  # AWS::Lambda::Function
print(result.tagging_resource)         # AWS::Lambda::Function
print(result.aws_sdk_service)          # lambda
```

## Get a boto3 client from an ARN

If you have `boto3` installed, you can create a client directly from the parsed ARN:

```python
import boto3
from arnmatch import arnmatch

arn = "arn:aws:lambda:us-east-1:123456789012:function:my-function"
resource = arnmatch(arn)

session = boto3.Session(region_name=resource.aws_region)
client = resource.client(session=session)

# Now use the client
client.get_function(FunctionName=resource.resource_name)
```

## Next steps

- Learn [how arnmatch works](../concepts/how-it-works.md).
- Browse the [Python API reference](../reference/api.md) for all fields and methods.
- See the [CLI reference](../reference/cli.md) for command-line options.
