# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3", "requests"]
# ///

"""Maps ARN service names to Tagging API resource types."""

import collections
import json
from pathlib import Path

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

from utils import botocore_metadata, load_rules


class TagServiceIndexer:
    """Builds mapping from ARN service names to Tagging API resource types."""

    CACHE_FILE = Path(__file__).parent / "cache" / "TaggingAPIResources.json"
    CACHE_SERVICES_FILE = Path(__file__).parent / "cache" / "TaggingAPIServices.json"

    # Excluded tagging services (no SDK mapping)
    EXCLUDES = set(load_rules("tag_excludes.json"))

    # Manual mapping: tagging service -> SDK service
    OVERRIDES = load_rules("tag_overrides.json")

    def download(self, region="us-east-1") -> list[str]:
        """Fetch and cache Tagging API resource types."""
        if self.CACHE_FILE.exists():
            return json.loads(self.CACHE_FILE.read_text())

        session = boto3.Session()
        credentials = session.get_credentials()

        url = f"https://resource-groups.{region}.amazonaws.com/resource-types-list"
        resource_types = []
        next_token = None

        while True:
            payload = {"QueryType": "TAG_FILTERS_1_0", "MaxResults": 50}
            if next_token:
                payload["NextToken"] = next_token

            body = json.dumps(payload)
            request = AWSRequest(
                method="POST",
                url=url,
                headers={"Content-Type": "application/json"},
                data=body,
            )
            SigV4Auth(credentials, "resource-groups", region).add_auth(request)

            response = requests.post(url, headers=dict(request.headers), data=body)
            response.raise_for_status()
            data = response.json()

            resource_types.extend(data.get("ResourceTypes", []))
            next_token = data.get("NextToken")
            if not next_token:
                break

        resource_types = sorted(set(resource_types))

        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.CACHE_FILE.write_text(json.dumps(resource_types, indent=2))

        return resource_types

    @property
    def tagging_resources(self) -> list[str]:
        """Get all Tagging API resource types."""
        return self.download()

    @property
    def tagging_services(self) -> list[str]:
        """Get unique services from Tagging API resource types."""
        services = {rt.split("::")[1] for rt in self.tagging_resources}
        services = {s for s in services if s not in self.EXCLUDES}
        return sorted(services)

    def sdk_to_names(self):
        """Build SDK service -> normalized names mapping."""
        metadata = botocore_metadata()

        def normalize(name):
            return name.lower().replace("-", "").replace(" ", "")

        sdk_to_names = collections.defaultdict(set)
        for sdk, meta in metadata.items():
            sdk_to_names[sdk].add(normalize(sdk))
            sdk_to_names[sdk].add(normalize(meta["endpointPrefix"]))
            sdk_to_names[sdk].add(normalize(meta["serviceId"]))
            sdk_to_names[sdk].add(normalize(meta["serviceFullName"]))
            if meta.get("signingName"):
                sdk_to_names[sdk].add(normalize(meta["signingName"]))

        return sdk_to_names

    def process(self, arn_to_sdk):
        """Build ARN service -> tagging services mapping."""
        sdk_to_names = self.sdk_to_names()

        def normalize(name):
            return name.lower().replace("-", "").replace(" ", "")

        # Map tagging service -> SDK service
        tag_to_sdk = {}
        direct_count = 0
        override_count = 0
        unmatched = []

        for tag_svc in self.tagging_services:
            ntag = normalize(tag_svc)

            # Check override first
            if tag_svc in self.OVERRIDES:
                tag_to_sdk[tag_svc] = self.OVERRIDES[tag_svc]
                override_count += 1
                continue

            # Try matching via botocore metadata
            matched = False
            for sdk, names in sdk_to_names.items():
                if ntag in names:
                    tag_to_sdk[tag_svc] = sdk
                    direct_count += 1
                    matched = True
                    break

            if not matched:
                unmatched.append(tag_svc)

        if unmatched:
            print(f"Unmatched tagging services: {unmatched}")
            raise ValueError(f"No SDK mapping for tagging services: {unmatched}")

        # Invert: SDK -> tagging services
        sdk_to_tag = collections.defaultdict(list)
        for tag_svc, sdk in tag_to_sdk.items():
            sdk_to_tag[sdk].append(tag_svc)

        # Map ARN service -> tagging services (via SDK)
        arn_to_tag = {}
        for arn_svc, sdks in arn_to_sdk.items():
            arn_to_tag[arn_svc] = []
            for sdk in sdks:
                arn_to_tag[arn_svc].extend(sdk_to_tag.get(sdk, []))

        # Save
        arn_to_tag = dict(sorted(arn_to_tag.items()))
        self.CACHE_SERVICES_FILE.write_text(json.dumps(arn_to_tag, indent=2))

        self.metrics = {
            "tagging_services_total": len(self.tagging_services),
            "direct_match": direct_count,
            "override": override_count,
            "excluded": len(self.EXCLUDES),
            "mapped_to_arn": len([s for s in arn_to_tag.values() if s]),
        }

        return arn_to_tag


if __name__ == "__main__":
    indexer = TagServiceIndexer()
    resources = indexer.tagging_resources
    services = indexer.tagging_services
    print(f"Tagging API: {len(resources)} resources, {len(services)} services")

    # Load SDK mapping and run process
    sdk_cache = Path(__file__).parent / "cache" / "SDKServices.json"
    if sdk_cache.exists():
        arn_to_sdk = json.loads(sdk_cache.read_text())
        arn_to_tag = indexer.process(arn_to_sdk)
        print(f"Mapped {len([v for v in arn_to_tag.values() if v])} ARN services to tagging")
