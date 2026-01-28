# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///

"""Maps ARN service names to CloudFormation resource types."""

import json
from pathlib import Path

import requests

CLOUDFORMATION_SPEC = "https://d1uauaxba7bl26.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json"


class CFNServiceIndexer:
    """Builds mapping from ARN service names to CloudFormation resource types."""

    CACHE_FILE = Path(__file__).parent / "cache" / "CloudFormationResourceSpecification.json"
    CACHE_SERVICES_FILE = Path(__file__).parent / "cache" / "CloudFormationServices.json"

    # Discontinued/EOL services (lowercase for comparison)
    EXCLUDES_DISCONTINUED = {
        "codestar",
        "lookoutvision",
        "opsworks",
        "qldb",
        "robomaker",
    }

    def download(self) -> dict:
        """Download and cache CloudFormation Resource Specification."""
        if self.CACHE_FILE.exists():
            return json.loads(self.CACHE_FILE.read_text())

        resp = requests.get(CLOUDFORMATION_SPEC, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.CACHE_FILE.write_text(json.dumps(data))
        return data

    def process(self) -> list[str]:
        """Download spec and return unique service names."""
        spec = self.download()
        services = {rt.split("::")[1] for rt in spec.get("ResourceTypes", {}).keys()}
        services = sorted(s for s in services if s.lower() not in self.EXCLUDES_DISCONTINUED)
        self.CACHE_SERVICES_FILE.write_text(json.dumps(services, indent=2))
        return services


if __name__ == "__main__":
    CFNServiceIndexer().process()
