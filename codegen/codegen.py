# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "joblib", "beautifulsoup4"]
# ///

import logging
import re

from scraper import AWSScraper

log = logging.getLogger(__name__)

# ARNs where service in pattern differs from service_prefix
ARN_SERVICE_OVERRIDES = {
    "arn:${Partition}:${Vendor}:${Region}:*:${ResourceType}:${RecoveryPointId}": "backup",
}

# ARNs to exclude (have multiple resource types or other issues)
EXCLUDED_ARNS = {
    "arn:${Partition}:rtbfabric:${Region}:${Account}:gateway/${GatewayId}/link/${LinkId}",
    "arn:${Partition}:rtbfabric:${Region}:${Account}:gateway/${GatewayId}",
    "arn:${Partition}:aws-marketplace::${Account}:${Catalog}/ReportingData/${FactTable}/Dashboard/${DashboardName}",
    "arn:${Partition}:iot:${Region}:${Account}:thinggroup/${ThingGroupName}",
    "arn:${Partition}:mediapackagev2:${Region}:${Account}:channelGroup/${ChannelGroupName}/channel/${ChannelName}",
    "arn:${Partition}:mediapackagev2:${Region}:${Account}:channelGroup/${ChannelGroupName}/channel/${ChannelName}/originEndpoint/${OriginEndpointName}",
}

# Services to exclude entirely (use wildcards instead of capture groups)
EXCLUDED_SERVICES = {"dms", "amplifybackend", "health", "neptune-db"}

# Specific resource types to exclude
EXCLUDED_RESOURCE_TYPES = {
    ("artifact", "agreement"),
    ("artifact", "customer-agreement"),
    ("backup", "recoveryPoint"),
    ("mobiletargeting", "apps"),
    ("mobiletargeting", "recommenders"),
}

# Resource type prefixes to exclude
EXCLUDED_RESOURCE_TYPE_PREFIXES = {
    ("connect", "wildcard-"),
    ("identitystore", "All"),
    ("imagebuilder", "all"),
}

# EC2 patterns to exclude (no account in pattern)
EXCLUDED_EC2_PATTERNS = {"::image/", "::snapshot/"}

# Type aliases: map AWS doc type -> list of known aliases
TYPE_ALIASES = {
    ("elasticloadbalancing", "loadbalancer/app/"): ["loadbalancer/app"],
    ("elasticloadbalancing", "loadbalancer/net/"): ["loadbalancer/net"],
    ("elasticloadbalancing", "loadbalancer/gwy/"): ["loadbalancer/gwy"],
    ("events", "rule-on-default-event-bus"): ["rule"],
    ("secretsmanager", "Secret"): ["secret"],
    ("mq", "configurations"): ["configuration"],
    ("inspector", "target-template"): ["target/template"],
    ("backup", "backupPlan"): ["backup-plan"],
    ("backup", "backupVault"): ["backup-vault"],
    ("ssm", "resourcedatasync"): ["resource-data-sync"],
    ("s3", "storagelensconfiguration"): ["storage-lens"],
    ("dms", "ReplicationSubnetGroup"): ["subgrp"],
}

