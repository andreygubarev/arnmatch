# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "boto3"]
# ///

"""Maps ARN service names to CloudFormation resource types."""

import collections
import json
from pathlib import Path

import requests

from utils import botocore_metadata, load_rules

CLOUDFORMATION_SPEC = "https://d1uauaxba7bl26.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json"


class CFNServiceIndexer:
    """Builds mapping from ARN service names to CloudFormation resource types."""

    CACHE_FILE = Path(__file__).parent / "cache" / "CloudFormationResourceSpecification.json"
    CACHE_SERVICES_FILE = Path(__file__).parent / "cache" / "CloudFormationServices.json"
    CACHE_RESOURCES_FILE = Path(__file__).parent / "cache" / "CloudFormationResources.json"

    # Excluded CFN services by category
    _EXCLUDES = load_rules("cfn_excludes.json")
    EXCLUDES = set(_EXCLUDES["discontinued"]) | set(_EXCLUDES["no_sdk"]) | set(_EXCLUDES["no_arn"])

    # Manual mapping: CFN service -> SDK service (for unmatched)
    OVERRIDES = load_rules("cfn_overrides.json")


    def download(self):
        """Download and cache CloudFormation Resource Specification."""
        if self.CACHE_FILE.exists():
            return json.loads(self.CACHE_FILE.read_text())

        resp = requests.get(CLOUDFORMATION_SPEC, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.CACHE_FILE.write_text(json.dumps(data))
        return data

    @property
    def cloudformation_resources(self) -> list[str]:
        """Get all CloudFormation resource types from the specification."""
        data = self.download()
        resources = list(sorted(data["ResourceTypes"].keys()))
        # create service -> [resource_types] mapping
        service_to_resources = collections.defaultdict(list)
        for service in self.cloudformation_services:
            service_resources = [
                rt for rt in resources if rt.startswith(f"AWS::{service}::")
            ]
            if not service_resources:
                raise ValueError(f"No resources found for CFN service: {service}")
            service_to_resources[service] = service_resources
        return service_to_resources

    @property
    def cloudformation_services(self) -> list[str]:
        """Get all CloudFormation services from the specification."""
        data = self.download()
        services = {rt.split("::")[1] for rt in data["ResourceTypes"].keys()}
        services = {s for s in services if s.lower() not in self.EXCLUDES}
        return list(sorted(services))

    def save(self, services):
        services = dict(sorted(services.items()))
        self.CACHE_SERVICES_FILE.write_text(json.dumps(services, indent=2))

    def sdk_to_names(self):
        metadata = botocore_metadata()

        def normalize(name):
            return name.lower().replace("-", "").replace(" ", "")

        sdk_to_names = collections.defaultdict(set)
        for sdk, names in metadata.items():
            sdk_to_names[sdk].add(normalize(sdk))
            sdk_to_names[sdk].add(normalize(names["endpointPrefix"]))
            sdk_to_names[sdk].add(normalize(names["serviceId"]))
            sdk_to_names[sdk].add(normalize(names["serviceFullName"]))
            if names.get("signingName"):
                sdk_to_names[sdk].add(normalize(names["signingName"]))

        return sdk_to_names


    def process(self, arn_to_sdk):
        """Build ARN service -> CFN services mapping."""
        self.CACHE_RESOURCES_FILE.write_text(json.dumps(self.cloudformation_resources, indent=2))

        sdk_to_names = self.sdk_to_names()

        cfn_to_sdk = {}
        direct_count = 0
        override_count = 0

        def normalize(name):
            return name.lower().replace("-", "").replace(" ", "")

        for cfn in self.cloudformation_services:
            ncfn = normalize(cfn)
            for sdk, names in sdk_to_names.items():
                if ncfn in names:
                    cfn_to_sdk[cfn] = sdk
                    direct_count += 1
                    break
            else:
                if cfn in self.OVERRIDES:
                    cfn_to_sdk[cfn] = self.OVERRIDES[cfn]
                    override_count += 1
                    continue
                raise ValueError(f"No SDK mapping for CFN service: {cfn}")

        sdk_to_cfn = {}
        for cfn, sdk in cfn_to_sdk.items():
            sdk_to_cfn.setdefault(sdk, []).append(cfn)

        arn_to_cfn = {}
        for arn, sdks in arn_to_sdk.items():
            arn_to_cfn[arn] = []
            for sdk in sdks:
                for cfn in sdk_to_cfn.get(sdk, []):
                    arn_to_cfn[arn].append(cfn)

        cloudformation_services = {s for services in arn_to_cfn.values() for s in services}
        diff = set(self.cloudformation_services) - cloudformation_services
        if diff:
            raise ValueError(f"CFN services with no ARN mapping: {diff}")

        self.save(arn_to_cfn)

        self.metrics = {
            "cfn_services_total": len(self.cloudformation_services),
            "direct_match": direct_count,
            "override": override_count,
            "excluded": len(self.EXCLUDES),
            "mapped_to_arn": len([s for s in arn_to_cfn.values() if s]),
        }

        return arn_to_cfn


if __name__ == "__main__":
    CFNServiceIndexer().process({})
