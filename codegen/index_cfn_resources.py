"""Maps ARN resource types to CloudFormation resource types."""

import json
from pathlib import Path


class CFNResourceIndexer:
    """Maps ARN resources to CloudFormation resource types."""

    CACHE_SERVICES_FILE = Path(__file__).parent / "cache" / "CloudFormationServices.json"
    CACHE_RESOURCES_FILE = Path(__file__).parent / "cache" / "CloudFormationResources.json"
    CACHE_RESOURCES_MISS_FILE = Path(__file__).parent / "cache" / "CloudFormationResourcesMissing.json"

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

        resources_registry = {}
        for service, patterns in by_service.items():
            if service not in services:
                continue
            resource_types = set()
            for regex, r in patterns:
                resource_types.update(r)
            resources_registry[service] = {r: self.cloudformation_resources[service] for r in sorted(resource_types)}

        resources = {}
        resources_missing = []
        for service, resource_types in resources_registry.items():
            resources.setdefault(service, {})
            for resource_type, cloudformation_resource_types in resource_types.items():
                n0 = self.normalize_name(resource_type)

                # Sort so CFN types whose service matches ARN service come last (win)
                n_service = self.normalize_name(service)
                sorted_cfn = sorted(
                    cloudformation_resource_types,
                    key=lambda r: self.normalize_name(r.split("::")[1]) == n_service
                )
                ns = {self.normalize_cloudformation_name(r): r for r in sorted_cfn}

                if n0 in ns:
                    resources[service][resource_type] = ns[n0]
                elif n0.endswith("s") and resource_type[:-1] in resources[service]:
                    print(f"Skipping plural resource type {resource_type} for service {service}")
                else:
                    resources_missing.append({
                        "resource_service": service,
                        "resource_type": resource_type,
                        "cloudformation_resources": cloudformation_resource_types,
                    })

        if resources_missing:
            self.CACHE_RESOURCES_MISS_FILE.write_text(json.dumps(resources_missing, indent=2))
            print(f"Wrote {len(resources_missing)} missing CFN resource mappings")

        return resources
