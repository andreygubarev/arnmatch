# CLI reference

`arnmatch` installs a command-line tool named `arnmatch`.

## Usage

```bash
arnmatch <arn>
```

## Arguments

| Argument | Description |
|----------|-------------|
| `<arn>` | The AWS ARN to parse. |

## Output

The CLI prints one line per field:

```text
aws_service: <service>
aws_sdk_service: <sdk-service>
aws_sdk_services: <sdk-service-1>,<sdk-service-2>
aws_region: <region>
aws_account: <account>
resource_type: <type>
resource_id: <id>
resource_name: <name>
cloudformation_resource: <cfn-type>
tagging_resource: <tagging-type>
```

Fields with no value are printed as an empty line after the colon.

## Examples

### Lambda function

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

### S3 bucket

```bash
arnmatch "arn:aws:s3:::my-bucket"
```

Output:

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

### IAM role (global resource)

```bash
arnmatch "arn:aws:iam::123456789012:role/Admin"
```

Output:

```text
aws_service: iam
aws_sdk_service: iam
aws_sdk_services: iam
aws_region:
aws_account: 123456789012
resource_type: iam-role
resource_id: Admin
resource_name: Admin
cloudformation_resource: AWS::IAM::Role
tagging_resource: AWS::IAM::Role
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success. |
| `1` | Invalid ARN format, unknown service, or no matching pattern. Error message is printed to stderr. |

## Error example

```bash
arnmatch "not-an-arn"
```

Stderr:

```text
Error: Invalid ARN format: not-an-arn
```
