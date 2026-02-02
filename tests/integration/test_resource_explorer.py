#!/usr/bin/env python3
"""
Integration test using AWS Resource Explorer 2 to validate arnmatch against real ARNs.

This test is NOT part of the automated test suite. Run it manually:
    uv run tests/integration/test_resource_explorer.py

Prerequisites:
    - AWS credentials configured (via environment, profile, or IAM role)
    - Resource Explorer enabled in your AWS account with an aggregator index
    - boto3 installed (add to dev dependencies or install separately)

The test fetches all resources from Resource Explorer and attempts to parse
each ARN with arnmatch, reporting any failures.
"""

import sys
from collections import defaultdict

import boto3

from arnmatch import arnmatch


def fetch_resources():
    """Fetch all resources from AWS Resource Explorer 2."""
    client = boto3.client("resource-explorer-2")
    paginator = client.get_paginator("list_resources")

    resources = []
    for page in paginator.paginate():
        for resource in page.get("Resources", []):
            arn = resource.get("Arn")
            if arn:
                resources.append(arn)
        print(f"Fetched {len(resources)} resources...")

    return resources


def test_arns(arns):
    """Test arnmatch against all ARNs, return results."""
    results = {
        "success": [],
        "failed": [],
        "by_service": defaultdict(lambda: {"success": 0, "failed": 0, "types": {}}),
    }

    for arn in arns:
        parsed = arnmatch(arn)
        if parsed is None:
            results["failed"].append(arn)
            service = arn.split(":")[2]
            results["by_service"][service]["failed"] += 1
        else:
            results["success"].append((arn, parsed))
            svc = results["by_service"][parsed.aws_service]
            svc["success"] += 1
            if parsed.resource_type not in svc["types"]:
                svc["types"][parsed.resource_type] = {
                    "sdk": parsed.aws_sdk_service,
                    "cfn": parsed.cloudformation_resource,
                }

    return results


def print_report(results):
    """Print a summary report of the test results."""
    total = len(results["success"]) + len(results["failed"])
    success_count = len(results["success"])
    failed_count = len(results["failed"])

    print("\n" + "=" * 60)
    print("ARNMATCH RESOURCE EXPLORER INTEGRATION TEST")
    print("=" * 60)
    print(f"\nTotal ARNs tested: {total}")
    print(f"Successful:        {success_count} ({100*success_count/total:.1f}%)" if total else "Successful: 0")
    print(f"Failed:            {failed_count} ({100*failed_count/total:.1f}%)" if total else "Failed: 0")

    if results["failed"]:
        print("\n" + "-" * 60)
        print("FAILED ARNs:")
        print("-" * 60)
        for arn in results["failed"]:
            print(f"  {arn}")

    print("\n" + "-" * 70)
    print(f"{'SERVICE':<25} {'ARNS':>8} {'TYPES':>8} {'SDK':>10} {'CFN':>10}")
    print("-" * 70)
    missing_sdk = []
    missing_cfn = []
    for service in sorted(results["by_service"].keys()):
        stats = results["by_service"][service]
        total_arns = stats["success"] + stats["failed"]
        types = stats["types"]
        total_types = len(types)
        with_sdk = sum(1 for t in types.values() if t["sdk"])
        with_cfn = sum(1 for t in types.values() if t["cfn"])
        sdk_str = f"{with_sdk}/{total_types}"
        cfn_str = f"{with_cfn}/{total_types}"
        print(f"  {service:<23} {total_arns:>8} {total_types:>8} {sdk_str:>10} {cfn_str:>10}")
        for rtype, info in types.items():
            if not info["sdk"]:
                missing_sdk.append(f"{service}:{rtype}")
            if not info["cfn"]:
                missing_cfn.append(f"{service}:{rtype}")

    if missing_sdk:
        print("\n" + "-" * 70)
        print(f"MISSING SDK ({len(missing_sdk)}):")
        print("-" * 70)
        for item in sorted(missing_sdk):
            print(f"  {item}")

    if missing_cfn:
        print("\n" + "-" * 70)
        print(f"MISSING CFN ({len(missing_cfn)}):")
        print("-" * 70)
        for item in sorted(missing_cfn):
            print(f"  {item}")

    print("\n" + "=" * 60)
    return failed_count == 0


def main():
    print("Fetching resources from AWS Resource Explorer 2...")
    arns = fetch_resources()
    print(f"Found {len(arns)} resources. Testing arnmatch...")
    results = test_arns(arns)
    success = print_report(results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
