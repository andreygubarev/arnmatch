# /// script
# requires-python = ">=3.11"
# dependencies = ["ruamel.yaml"]
# ///

"""Maps ARN resource types to Tagging API resource types."""

import json
from pathlib import Path

from utils import load_rules


class TagResourceIndexer:
    """Maps ARN resources to Tagging API resource types."""

    # Manual overrides: service -> {resource_type -> tagging resource type}
    OVERRIDES = load_rules("tag_resources_overrides.json")

    # Resources with no tagging equivalent
    EXCLUDES = load_rules("tag_resources_excludes.json")

    CACHE_RESOURCES_FILE = Path(__file__).parent / "cache" / "TaggingAPIResources.json"
    CACHE_SERVICES_FILE = Path(__file__).parent / "cache" / "TaggingAPIServices.json"
    CACHE_MAPPING_FILE = Path(__file__).parent / "cache" / "TaggingAPIResourcesMapping.json"
    CACHE_MISSING_FILE = Path(__file__).parent / "cache" / "TaggingAPIResourcesMissing.json"

    @property
    def tagging_services(self):
        """Load ARN service -> tagging services mapping."""
        return json.loads(self.CACHE_SERVICES_FILE.read_text())

    @property
    def tagging_resources(self):
        """Load tagging resources grouped by service."""
        resources = json.loads(self.CACHE_RESOURCES_FILE.read_text())
        by_service = {}
        for rt in resources:
            parts = rt.split("::")
            service = parts[1]
            by_service.setdefault(service, []).append(rt)
        return by_service

    def normalize_name(self, s):
        """Normalize resource type name for comparison."""
        return s.strip().lower().replace("-", "").replace("_", "").replace(" ", "")

    def normalize_tagging_name(self, s):
        """Normalize Tagging API resource type name for comparison."""
        return self.normalize_name(s.split("::")[-1])

    def process(self, by_service, arn_to_tag):
        """Build ARN service -> resource type -> tagging resource mapping."""
        # Services that have tagging support
        services = [service for service, tags in arn_to_tag.items() if tags]

        # Build candidate mapping: ARN service -> {resource_type -> [tagging_resources]}
        tagging_resources = self.tagging_resources
        resources_candidates = {}

        for service, patterns in by_service.items():
            if service not in services:
                continue

            # Get all tagging resources for this service's tagging services
            tag_services = arn_to_tag.get(service, [])
            available_resources = []
            for tag_svc in tag_services:
                available_resources.extend(tagging_resources.get(tag_svc, []))

            if not available_resources:
                continue

            # Get all resource types from patterns
            resource_types = set()
            for regex, names in patterns:
                resource_types.update(names)

            resources_candidates[service] = {
                rt: available_resources for rt in sorted(resource_types)
            }

        # Match resources
        resources = {}
        resources_missing = []
        exact_count = 0
        plural_count = 0
        override_count = 0
        excluded_count = 0

        for service, resource_types in resources_candidates.items():
            resources.setdefault(service, {})

            for resource_type, tagging_resource_types in resource_types.items():
                # Skip excluded resources
                if service in self.EXCLUDES and resource_type in self.EXCLUDES[service]:
                    excluded_count += 1
                    continue

                # Check manual overrides
                if service in self.OVERRIDES and resource_type in self.OVERRIDES[service]:
                    resources[service][resource_type] = self.OVERRIDES[service][resource_type]
                    override_count += 1
                    continue

                n0 = self.normalize_name(resource_type)

                # Sort so tagging types whose service matches ARN service come last (win)
                n_service = self.normalize_name(service)
                sorted_tag = sorted(
                    tagging_resource_types,
                    key=lambda r: self.normalize_name(r.split("::")[1]) == n_service
                )
                ns = {self.normalize_tagging_name(r): r for r in sorted_tag}

                if n0 in ns:
                    resources[service][resource_type] = ns[n0]
                    exact_count += 1
                elif n0.endswith("s") and n0[:-1] in ns:
                    resources[service][resource_type] = ns[n0[:-1]]
                    plural_count += 1
                elif n0.endswith("es") and n0[:-2] in ns:
                    resources[service][resource_type] = ns[n0[:-2]]
                    plural_count += 1
                else:
                    resources_missing.append({
                        "service": service,
                        "resource_type": resource_type,
                        "tagging_resources": tagging_resource_types,
                    })

        # Save mapping
        self.CACHE_MAPPING_FILE.write_text(json.dumps(resources, indent=2))

        # Save missing
        if resources_missing:
            self.CACHE_MISSING_FILE.write_text(json.dumps(resources_missing, indent=2))
            print(f"Wrote {len(resources_missing)} missing tagging resource mappings")
        elif self.CACHE_MISSING_FILE.exists():
            self.CACHE_MISSING_FILE.unlink()

        self.metrics = {
            "services_with_tag": len(services),
            "exact_match": exact_count,
            "plural_match": plural_count,
            "override": override_count,
            "excluded": excluded_count,
            "missing": len(resources_missing),
            "mapped": sum(len(r) for r in resources.values()),
        }

        return resources


if __name__ == "__main__":
    # Test run - requires codegen.py to have run first
    import json
    from pathlib import Path

    BUILD_DIR = Path(__file__).parent / "build"
    CACHE_DIR = Path(__file__).parent / "cache"

    # Load by_service from arn_patterns.yaml
    from ruamel.yaml import YAML
    yaml = YAML()
    with open(BUILD_DIR / "arn_patterns.yaml") as f:
        data = yaml.load(f)

    # Convert to by_service format (regex, names)
    by_service = {}
    for service, resources in data.items():
        patterns = []
        for r in resources:
            patterns.append((None, r["names"]))
        by_service[service] = patterns

    # Load arn_to_tag
    arn_to_tag = json.loads((CACHE_DIR / "TaggingAPIServices.json").read_text())

    indexer = TagResourceIndexer()
    result = indexer.process(by_service, arn_to_tag)

    print(f"Metrics: {indexer.metrics}")
