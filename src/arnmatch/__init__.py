"""ARN pattern matching using regex patterns."""

__version__ = "2026.01.2"

import sys
from dataclasses import dataclass
from functools import cached_property

from .arn_patterns import ARN_PATTERNS, AWS_SDK_SERVICES, AWS_SDK_RESOURCE_OVERRIDES

# Standard groups that are not resource-specific
STANDARD_GROUPS = {"Partition", "Region", "Account"}


class ARNError(ValueError):
    """Raised when ARN cannot be parsed or matched."""

    pass


@dataclass(frozen=True)
class ARN:
    """Parsed ARN with structured data and captured groups."""

    aws_partition: str
    aws_service: str
    aws_region: str
    aws_account: str
    resource_type: str  # canonical type (from AWS docs)
    resource_types: list[str]  # all known names including Resource Explorer
    attributes: dict[str, str]

    @cached_property
    def resource_id(self) -> str:
        """Extract resource ID using heuristics.

        Priority (from end, more specific groups come last):
        1. Group ending with 'Id' (InstanceId, CertificateId, KeyId)
        2. Group ending with 'Name' as fallback
        3. Last non-standard group
        """
        resource_groups = list(self.attributes.items())
        resource_groups = [(k, v) for k, v in resource_groups if k not in STANDARD_GROUPS]

        # Look for *Id (from end)
        for key, value in reversed(resource_groups):
            if key.endswith("Id"):
                return value

        # Fall back to *Name (from end)
        for key, value in reversed(resource_groups):
            if key.endswith("Name"):
                return value

        # Last resort: last group value
        if resource_groups:
            return resource_groups[-1][1]

        return ""

    @cached_property
    def resource_name(self) -> str:
        """Extract resource name using heuristics.

        Priority (from end, more specific groups come last):
        1. Group ending with 'Name' (FunctionName, BucketName, StackName)
        2. Falls back to resource_id
        """
        resource_groups = list(self.attributes.items())
        resource_groups = [(k, v) for k, v in resource_groups if k not in STANDARD_GROUPS]

        # Look for *Name (from end)
        for key, value in reversed(resource_groups):
            if key.endswith("Name"):
                return value

        # Fall back to resource_id
        return self.resource_id

    @cached_property
    def aws_sdk_services(self):
        """Get AWS SDK (boto3) client names for this resource's service.

        Returns list of client names that can interact with this resource type.
        May return multiple clients for services with versioned APIs
        (e.g., ['elb', 'elbv2'] for elasticloadbalancing).
        Returns empty list if no SDK client exists.
        """
        return AWS_SDK_SERVICES.get(self.aws_service, [])

    @cached_property
    def aws_sdk_service(self) -> str | None:
        """Get the specific AWS SDK (boto3) client for this resource type.

        Returns the SDK client name if determinable, or None if ambiguous.
        For services with multiple SDK clients (e.g., elasticloadbalancing),
        uses resource type to determine the specific client.
        """
        sdk_clients = self.aws_sdk_services

        if not sdk_clients:
            return None

        if len(sdk_clients) == 1:
            return sdk_clients[0]

        # Multiple SDKs - check resource type overrides
        if self.aws_service in AWS_SDK_RESOURCE_OVERRIDES:
            for pattern, sdk_client in AWS_SDK_RESOURCE_OVERRIDES[self.aws_service]:
                if self.resource_type == pattern or self.resource_type.startswith(pattern + "/"):
                    return sdk_client

        return None


def arnmatch(arn: str) -> ARN:
    """Match ARN against patterns.

    Returns ARNMatch with all captured groups.

    Raises:
        ARNMatchError: If ARN cannot be matched.
    """
    parts = arn.split(":", 5)
    if len(parts) != 6 or parts[0] != "arn":
        raise ARNError(f"Invalid ARN format: {arn}")

    _, partition, service, region, account, _ = parts

    if service not in ARN_PATTERNS:
        raise ARNError(f"Unknown service: {service}")

    for regex, type_names in ARN_PATTERNS[service]:
        match = regex.match(arn)
        if match:
            return ARN(
                aws_partition=partition,
                aws_service=service,
                aws_region=region,
                aws_account=account,
                resource_type=type_names[0],  # canonical
                resource_types=type_names,  # all known names
                attributes=match.groupdict(),
            )

    raise ARNError(f"No pattern matched ARN: {arn}")


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: arnmatch <arn>", file=sys.stderr)
        sys.exit(1)

    arn = sys.argv[1]
    try:
        result = arnmatch(arn)
        print(f"aws_service: {result.aws_service}")
        print(f"aws_sdk_service: {result.aws_sdk_service}")
        print(f"aws_sdk_services: {','.join(result.aws_sdk_services)}")
        print(f"aws_region: {result.aws_region}")
        print(f"aws_account: {result.aws_account}")
        print(f"resource_type: {result.resource_type}")
        print(f"resource_id: {result.resource_id}")
        print(f"resource_name: {result.resource_name}")
    except ARNError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
