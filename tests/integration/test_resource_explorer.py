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
        "by_service": defaultdict(lambda: {"success": 0, "failed": 0}),
    }

    for arn in arns:
        parsed = arnmatch(arn)
        if parsed is None:
            results["failed"].append(arn)
            service = arn.split(":")[2]
            results["by_service"][service]["failed"] += 1
        else:
            results["success"].append((arn, parsed))
            results["by_service"][parsed.aws_service]["success"] += 1

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
        for arn, error in results["failed"]:
            print(f"  {arn}")
            print(f"    Error: {error}")

    print("\n" + "-" * 60)
    print("RESULTS BY SERVICE:")
    print("-" * 60)
    for service in sorted(results["by_service"].keys()):
        stats = results["by_service"][service]
        total_svc = stats["success"] + stats["failed"]
        status = "OK" if stats["failed"] == 0 else "FAIL"
        print(f"  {service:30} {stats['success']:4}/{total_svc:<4} [{status}]")

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
