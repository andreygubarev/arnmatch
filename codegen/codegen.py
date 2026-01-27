# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "joblib", "beautifulsoup4"]
# ///

import logging
import re
from pathlib import Path

from scraper import AWSScraper

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

    def process(self, resources):
        """Process raw resources: add arn_service, filter, dedupe, add manual, sort."""
        # Add arn_service
        for r in resources:
            r["arn_service"] = self.extract_arn_service(r["arn_pattern"])

        # Filter
        resources = [r for r in resources if not self.should_exclude(r)]
        log.info(f"After filtering: {len(resources)} resources")

        # Deduplicate
        resources = self.deduplicate(resources)
        log.info(f"After deduplication: {len(resources)} resources")

        # Add manual patterns
        for service, arn_pattern, resource_type in self.MANUAL_PATTERNS:
            resources.append({
                "service": service,
                "arn_service": service,
                "resource_type": resource_type,
                "arn_pattern": arn_pattern,
            })
        log.info(f"After manual patterns: {len(resources)} resources")

        # Sort
        resources = self.sort_by_specificity(resources)

        return resources

    def extract_arn_service(self, arn_pattern):
        """Extract service from ARN pattern (3rd colon-separated part)."""
        parts = arn_pattern.split(":")
        if len(parts) >= 3:
            return parts[2]
        return ""

    def should_exclude(self, r):
        """Check if a resource should be excluded."""
        service = r["service"]
        resource_type = r["resource_type"]
        arn_pattern = r["arn_pattern"]

        if arn_pattern in self.EXCLUDED_ARNS:
            return True
        if service in self.EXCLUDED_SERVICES:
            return True
        if (service, resource_type) in self.EXCLUDED_RESOURCE_TYPES:
            return True
        for svc, prefix in self.EXCLUDED_RESOURCE_TYPE_PREFIXES:
            if service == svc and resource_type.startswith(prefix):
                return True
        if service == "ec2":
            for pattern in self.EXCLUDED_EC2_PATTERNS:
                if pattern in arn_pattern:
                    return True
        return False

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
                matches = [r for r in group if r["arn_service"] == r["service"]]
                if matches:
                    results.extend(matches)
                else:
                    results.append(group[0])

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

    def generate(self, resources, output_path):
        """Generate Python file with ARN patterns."""
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
                    f.write(f"        (re.compile(r{regex!r}), {type_names!r}),\n")
                f.write("    ],\n")

            f.write("}\n")

        log.info(f"Wrote {len(resources)} patterns for {len(by_service)} services to {output_path}")

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
            result = result.replace(f"\x00{i}\x00", f"(?P<{name}>.+?)")

        result = result.replace("\x01", ".*")
        return f"^{result}$"

    def get_type_names(self, service, resource_type):
        """Get list of type names: primary type + any aliases."""
        types = [resource_type]
        aliases = self.TYPE_ALIASES.get((service, resource_type), [])
        types.extend(aliases)
        return types


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Scrape
    scraper = AWSScraper()
    services = scraper.get_services()
    resources = []
    for svc in services:
        resources.extend(scraper.get_resources(svc["href"]))

    # Process
    indexer = ARNIndexer()
    resources = indexer.process(resources)

    # Generate
    BUILD_DIR.mkdir(exist_ok=True)
    generator = CodeGenerator()
    generator.generate(resources, BUILD_DIR / "arn_patterns.py")


if __name__ == "__main__":
    main()
