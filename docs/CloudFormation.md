# CloudFormation Resource Mapping

## Overview

This library maps AWS ARN resource types to CloudFormation (CFN) resource types through an automated process. The mapping is generated from:
1. AWS ARN documentation patterns (what resources exist)
2. CloudFormation Resource Specification (what CFN supports)
3. Fuzzy name matching to correlate the two

## Mapping Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| Total ARN resource types | 1,639 | 100% |
| Successfully mapped to CFN | 975 | 59.5% |
| Missing mappings | 664 | 40.5% |

## How Mapping Works

The mapping algorithm (`codegen/index_cfn_resources.py`) uses name normalization:

```python
def normalize_name(self, s):
    """Normalize resource type name for comparison."""
    return s.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
```

For example:
- `certificate-authority` → `certificateauthority`
- `BackupPlan` → `backupplan`
- `load-balancer` → `loadbalancer`

The algorithm:
1. Tries exact match on normalized names
2. Tries plural form (removes trailing `s` or `es`)
3. Prefers CFN types where the service name matches the ARN service

## EC2 Deep Dive

EC2 has **110 total ARN resource types** but only **~71 are mapped** to CloudFormation, leaving **39 missing**.

### Missing EC2 Resources by Category

#### 1. No CloudFormation Support (16 resources)

These resources simply don't exist in CloudFormation:

| ARN Type | Reason |
|----------|--------|
| `capacity-block` | Not supported in CFN |
| `coip-pool` | Customer-owned IP pools not in CFN |
| `declarative-policies-report` | Report, not a resource |
| `elastic-gpu` | Elastic GPUs deprecated/not in CFN |
| `elastic-ip` | Actually `EIP` in CFN - name mismatch |
| `export-image-task` | Async operation, not a resource |
| `export-instance-task` | Async operation, not a resource |
| `fpga-image` | FPGA images not in CFN |
| `image` | AMIs not managed by CFN |
| `image-usage-report` | Report, not a resource |
| `import-image-task` | Async operation, not a resource |
| `import-snapshot-task` | Async operation, not a resource |
| `ipv4pool-ec2` | Public IP pools not in CFN |
| `ipv6pool-ec2` | Public IP pools not in CFN |
| `mac-modification-task` | Async operation, not a resource |
| `outpost-lag` | Outposts linking not in CFN |

#### 2. Name Mismatches (6 resources)

These could be mapped with manual overrides:

| ARN Type | CFN Type | Issue |
|----------|----------|-------|
| `dedicated-host` | `AWS::EC2::Host` | "dedicatedhost" ≠ "host" |
| `fleet` | `AWS::EC2::EC2Fleet` | "fleet" ≠ "ec2fleet" |
| `host-reservation` | `AWS::EC2::Host` | Reservation vs Host |
| `snapshot` | *(none in EC2)* | EBS snapshots in different service |
| `spot-fleet-request` | `AWS::EC2::SpotFleet` | "spotfleetrequest" ≠ "spotfleet" |
| `vpc-flow-log` | `AWS::EC2::FlowLog` | "vpcflowlog" ≠ "flowlog" |

#### 3. Sub-resources / Properties (17 resources)

CloudFormation only supports the parent resource:

| ARN Type | CFN Parent Resource | Relationship |
|----------|---------------------|--------------|
| `instance-event-window` | `AWS::EC2::Instance` | Instance property |
| `ipam-external-resource-verification-token` | `AWS::EC2::IPAM` | IPAM sub-resource |
| `ipam-policy` | `AWS::EC2::IPAM` | IPAM sub-resource |
| `ipam-prefix-list-resolver` | `AWS::EC2::IPAM` | IPAM sub-resource |
| `ipam-prefix-list-resolver-target` | `AWS::EC2::IPAM` | IPAM sub-resource |
| `local-gateway` | Various local gateway types | Standalone LGW not exposed |
| `replace-root-volume-task` | `AWS::EC2::Volume` | Volume operation |
| `security-group-rule` | `AWS::EC2::SecurityGroup` | Inline property only |
| `spot-instances-request` | `AWS::EC2::Instance` | Creates an instance |
| `subnet-cidr-reservation` | `AWS::EC2::Subnet` | Subnet property |
| `transit-gateway-policy-table` | `AWS::EC2::TransitGateway` | TGW property |
| `transit-gateway-route-table-announcement` | `AWS::EC2::TransitGatewayRouteTable` | TGW RT property |
| `verified-access-endpoint-target` | `AWS::EC2::VerifiedAccessEndpoint` | Endpoint property |
| `verified-access-policy` | *(none)* | Policy not exposed |
| `vpc-endpoint-connection` | `AWS::EC2::VPCEndpoint` | Connection detail |
| `vpc-endpoint-service-permission` | `AWS::EC2::VPCEndpointService` | Service property |
| `vpn-connection-device-type` | `AWS::EC2::VPNConnection` | VPN property |

### EC2 Key Findings

1. **Security Group Rules** - CFN doesn't have a standalone `SecurityGroupRule` resource. Rules must be defined inline in `AWS::EC2::SecurityGroup` or via `SecurityGroupEgress`/`SecurityGroupIngress` resources.

