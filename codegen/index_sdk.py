# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3"]
# ///

"""Maps ARN service names to AWS SDK (boto3) client names."""

import gzip
import json
import os
from pathlib import Path


class SDKServiceIndexer:
    """Builds mapping from ARN service names to AWS SDK client names."""

    # Phase 3: Manual overrides for services where botocore metadata doesn't match
    # Format: "arn_service" -> ["sdk_client1", "sdk_client2", ...]
    OVERRIDES = {
        # AI DevOps uses aiops client
        "aidevops": ["aiops"],
        # AppMesh preview uses appmesh client
        "appmesh-preview": ["appmesh"],
        # Service Catalog uses 'catalog' in ARNs but 'servicecatalog' client
        "catalog": ["servicecatalog"],
        # CloudWatch uses 'monitoring' as endpointPrefix but 'cloudwatch' in ARNs
        "cloudwatch": ["cloudwatch"],
        # Partner Central has multiple sub-clients
        "partnercentral": [
            "partnercentral-account",
            "partnercentral-benefits",
            "partnercentral-channel",
            "partnercentral-selling",
        ],
        # AWS Private 5G uses privatenetworks client
        "private-networks": ["privatenetworks"],
        # RDS IAM auth uses rds client
        "rds-db": ["rds"],
        # Route53 recovery services
        "route53-recovery-control": [
            "route53-recovery-cluster",
            "route53-recovery-control-config",
        ],
        # S3 variants map to s3 client
        "s3-object-lambda": ["s3"],
        "s3express": ["s3"],
    }

    # Services that are deprecated/console-only and have no SDK client
    # These will be explicitly mapped to empty list
    EXCLUDES = {
        "a4b",  # Alexa for Business - discontinued
        "appstudio",  # AWS App Studio - console only
        "apptest",  # AWS Application Testing - no SDK
        "bedrock-mantle",  # Bedrock inference engine - uses OpenAI SDK, not boto3
        "bugbust",  # AWS BugBust - discontinued
        "cloudshell",  # AWS CloudShell - console only
        "codestar",  # CodeStar - discontinued
        "codewhisperer",  # Now Q Developer - IDE extension, no SDK
        "consoleapp",  # Console Mobile App
        "elastic-inference",  # Elastic Inference - EOL April 2024
        "elastictranscoder",  # Replaced by MediaConvert
        "elemental-appliances-software",  # Physical hardware - console managed
        "elemental-support-cases",  # Elemental support tickets - console only
        "freertos",  # FreeRTOS console config - no SDK
        "honeycode",  # Honeycode - discontinued
        "identity-sync",  # Identity sync service - console only
        "iotfleethub",  # IoT Fleet Hub - EOL October 2025
        "iq",  # AWS IQ
        "iq-permission",  # AWS IQ
        "lookoutmetrics",  # Lookout for Metrics - discontinued
        "lookoutvision",  # Lookout for Vision - discontinued
        "mapcredits",  # AWS MAP credits - billing/console only
        "monitron",  # Monitron - discontinued
        "nimble",  # Nimble Studio - discontinued
        "one",  # Amazon One Enterprise (palm recognition) - console only
        "opsworks",  # OpsWorks Stacks - EOL May 2024
        "opsworks-cm",  # OpsWorks for Chef/Puppet - EOL 2024
        "payments",  # AWS billing payments - console only
        "pricingplanmanager",  # AWS pricing plans - console only
        "purchase-orders",  # AWS billing purchase orders - console only
        "qdeveloper",  # Amazon Q Developer - IDE plugins only, no SDK
        "qldb",  # QLDB - end of life 2025
        "robomaker",  # RoboMaker - end of life 2025
        "securityagent",  # AWS Security Agent - preview, console only
        "sqlworkbench",  # Redshift Query Editor - console only
        "transform",  # AWS Transform - CLI only, no SDK
        "transform-custom",  # AWS Transform Custom - CLI only, no SDK
        "ts",  # AWS Diagnostic Tools - internal/support
        "vendor-insights",  # AWS Marketplace Vendor Insights - console only
        "worklink",  # WorkLink - discontinued
    }

    def __init__(self):
        import botocore
        self.botocore_data = Path(botocore.__file__).parent / "data"

    def process(self, arn_services):
        """Build ARN service -> SDK clients mapping."""
        # Get all boto3 client metadata
        metadata = self.metadata_load()

        result = {}

        for arn_service in sorted(arn_services):
            # Phase 3: Check manual overrides first
            if arn_service in self.OVERRIDES:
                result[arn_service] = self.OVERRIDES[arn_service]
                continue

            # Known no-SDK services
            if arn_service in self.EXCLUDES:
                result[arn_service] = []
                continue

            # Phase 1: Direct name match
            if arn_service in metadata:
                result[arn_service] = [arn_service]
                # Also check for additional clients via metadata
                additional = self.metadata_match(
                    arn_service, metadata, exclude={arn_service}
                )
                if additional:
                    result[arn_service].extend(sorted(additional))
                continue

            # Phase 2: Find via botocore metadata (signingName/endpointPrefix)
            clients = self.metadata_match(arn_service, metadata)
            if clients:
                result[arn_service] = sorted(clients)
                continue

            # No mapping found
            raise ValueError(f"No SDK client mapping for ARN service: {arn_service}")

        return result

    def metadata_load(self):
        """Load metadata for all boto3 clients."""
        metadata = {}

        for sdk_service in os.listdir(self.botocore_data):
            client_path = self.botocore_data / sdk_service
            if not client_path.is_dir():
                continue

            # Find latest version
            versions = sorted(
                [d for d in os.listdir(client_path) if d[0].isdigit()],
                reverse=True,
            )
            if not versions:
                continue

            # Load service metadata
            service_file = client_path / versions[0] / "service-2.json.gz"
            if not service_file.exists():
                continue

            with gzip.open(service_file) as f:
                data = json.load(f)
                metadata[sdk_service] = data.get("metadata", {})

        return metadata

    def metadata_match(self, arn_service, metadata, exclude=None):
        """Find SDK clients whose signingName or endpointPrefix matches ARN service."""
        exclude = exclude or set()
        matches = set()

        for sdk_service, meta in metadata.items():
            if sdk_service in exclude:
                continue

            # Check signingName first (more specific)
            signing_name = meta.get("signingName")
            if signing_name == arn_service:
                matches.add(sdk_service)
                continue

            # Check endpointPrefix (fallback)
            endpoint_prefix = meta.get("endpointPrefix")
            if endpoint_prefix == arn_service:
                matches.add(sdk_service)

        return matches
