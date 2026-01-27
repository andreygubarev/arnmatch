"""ARN pattern matching using regex patterns."""

import sys
from dataclasses import dataclass
from functools import cached_property

from .patterns import ARN_PATTERNS

# Standard groups that are not resource-specific
STANDARD_GROUPS = {"Partition", "Region", "Account"}


class ARNMatchError(ValueError):
    """Raised when ARN cannot be matched."""

    pass


@dataclass(frozen=True)
class ARNMatch:
    """Result of matching an ARN against patterns."""

    partition: str
    service: str
    region: str
    account: str
    resource_type: str  # canonical type (from AWS docs)
    resource_type_aliases: list[str]  # all known names including Resource Explorer
    groups: dict[str, str]

    @cached_property
    def resource_id(self) -> str:
        """Extract resource ID using heuristics.

        Priority (from end, more specific groups come last):
        1. Group ending with 'Id' (InstanceId, CertificateId, KeyId)
        2. Group ending with 'Name' as fallback
        3. Last non-standard group
        """
        resource_groups = list(self.groups.items())
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
        resource_groups = list(self.groups.items())
        resource_groups = [(k, v) for k, v in resource_groups if k not in STANDARD_GROUPS]

        # Look for *Name (from end)
        for key, value in reversed(resource_groups):
            if key.endswith("Name"):
                return value

        # Fall back to resource_id
        return self.resource_id


def arnmatch(arn: str) -> ARNMatch:
    """Match ARN against patterns.

    Returns ARNMatch with all captured groups.

    Raises:
        ARNMatchError: If ARN cannot be matched.
    """
    parts = arn.split(":", 5)
    if len(parts) != 6 or parts[0] != "arn":
        raise ARNMatchError(f"Invalid ARN format: {arn}")

    _, partition, service, region, account, _ = parts

    if service not in ARN_PATTERNS:
        raise ARNMatchError(f"Unknown service: {service}")

    for regex, type_names in ARN_PATTERNS[service]:
        match = regex.match(arn)
        if match:
            return ARNMatch(
                partition=partition,
                service=service,
                region=region,
                account=account,
                resource_type=type_names[0],  # canonical
                resource_type_aliases=type_names,  # all known names
                groups=match.groupdict(),
            )

    raise ARNMatchError(f"No pattern matched ARN: {arn}")


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: arnmatch <arn>", file=sys.stderr)
        sys.exit(1)

    arn = sys.argv[1]
    try:
        result = arnmatch(arn)
        print(f"service: {result.service}")
        print(f"region: {result.region}")
        print(f"account: {result.account}")
        print(f"resource_type: {result.resource_type}")
        print(f"resource_id: {result.resource_id}")
        print(f"resource_name: {result.resource_name}")
    except ARNMatchError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
