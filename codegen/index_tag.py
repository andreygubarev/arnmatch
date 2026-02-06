# /// script
# requires-python = ">=3.11"
# dependencies = ["boto3", "requests"]
# ///

"""Maps ARN service names to Tagging API resource types."""

import json
from pathlib import Path

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests


class TagServiceIndexer:
    """Builds mapping from ARN service names to Tagging API resource types."""

    CACHE_FILE = Path(__file__).parent / "cache" / "TaggingAPIResources.json"

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
        return sorted(services)


if __name__ == "__main__":
    indexer = TagServiceIndexer()
    resources = indexer.tagging_resources
    services = indexer.tagging_services
    print(f"Tagging API: {len(resources)} resources, {len(services)} services")
