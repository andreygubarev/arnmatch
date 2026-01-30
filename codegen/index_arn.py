# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""Processes raw ARN resources into a clean, sorted index."""

import logging
import re

from utils import load_rules

log = logging.getLogger(__name__)


class ARNIndexer:
    """Processes raw ARN resources into a clean, sorted index."""

    # ARNs to exclude (have multiple resource types or other issues)
    EXCLUDED_ARNS = set(load_rules("arn_excludes.json"))

    # Specific resource types to exclude: service -> [resource_types]
    EXCLUDED_RESOURCES = load_rules("arn_excludes_resources.json")

    # Pattern overrides: service -> {resource_type -> corrected arn_pattern}
    # Used when AWS docs have wildcards instead of capture groups
    OVERRIDES = load_rules("arn_overrides.json")

    # Additional patterns not in AWS docs
    INCLUDES = load_rules("arn_includes.json")

    def process(self, resources):
        """Process raw resources: add arn_service, apply overrides, filter, dedupe, add includes, sort."""
        # Add arn_service and apply overrides
        for r in resources:
            r["arn_service"] = self.extract_arn_service(r["arn_pattern"])
            svc, rt = r["service"], r["resource_type"]
            if svc in self.OVERRIDES and rt in self.OVERRIDES[svc]:
                r["arn_pattern"] = self.OVERRIDES[svc][rt]

        # Filter
        resources = [
            r for r in resources
            if r["arn_pattern"] not in self.EXCLUDED_ARNS
            and r["resource_type"] not in self.EXCLUDED_RESOURCES.get(r["service"], [])
        ]
        log.info(f"After filtering: {len(resources)} resources")

        # Deduplicate
        resources = self.deduplicate(resources)
        log.info(f"After deduplication: {len(resources)} resources")

        # Add included patterns
        for item in self.INCLUDES:
            resources.append({
                "service": item["service"],
                "arn_service": item["service"],
                "resource_type": item["resource_type"],
                "arn_pattern": item["arn_pattern"],
            })
        log.info(f"After includes: {len(resources)} resources")

        # Sort
        resources = self.sort_by_specificity(resources)

        return resources

    def extract_arn_service(self, arn_pattern):
        """Extract service from ARN pattern (3rd colon-separated part)."""
        parts = arn_pattern.split(":")
        if len(parts) >= 3:
            return parts[2]
        return ""

    def deduplicate(self, resources):
        """Deduplicate ARN patterns, keeping authoritative service."""
        by_arn = {}
        for r in resources:
            arn = r["arn_pattern"]
            if arn not in by_arn:
                by_arn[arn] = []
            by_arn[arn].append(r)

        results = []
        for arn, group in by_arn.items():
            if len(group) == 1:
                results.append(group[0])
            else:
                # Prefer resource where arn_service matches service
                matches = [r for r in group if r["arn_service"] == r["service"]]
                results.append(matches[0] if matches else group[0])

        return results

    def sort_by_specificity(self, resources):
        """Sort patterns: more specific (more segments, literals) first."""
        return sorted(resources, key=self.sort_key)

    def sort_key(self, r):
        arn = r["arn_pattern"]
        parts = arn.split(":", 5)
        service = parts[2] if len(parts) > 2 else ""
        region = parts[3] if len(parts) > 3 else ""
        account = parts[4] if len(parts) > 4 else ""
        resource = parts[5] if len(parts) > 5 else ""

        segments = self.parse_segments(resource)
        seg_count = len(segments)

        norm_service = self.normalize_for_sort(service)
        norm_region = self.normalize_for_sort(region)
        norm_account = self.normalize_for_sort(account)
        norm_segments = [self.normalize_for_sort(s) for s in segments]

        return (norm_service, norm_region, norm_account, -seg_count, norm_segments)

    def parse_segments(self, resource):
        """Split resource into segments by /, : and variables."""
        var_pattern = re.compile(r"(\$\{[^}]+\})")
        parts = [s1 for s0 in resource.split("/") for s1 in s0.split(":")]
        segments = []
        for part in parts:
            splits = var_pattern.split(part)
            segments.extend([s for s in splits if s])
        return segments

    def normalize_for_sort(self, value):
        """Replace variables and wildcards so they sort after literals."""
        value = re.sub(r"\$\{[^}]+\}", "~", value)
        value = value.replace("*", "~~")
        return value
