# Mappings reference

`arnmatch` maps every parsed ARN to three external AWS type systems:

- **CloudFormation resource types** — for infrastructure-as-code correlation.
- **Resource Groups Tagging API types** — for tag-based resource queries.
- **boto3 SDK service names** — for programmatic API access.

These mappings are generated automatically from AWS metadata and reconciled with override rules. Coverage varies by service.

## CloudFormation mapping

The `cloudformation_resource` field contains the CloudFormation resource type when a reliable mapping exists.

```python
from arnmatch import arnmatch

resource = arnmatch("arn:aws:lambda:us-east-1:123456789012:function:my-function")
print(resource.cloudformation_resource)  # AWS::Lambda::Function
```

### Coverage

- Core infrastructure services (EC2, VPC, ELB) have high coverage (80%+).
- Storage services have medium coverage (~70%).
- ML/AI services (SageMaker, Bedrock) and newer services may have lower coverage because CloudFormation support lags behind API releases.
- Async operations, tasks, jobs, and sub-resources often do not map to CloudFormation because CFN manages persistent infrastructure, not operations.

When no mapping exists, `cloudformation_resource` is `None`.

## Resource Groups Tagging API mapping

The `tagging_resource` field contains the Tagging API resource type used with APIs such as `GetResources`.

```python
resource = arnmatch("arn:aws:rds:us-east-1:123456789012:db:my-database")
print(resource.tagging_resource)  # AWS::RDS::DBInstance
```

When no mapping exists, `tagging_resource` is `None`.

## boto3 SDK mapping

### Primary service

`aws_sdk_service` returns the primary boto3 client name for the ARN's service.

```python
resource = arnmatch("arn:aws:lambda:us-east-1:123456789012:function:my-function")
print(resource.aws_sdk_service)  # lambda
```

### All services

`aws_sdk_services` returns every boto3 client mapped to the service. Some AWS services expose multiple API versions or sub-services.

```python
resource = arnmatch("arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb")
print(resource.aws_sdk_services)  # ['elb', 'elbv2']
```

When no SDK mapping exists, `aws_sdk_service` is `None` and `aws_sdk_services` is an empty list.

## Using mappings together

A common workflow is to parse an ARN, then use the mapping fields to interact with AWS:

```python
import boto3
from arnmatch import arnmatch

arn = "arn:aws:lambda:us-east-1:123456789012:function:my-function"
resource = arnmatch(arn)

# Use the CloudFormation type for asset correlation
print(resource.cloudformation_resource)

# Use the Tagging API type for tag queries
print(resource.tagging_resource)

# Use the SDK service to call AWS APIs
session = boto3.Session(region_name=resource.aws_region)
client = resource.client(session=session)
```
