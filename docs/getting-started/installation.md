# Installation

`arnmatch` requires Python 3.10 or later and has zero runtime dependencies for parsing.

## Install from PyPI

```bash
pip install arnmatch
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install arnmatch
```

## Verify the installation

```bash
arnmatch "arn:aws:s3:::my-bucket"
```

Expected output:

```text
aws_service: s3
aws_sdk_service: s3
aws_sdk_services: s3
aws_region:
aws_account:
resource_type: bucket
resource_id: my-bucket
resource_name: my-bucket
cloudformation_resource: AWS::S3::Bucket
tagging_resource: AWS::S3::Bucket
```

## Optional: boto3 for the client helper

The `ARN.client()` method requires `boto3` in your environment. It is not installed automatically because arnmatch parsing itself has no runtime dependencies.

```bash
pip install boto3
```

## Next steps

- Follow the [Quickstart](quickstart.md) to parse ARNs and use the results.
- Read the [Python API reference](../reference/api.md) for detailed usage.