# Manual patterns to add (service, arn_pattern, resource_type)
MANUAL_PATTERNS = [
    # amplifybackend: wildcards replaced with capture groups
    ("amplifybackend", "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/api/${ApiId}", "api"),
    ("amplifybackend", "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/auth/${AuthId}", "auth"),
    ("amplifybackend", "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/challenge/${ChallengeId}", "token"),
    ("amplifybackend", "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/config/${ConfigId}", "config"),
    ("amplifybackend", "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/environments/${EnvironmentId}", "environment"),
    ("amplifybackend", "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/job/${JobId}", "job"),
    ("amplifybackend", "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/storage/${StorageId}", "storage"),
    ("amplifybackend", "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/${SubResourceId}", "backend"),
    ("amplifybackend", "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${BackendId}", "created-backend"),
    # artifact: wildcards replaced with capture groups
    ("artifact", "arn:${Partition}:artifact:::agreement/${AgreementId}", "agreement"),
    ("artifact", "arn:${Partition}:artifact::${Account}:customer-agreement/${CustomerAgreementId}", "customer-agreement"),
    # health: wildcards replaced with capture groups
    ("health", "arn:${Partition}:health:${Region}:${Account}:event/${Service}/${EventTypeCode}/${EventId}", "event"),
    # neptune-db: wildcard replaced with capture group
    ("neptune-db", "arn:${Partition}:neptune-db:${Region}:${Account}:${ClusterResourceId}/${DatabaseId}", "database"),
    # EC2 with account (modern format)
    ("ec2", "arn:${Partition}:ec2:${Region}:${Account}:image/${ImageId}", "image"),
    ("ec2", "arn:${Partition}:ec2:${Region}:${Account}:snapshot/${SnapshotId}", "snapshot"),
    # EKS Kubernetes resources (from Resource Explorer)
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:deployment/${ClusterName}/${Namespace}/${DeploymentName}/${UUID}", "deployment"),
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:replicaset/${ClusterName}/${Namespace}/${ReplicaSetName}/${UUID}", "replicaset"),
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:service/${ClusterName}/${Namespace}/${ServiceName}/${UUID}", "service"),
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:endpointslice/${ClusterName}/${Namespace}/${EndpointSliceName}/${UUID}", "endpointslice"),
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:namespace/${ClusterName}/${NamespaceName}/${UUID}", "namespace"),
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:ingress/${ClusterName}/${Namespace}/${IngressName}/${UUID}", "ingress"),
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:statefulset/${ClusterName}/${Namespace}/${StatefulSetName}/${UUID}", "statefulset"),
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:persistentvolume/${ClusterName}/${PersistentVolumeName}/${UUID}", "persistentvolume"),
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:daemonset/${ClusterName}/${Namespace}/${DaemonSetName}/${UUID}", "daemonset"),
    # Inspector (legacy)
    ("inspector", "arn:${Partition}:inspector:${Region}:${Account}:target/${TargetId}/template/${TemplateId}", "target-template"),
    # DMS: AWS docs use wildcards, add proper capture groups
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:assessment-run:${AssessmentRunId}", "ReplicationTaskAssessmentRun"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:cert:${CertificateId}", "Certificate"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:data-migration:${DataMigrationId}", "DataMigration"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:data-provider:${DataProviderId}", "DataProvider"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:endpoint:${EndpointId}", "Endpoint"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:es:${EventSubscriptionId}", "EventSubscription"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:individual-assessment:${IndividualAssessmentId}", "ReplicationTaskIndividualAssessment"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:instance-profile:${InstanceProfileId}", "InstanceProfile"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:migration-project:${MigrationProjectId}", "MigrationProject"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:rep:${ReplicationInstanceId}", "ReplicationInstance"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:replication-config:${ReplicationConfigId}", "ReplicationConfig"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:task:${TaskId}", "ReplicationTask"),
    ("dms", "arn:${Partition}:dms:${Region}:${Account}:subgrp:${SubnetGroupName}", "ReplicationSubnetGroup"),
]


def extract_arn_service(arn_pattern: str) -> str:
    """Extract service from ARN pattern (3rd colon-separated part)."""
    parts = arn_pattern.split(":")
    if len(parts) >= 3:
        return parts[2]
    return ""


def parse_segments(resource: str) -> list[str]:
    """Split resource into segments by /, : and variables."""
    var_pattern = re.compile(r"(\$\{[^}]+\})")
    parts = [s1 for s0 in resource.split("/") for s1 in s0.split(":")]
    segments = []
    for part in parts:
        splits = var_pattern.split(part)
        segments.extend([s for s in splits if s])
    return segments


def normalize_for_sort(value: str) -> str:
    """Replace variables and wildcards so they sort after literals."""
    value = re.sub(r"\$\{[^}]+\}", "~", value)
    value = value.replace("*", "~~")
    return value


def pattern_to_regex(arn_pattern: str) -> str:
    """Convert ARN pattern to regex with named capture groups."""
    placeholders = []

    def capture_var(m):
        placeholders.append(m.group(1))
        return f"\x00{len(placeholders) - 1}\x00"

    result = re.sub(r"\$\{([^}]+)\}", capture_var, arn_pattern)
    result = result.replace("*", "\x01")
    result = re.escape(result)
    result = result.replace("\\-", "-")

    for i, name in enumerate(placeholders):
        result = result.replace(f"\x00{i}\x00", f"(?P<{name}>.+?)")

    result = result.replace("\x01", ".*")
    return f"^{result}$"


