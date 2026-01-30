"""Maps ARN resource types to CloudFormation resource types."""

import json
from pathlib import Path

from utils import load_rules


class CFNResourceIndexer:
    """Maps ARN resources to CloudFormation resource types."""

    # Manual overrides: service -> {resource_type -> CFN resource type}
    # Used when ARN resource names don't match CFN resource names
    OVERRIDES = load_rules("cfn_resources_overrides.json")

    # Resources with no CloudFormation equivalent (API-only, runtime, jobs, etc.)
    # These won't appear in the missing list and return None at runtime
    EXCLUDES = load_rules("cfn_resources_excludes.json")

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

        resources_candidates = {}
        for service, patterns in by_service.items():
            if service not in services:
                continue
            resource_types = set()
            for regex, r in patterns:
                resource_types.update(r)
            resources_candidates[service] = {r: self.cloudformation_resources[service] for r in sorted(resource_types)}

        resources = {}
        resources_missing = []
        for service, resource_types in resources_candidates.items():
            resources.setdefault(service, {})
            for resource_type, cloudformation_resource_types in resource_types.items():
                # Skip resources with no CFN equivalent
                if service in self.EXCLUDES and resource_type in self.EXCLUDES[service]:
                    continue

                # Check manual overrides
                if service in self.OVERRIDES and resource_type in self.OVERRIDES[service]:
                    resources[service][resource_type] = self.OVERRIDES[service][resource_type]
                    continue

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
                elif n0.endswith("s"):
                    if resource_type[:-1] in resources[service]:
                        print(f"Plural form: already mapped for {service} {resource_type}")
                    else:
                        if n0[:-1] in ns:
                            resources[service][resource_type] = ns[n0[:-1]]
                        elif n0[:-2] in ns:
                            resources[service][resource_type] = ns[n0[:-2]]
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