2. **IPAM Complexity** - IPAM has many sub-resources (policies, tokens, resolvers) that are configured as properties on the parent IPAM resource in CFN.

3. **Tasks vs Resources** - EC2 has many "task" resources that represent async operations, not persistent infrastructure that CFN manages.

4. **EBS Snapshots** - Surprisingly, `snapshot` ARNs don't map to EC2 CFN resources. EBS snapshots may be under a different service namespace.

## General Patterns Across All Services

### Top Services with Missing Mappings

| Service | Missing | Primary Reason |
|---------|---------|----------------|
| `ec2` | 39 | Tasks, sub-resources, no CFN support |
| `sagemaker` | 35 | Jobs (training, processing, etc.) are operations |
| `bedrock` | 22 | New service, CFN coverage lagging |
| `rds` | 21 | DB snapshots, events, tasks not in CFN |
| `redshift` | 18 | Cluster snapshots, data shares |
| `apigateway` | 14 | v2 resources, cache settings, documentation |
| `iot` | 14 | Thing shadows, jobs, policies as properties |
| `personalize` | 14 | Datasets, solutions - CFN coverage gaps |

### Categories of Missing Mappings

Across all 664 missing resources, the patterns are:

#### 1. Operations/Tasks (~30%)
Resources representing async operations rather than persistent infrastructure:
- Export tasks, import tasks, backup jobs
- Training jobs (SageMaker), model customization jobs (Bedrock)
- Snapshot creation tasks

**Examples:**
- `ec2:export-image-task`
- `sagemaker:training-job`
- `bedrock:model-customization-job`

#### 2. Sub-resources (~35%)
Child resources that CFN configures as parent properties:
- Security group rules
- IPAM policies/tokens
- API Gateway methods/responses
- ECS task definitions

**Examples:**
- `ec2:security-group-rule`
- `apigateway:MethodResponse`
- `backup:legalHold`

#### 3. Read-only/Derived Resources (~15%)
Resources that are outputs or derived data:
- Reports (image usage, declarative policies)
- Analysis results (Access Analyzer findings)
- Data shares (Redshift)

**Examples:**
- `ec2:image-usage-report`
- `access-analyzer:ArchiveRule`
- `redshift:datashare`

#### 4. No CFN Support (~20%)
Resources that CloudFormation simply doesn't support yet:
- New service features
- Deprecated services (Elastic GPU)
- Administrative resources

**Examples:**
- `bedrock:async-invoke`
- `ec2:elastic-gpu`
- `personalize:dataset` (partial support)

### Name Matching Failures

The fuzzy matcher fails on these patterns:

| Pattern | Example ARN | CFN Equivalent |
|---------|-------------|----------------|
| Abbreviations | `elastic-ip` | `EIP` |
| Service prefixes | `vpc-flow-log` | `FlowLog` |
| Added prefixes | `fleet` | `EC2Fleet` |
| Different word order | `spot-fleet-request` | `SpotFleet` |
| Pluralization edge cases | `archiveRule` | `Analyzer` (parent) |
| Compound words | `dedicated-host` | `Host` |

### CFN Coverage Gaps by Service Type

| Service Type | CFN Coverage | Reason |
|--------------|--------------|--------|
| Compute (EC2, ECS, EKS) | High (80%+) | Core infrastructure |
| Networking (VPC, ELB) | High (85%+) | Core infrastructure |
| Storage (S3, EBS, EFS) | Medium (70%) | Some sub-resources missing |
| Analytics (Redshift, Athena) | Medium (65%) | Jobs, snapshots limited |
| ML/AI (SageMaker, Bedrock) | Low (50%) | Rapid development, jobs not resources |
| Integration (API Gateway, AppSync) | Medium (70%) | v2 APIs, cache settings |
| IoT | Low (55%) | Many sub-resources |

## Recommendations

### For Manual Overrides

Consider adding manual mappings for these high-impact mismatches:

```python
# In codegen/index_cfn_resources.py or a new overrides file
CFN_RESOURCE_OVERRIDES = {
    "ec2": {
        "dedicated-host": "AWS::EC2::Host",
        "fleet": "AWS::EC2::EC2Fleet",
        "vpc-flow-log": "AWS::EC2::FlowLog",
        "spot-fleet-request": "AWS::EC2::SpotFleet",
        "elastic-ip": "AWS::EC2::EIP",
    },
    # ... other services
}
```

### For Coverage Improvements

1. **Accept that tasks/jobs won't map** - These are operations, not resources
2. **Focus on sub-resources** - Some may deserve manual mapping to parent
3. **Monitor new CFN releases** - Bedrock, SageMaker improving rapidly
4. **Document edge cases** - Some resources (like AMI images) intentionally not in CFN

## Data Files

- `codegen/cache/CloudFormationResources.json` - All CFN resources by service
- `codegen/cache/CloudFormationResourcesMissing.json` - Missing mappings with candidate CFN types
- `codegen/build/arn_patterns.py` - Generated Python with `AWS_CLOUDFORMATION_RESOURCES` dict
