# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///

"""
Verify that all ARN patterns from AWS CloudFormation IAM Policy Validator
are covered by our generated arn_resources.json.

Usage:
    cd codegen && uv run verify_cfn_coverage.py
"""

import json
import re
from pathlib import Path

import requests

CFN_ARN_MAP_URL = "https://raw.githubusercontent.com/awslabs/aws-cloudformation-iam-policy-validator/refs/heads/main/cfn_policy_validator/parsers/utils/cfn_to_arn_map.json"
BUILD_DIR = Path(__file__).parent / "build"


def normalize_pattern(arn_pattern: str) -> str:
    """Normalize ARN pattern by replacing variable names with a placeholder.

    This allows structural comparison regardless of variable naming differences.
    e.g., '${CertificateId}' and '${ResourceId}' both become '${*}'
    """
    return re.sub(r"\$\{[^}]+\}", "${*}", arn_pattern)


def extract_cfn_patterns(cfn_map: dict) -> dict[str, set[str]]:
    """Extract all unique ARN patterns from cfn_to_arn_map.json.

    Returns: dict mapping service_prefix -> set of ARN patterns
    """
    patterns = {}  # service -> set of patterns

    def process_value(value_obj):
        if value_obj is None:
            return
        if isinstance(value_obj, dict) and "Value" in value_obj:
            arn = value_obj["Value"]
            service = value_obj.get("ServicePrefix", "")
            if arn and service:
                if service not in patterns:
                    patterns[service] = set()
                patterns[service].add(arn)

    for cfn_service, resources in cfn_map.items():
        if not isinstance(resources, dict):
            continue
        for resource_type, outputs in resources.items():
            if not isinstance(outputs, dict):
                continue
            for output_name, value_obj in outputs.items():
                process_value(value_obj)

    return patterns


def load_arn_resources() -> dict[str, set[str]]:
    """Load arn_resources.json and return service -> set of patterns."""
    resources_path = BUILD_DIR / "arn_resources.json"
    if not resources_path.exists():
        raise FileNotFoundError(f"Run codegen first: {resources_path}")

    with open(resources_path) as f:
        resources = json.load(f)

    patterns = {}
    for r in resources:
        # Extract service from ARN pattern (3rd colon-separated part)
        parts = r["arn_pattern"].split(":")
        service = parts[2] if len(parts) >= 3 else ""
        if service not in patterns:
            patterns[service] = set()
        patterns[service].add(r["arn_pattern"])

    return patterns


def find_missing_patterns(cfn_patterns: dict, our_patterns: dict) -> list[tuple[str, str]]:
    """Find CFN patterns not covered by our patterns.

    Uses normalized comparison to handle variable name differences.
    Returns list of (service, arn_pattern) tuples.
    """
    missing = []

    # Build normalized lookup for our patterns
    our_normalized = {}  # service -> set of normalized patterns
    for service, arns in our_patterns.items():
        our_normalized[service] = {normalize_pattern(arn) for arn in arns}

    for service, cfn_arns in cfn_patterns.items():
        our_service_normalized = our_normalized.get(service, set())

        for arn in cfn_arns:
            normalized = normalize_pattern(arn)
            if normalized not in our_service_normalized:
                missing.append((service, arn))

    return sorted(missing)


def main():
    print("Fetching cfn_to_arn_map.json...")
    resp = requests.get(CFN_ARN_MAP_URL)
    resp.raise_for_status()
    cfn_map = resp.json()

    print("Loading arn_resources.json...")
    our_patterns = load_arn_resources()

    print("Extracting CFN patterns...")
    cfn_patterns = extract_cfn_patterns(cfn_map)

    cfn_count = sum(len(arns) for arns in cfn_patterns.values())
    our_count = sum(len(arns) for arns in our_patterns.values())
    print(f"CFN patterns: {cfn_count} across {len(cfn_patterns)} services")
    print(f"Our patterns: {our_count} across {len(our_patterns)} services")

    print("\nChecking coverage...")
    missing = find_missing_patterns(cfn_patterns, our_patterns)

    if not missing:
        print("\nAll CFN patterns are covered!")
    else:
        print(f"\nMissing {len(missing)} patterns:\n")
        current_service = None
        for service, arn in missing:
            if service != current_service:
                print(f"\n{service}:")
                current_service = service
            print(f"  {arn}")

    return len(missing)


if __name__ == "__main__":
    exit(main())
