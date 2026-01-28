# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""Processes raw ARN resources into a clean, sorted index."""

import logging
import re

log = logging.getLogger(__name__)


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
