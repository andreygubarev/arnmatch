"""Maps ARN resource types to CloudFormation resource types."""

import json
from pathlib import Path


class CFNResourceIndexer:
    """Maps ARN resources to CloudFormation resource types."""

    CACHE_SERVICES_FILE = Path(__file__).parent / "cache" / "CloudFormationServices.json"
    CACHE_RESOURCES_FILE = Path(__file__).parent / "cache" / "CloudFormationResources.json"

    @property
    def cloudformation_services(self):
        """Load CFN service list."""
        cloudformation_services = json.loads(self.CACHE_SERVICES_FILE.read_text())
        return cloudformation_services

    @property
    def cloudformation_resources(self):
        """Load CFN service -> CFN resource types mapping."""
        cloudformation_resources = json.loads(self.CACHE_RESOURCES_FILE.read_text())
        resources = {}
        for name, services in self.cloudformation_services.items():
            resources[name] = []
            for service in services:
                resources[name].extend(cloudformation_resources.get(service, []))
            resources[name] = sorted(set(resources[name]))
        return resources

    def normalize_name(self, s):
        """Normalize resource type name for comparison."""
        return s.strip().lower().replace("-", "").replace("_", "").replace(" ", "")

    def normalize_cloudformation_name(self, s):
        """Normalize CloudFormation resource type name for comparison."""
        return self.normalize_name(s.split("::")[-1])

    def process(self, by_service, arn_to_cfn):
        """Build ARN service to resource types mapping."""
        services = [service for service, cfns in arn_to_cfn.items() if cfns]

        resources = {}
        for service, patterns in by_service.items():
            if service not in services:
                continue
            resource_types = set()
            for regex, r in patterns:
                resource_types.update(r)
            resources[service] = {r: self.cloudformation_resources[service] for r in sorted(resource_types)}

        mapping = {}
        missing = []
        for service, resource_types in resources.items():
            mapping.setdefault(service, {})
            for resource_type, cloudformation_resource_types in resource_types.items():
                n0 = self.normalize_name(resource_type)
                ns = {self.normalize_cloudformation_name(r): r for r in cloudformation_resource_types}
                if n0 in ns:
                    mapping[service][resource_type] = ns[n0]
                else:
                    missing.append((service, resource_type, cloudformation_resource_types))

        if missing:
            # save missing mappings for review
            missing_file = Path(__file__).parent / "cache" / "CloudFormationResourcesMissing.json"
            missing_data = [
                {"service": s, "resource_type": r, "cfn_resource_types": c}
                for s, r, c in missing
            ]
            missing_file.write_text(json.dumps(missing_data, indent=2))
            print(f"Wrote {len(missing)} missing CFN resource mappings to {missing_file}")

        return mapping