def get_type_names(service: str, resource_type: str) -> list[str]:
    """Get list of type names: primary type + any aliases."""
    types = [resource_type]
    aliases = TYPE_ALIASES.get((service, resource_type), [])
    types.extend(aliases)
    return types


def should_exclude(service: str, resource_type: str, arn_pattern: str) -> bool:
    """Check if a resource should be excluded."""
    if arn_pattern in EXCLUDED_ARNS:
        return True
    if service in EXCLUDED_SERVICES:
        return True
    if (service, resource_type) in EXCLUDED_RESOURCE_TYPES:
        return True
    for svc, prefix in EXCLUDED_RESOURCE_TYPE_PREFIXES:
        if service == svc and resource_type.startswith(prefix):
            return True
    if service == "ec2":
        for pattern in EXCLUDED_EC2_PATTERNS:
            if pattern in arn_pattern:
                return True
    return False


def deduplicate(resources: list[dict]) -> list[dict]:
    """Deduplicate ARN patterns, keeping authoritative service."""
    # Group by arn_pattern
    by_arn: dict[str, list[dict]] = {}
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
            # Prefer where arn_service == service
            matches = [r for r in group if r["arn_service"] == r["service"]]
            if matches:
                results.extend(matches)
            else:
                results.append(group[0])

    return results


def sort_by_specificity(resources: list[dict]) -> list[dict]:
    """Sort patterns: more specific (more segments, literals) first."""

    def sort_key(r):
        arn = r["arn_pattern"]
        parts = arn.split(":", 5)
        service = parts[2] if len(parts) > 2 else ""
        region = parts[3] if len(parts) > 3 else ""
        account = parts[4] if len(parts) > 4 else ""
        resource = parts[5] if len(parts) > 5 else ""

        segments = parse_segments(resource)
        seg_count = len(segments)

        # Normalize for sorting (variables/wildcards sort after literals)
        norm_service = normalize_for_sort(service)
        norm_region = normalize_for_sort(region)
        norm_account = normalize_for_sort(account)
        norm_segments = [normalize_for_sort(s) for s in segments]

        # Sort by: service, region, account, segment count DESC, then segments
        return (norm_service, norm_region, norm_account, -seg_count, norm_segments)

    return sorted(resources, key=sort_key)


def generate(output_path: str):
    """Generate ARN patterns file."""
    scraper = AWSScraper()

    # Scrape
    services = scraper.get_services()
    resources = []
    for svc in services:
        resources.extend(scraper.get_resources(svc["href"]))

    # Add arn_service
    for r in resources:
        arn_service = extract_arn_service(r["arn_pattern"])
        r["arn_service"] = ARN_SERVICE_OVERRIDES.get(r["arn_pattern"], arn_service)

    # Filter
    resources = [r for r in resources if not should_exclude(r["service"], r["resource_type"], r["arn_pattern"])]
    log.info(f"After filtering: {len(resources)} resources")

    # Deduplicate
    resources = deduplicate(resources)
    log.info(f"After deduplication: {len(resources)} resources")

    # Add manual patterns
    for service, arn_pattern, resource_type in MANUAL_PATTERNS:
        resources.append({
            "service": service,
            "arn_service": service,
            "resource_type": resource_type,
            "arn_pattern": arn_pattern,
        })
    log.info(f"After manual patterns: {len(resources)} resources")

    # Sort
    resources = sort_by_specificity(resources)

    # Group by service
    by_service: dict[str, list[tuple[str, list[str]]]] = {}
    for r in resources:
        service = r["arn_service"]
        if service not in by_service:
            by_service[service] = []
        regex = pattern_to_regex(r["arn_pattern"])
        type_names = get_type_names(service, r["resource_type"])
        by_service[service].append((regex, type_names))

    # Write Python file
    with open(output_path, "w") as f:
        f.write("# Auto-generated ARN patterns for matching\n")
        f.write("# Patterns are ordered: most specific first\n")
        f.write("import re\n\n")
        f.write("ARN_PATTERNS: dict[str, list[tuple[re.Pattern, list[str]]]] = {\n")

        for service, patterns in by_service.items():
            f.write(f"    {service!r}: [\n")
            for regex, type_names in patterns:
                f.write(f"        (re.compile(r{regex!r}), {type_names!r}),\n")
            f.write("    ],\n")

        f.write("}\n")

    log.info(f"Wrote {len(resources)} patterns for {len(by_service)} services to {output_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    generate("arn_patterns.py")
