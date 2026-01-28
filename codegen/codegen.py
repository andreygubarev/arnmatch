# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "joblib", "beautifulsoup4", "boto3"]
# ///

import logging
import re
from pathlib import Path

from scraper import AWSScraper
from index_sdk import SDKServiceIndexer

log = logging.getLogger(__name__)

CODEGEN_DIR = Path(__file__).parent
BUILD_DIR = CODEGEN_DIR / "build"


class ARNIndexer:
    """Processes raw ARN resources into a clean, sorted index."""

    # ARNs to exclude (have multiple resource types or other issues)
    EXCLUDED_ARNS = {
        "arn:${Partition}:${Vendor}:${Region}:*:${ResourceType}:${RecoveryPointId}",
        "arn:${Partition}:rtbfabric:${Region}:${Account}:gateway/${GatewayId}/link/${LinkId}",
        "arn:${Partition}:rtbfabric:${Region}:${Account}:gateway/${GatewayId}",
        "arn:${Partition}:aws-marketplace::${Account}:${Catalog}/ReportingData/${FactTable}/Dashboard/${DashboardName}",
        "arn:${Partition}:iot:${Region}:${Account}:thinggroup/${ThingGroupName}",
        "arn:${Partition}:mediapackagev2:${Region}:${Account}:channelGroup/${ChannelGroupName}/channel/${ChannelName}",
        "arn:${Partition}:mediapackagev2:${Region}:${Account}:channelGroup/${ChannelGroupName}/channel/${ChannelName}/originEndpoint/${OriginEndpointName}",
    }

    # Specific resource types to exclude
    EXCLUDED_RESOURCE_TYPES = {
        ("backup", "recoveryPoint"),
        ("connect", "wildcard-agent-status"),
        ("ebs", "snapshot"),
        ("connect", "wildcard-contact-flow"),
        ("connect", "wildcard-legacy-phone-number"),
        ("connect", "wildcard-phone-number"),
        ("connect", "wildcard-queue"),
        ("connect", "wildcard-quick-connect"),
        ("identitystore", "AllGroupMemberships"),
        ("identitystore", "AllGroups"),
        ("identitystore", "AllUsers"),
        ("imagebuilder", "allComponentBuildVersions"),
        ("imagebuilder", "allImageBuildVersions"),
        ("imagebuilder", "allWorkflowBuildVersions"),
        ("mobiletargeting", "apps"),
        ("mobiletargeting", "recommenders"),
    }

    # Pattern overrides: (service, resource_type) -> corrected arn_pattern
    # Used when AWS docs have wildcards instead of capture groups
    PATTERN_OVERRIDES = {
        # amplifybackend: wildcards replaced with capture groups
        ("amplifybackend", "api"): "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/api/${ApiId}",
        ("amplifybackend", "auth"): "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/auth/${AuthId}",
        ("amplifybackend", "token"): "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/challenge/${ChallengeId}",
        ("amplifybackend", "config"): "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/config/${ConfigId}",
        ("amplifybackend", "environment"): "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/environments/${EnvironmentId}",
        ("amplifybackend", "job"): "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/job/${JobId}",
        ("amplifybackend", "storage"): "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/storage/${StorageId}",
        ("amplifybackend", "backend"): "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${AppId}/${SubResourceId}",
        ("amplifybackend", "created-backend"): "arn:${Partition}:amplifybackend:${Region}:${Account}:/backend/${BackendId}",
        # artifact: wildcards replaced with capture groups
        ("artifact", "agreement"): "arn:${Partition}:artifact:::agreement/${AgreementId}",
        ("artifact", "customer-agreement"): "arn:${Partition}:artifact::${Account}:customer-agreement/${CustomerAgreementId}",
        # dms: wildcards replaced with capture groups
        ("dms", "ReplicationTaskAssessmentRun"): "arn:${Partition}:dms:${Region}:${Account}:assessment-run:${AssessmentRunId}",
        ("dms", "Certificate"): "arn:${Partition}:dms:${Region}:${Account}:cert:${CertificateId}",
        ("dms", "DataMigration"): "arn:${Partition}:dms:${Region}:${Account}:data-migration:${DataMigrationId}",
        ("dms", "DataProvider"): "arn:${Partition}:dms:${Region}:${Account}:data-provider:${DataProviderId}",
        ("dms", "Endpoint"): "arn:${Partition}:dms:${Region}:${Account}:endpoint:${EndpointId}",
        ("dms", "EventSubscription"): "arn:${Partition}:dms:${Region}:${Account}:es:${EventSubscriptionId}",
        ("dms", "ReplicationTaskIndividualAssessment"): "arn:${Partition}:dms:${Region}:${Account}:individual-assessment:${IndividualAssessmentId}",
        ("dms", "InstanceProfile"): "arn:${Partition}:dms:${Region}:${Account}:instance-profile:${InstanceProfileId}",
        ("dms", "MigrationProject"): "arn:${Partition}:dms:${Region}:${Account}:migration-project:${MigrationProjectId}",
        ("dms", "ReplicationInstance"): "arn:${Partition}:dms:${Region}:${Account}:rep:${ReplicationInstanceId}",
        ("dms", "ReplicationConfig"): "arn:${Partition}:dms:${Region}:${Account}:replication-config:${ReplicationConfigId}",
        ("dms", "ReplicationTask"): "arn:${Partition}:dms:${Region}:${Account}:task:${TaskId}",
        ("dms", "ReplicationSubnetGroup"): "arn:${Partition}:dms:${Region}:${Account}:subgrp:${SubnetGroupName}",
        # ec2: add account (modern format)
        ("ec2", "image"): "arn:${Partition}:ec2:${Region}:${Account}:image/${ImageId}",
        ("ec2", "snapshot"): "arn:${Partition}:ec2:${Region}:${Account}:snapshot/${SnapshotId}",
        # health: wildcards replaced with capture groups
        ("health", "event"): "arn:${Partition}:health:${Region}:${Account}:event/${Service}/${EventTypeCode}/${EventId}",
        # neptune-db: wildcard replaced with capture group
        ("neptune-db", "database"): "arn:${Partition}:neptune-db:${Region}:${Account}:${ClusterResourceId}/${DatabaseId}",
    }

    # Additional patterns not in AWS docs (service, arn_pattern, resource_type)
    PATTERN_INCLUDES = [
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
    ]

    def process(self, resources):
        """Process raw resources: add arn_service, apply overrides, filter, dedupe, add includes, sort."""
        # Add arn_service and apply overrides
        for r in resources:
            r["arn_service"] = self.extract_arn_service(r["arn_pattern"])
            key = (r["service"], r["resource_type"])
            if key in self.PATTERN_OVERRIDES:
                r["arn_pattern"] = self.PATTERN_OVERRIDES[key]

        # Filter
        resources = [
            r for r in resources
            if r["arn_pattern"] not in self.EXCLUDED_ARNS
            and (r["service"], r["resource_type"]) not in self.EXCLUDED_RESOURCE_TYPES
        ]
        log.info(f"After filtering: {len(resources)} resources")

        # Deduplicate
        resources = self.deduplicate(resources)
        log.info(f"After deduplication: {len(resources)} resources")

        # Add included patterns
        for service, arn_pattern, resource_type in self.PATTERN_INCLUDES:
            resources.append({
                "service": service,
                "arn_service": service,
                "resource_type": resource_type,
                "arn_pattern": arn_pattern,
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


class CodeGenerator:
    """Generates Python code from processed ARN resources."""

    # Placeholder patterns: map placeholder name -> regex pattern
    # Based on AWS regex: ^arn:[\w+=/,.@-]+:service:[\w+=/,.@-]*:[0-9]+:...
    PLACEHOLDER_PATTERNS = {
        "Partition": r"[\w-]+",  # aws, aws-cn, aws-us-gov
        "Region": r"[\w-]*",  # us-east-1, eu-west-1, or empty
        "Account": r"\d{12}",  # AWS accounts are always 12 digits
    }

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

    def generate(self, resources, sdk_services_mapping, sdk_resource_overrides, output_path):
        """Generate Python file with ARN patterns and SDK services mapping."""
        # Group by service
        by_service = {}
        for r in resources:
            service = r["arn_service"]
            if service not in by_service:
                by_service[service] = []
            regex = self.pattern_to_regex(r["arn_pattern"])
            type_names = self.get_type_names(service, r["resource_type"])
            by_service[service].append((regex, type_names))

        # Write Python file
        with open(output_path, "w") as f:
            f.write("# Auto-generated ARN patterns for matching\n")
            f.write("# Patterns are ordered: most specific first\n")
            f.write("import re\n\n")
            f.write("ARN_PATTERNS = {\n")

            for service, patterns in by_service.items():
                f.write(f"    {service!r}: [\n")
                for regex, type_names in patterns:
                    f.write(f'        (re.compile(r"{regex}"), {type_names!r}),\n')
                f.write("    ],\n")

            f.write("}\n\n")

            # Write SDK services mapping
            f.write("# Auto-generated mapping: ARN service -> AWS SDK client names\n")
            f.write("AWS_SDK_SERVICES = {\n")
            for arn_svc, clients in sorted(sdk_services_mapping.items()):
                f.write(f"    {arn_svc!r}: {clients!r},\n")
            f.write("}\n\n")

            # Write SDK resource overrides
            f.write("# Auto-generated mapping: ARN service -> [(resource_type_prefix, sdk_client), ...]\n")
            f.write("# For services with multiple SDK clients, maps specific resource types to their SDK\n")
            f.write("AWS_SDK_RESOURCE_OVERRIDES = {\n")
            for svc, patterns in sorted(sdk_resource_overrides.items()):
                f.write(f"    {svc!r}: [\n")
                for pattern, client in patterns:
                    f.write(f"        ({pattern!r}, {client!r}),\n")
                f.write("    ],\n")
            f.write("}\n")

        log.info(f"Wrote {len(resources)} patterns for {len(by_service)} services to {output_path}")
        log.info(f"Wrote SDK mapping for {len(sdk_services_mapping)} services")
        log.info(f"Wrote SDK resource overrides for {len(sdk_resource_overrides)} services")

    def pattern_to_regex(self, arn_pattern):
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
            pattern = self.PLACEHOLDER_PATTERNS.get(name, ".+?")
            result = result.replace(f"\x00{i}\x00", f"(?P<{name}>{pattern})")

        result = result.replace("\x01", ".*")
        return f"^{result}$"

    def get_type_names(self, service, resource_type):
        """Get list of type names: primary type + any aliases."""
        types = [resource_type]
        aliases = self.TYPE_ALIASES.get((service, resource_type), [])
        types.extend(aliases)
        return types


def validate_sdk_overrides(resources, sdk_mapping, sdk_resource_overrides):
    """Validate that all resources with multiple SDK clients have overrides."""
    # Find services with multiple SDK clients
    multi_sdk_services = {svc for svc, clients in sdk_mapping.items() if len(clients) > 1}

    missing = []
    for r in resources:
        service = r["arn_service"]
        if service not in multi_sdk_services:
            continue

        resource_type = r["resource_type"]
        overrides = sdk_resource_overrides.get(service, [])

        # Check if resource type matches any override pattern
        matched = False
        for pattern, _ in overrides:
            if resource_type == pattern or resource_type.startswith(pattern + "/"):
                matched = True
                break

        if not matched:
            missing.append((service, resource_type))

    if missing:
        msg = "Resources with multiple SDK clients missing overrides:\n"
        for service, resource_type in sorted(set(missing)):
            msg += f"  {service}: {resource_type}\n"
        raise ValueError(msg)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Scrape
    scraper = AWSScraper()
    services = scraper.get_services()
    resources = []
    for svc in services:
        resources.extend(scraper.get_resources(svc["href"]))

    # Process ARN patterns
    indexer = ARNIndexer()
    resources = indexer.process(resources)

    # Build SDK services mapping
    arn_services = {r["arn_service"] for r in resources}
    sdk_indexer = SDKServiceIndexer()
    sdk_mapping = sdk_indexer.process(arn_services)
    sdk_resource_overrides = SDKServiceIndexer.SDK_RESOURCE_OVERRIDES

    # Validate overrides coverage
    validate_sdk_overrides(resources, sdk_mapping, sdk_resource_overrides)

    # Generate
    BUILD_DIR.mkdir(exist_ok=True)
    generator = CodeGenerator()
    generator.generate(resources, sdk_mapping, sdk_resource_overrides, BUILD_DIR / "arn_patterns.py")


if __name__ == "__main__":
    main()
