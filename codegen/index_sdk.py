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
        # AppConfig - appconfigdata is runtime-only
        "appconfig": ["appconfig"],
        # AppMesh preview uses appmesh client
        "appmesh-preview": ["appmesh"],
        # Cassandra (Keyspaces)
        "cassandra": ["keyspaces"],
        # Service Catalog uses 'catalog' in ARNs but 'servicecatalog' client
        "catalog": ["servicecatalog"],
        # CloudHSM v2
        "cloudhsm": ["cloudhsmv2"],
        # CloudSearch - cloudsearchdomain is for search queries only
        "cloudsearch": ["cloudsearch"],
        # CloudWatch uses 'monitoring' as endpointPrefix but 'cloudwatch' in ARNs
        "cloudwatch": ["cloudwatch"],
        # Connect - connect-contact-lens is analytics only
        "connect": ["connect"],
        # Connect Campaigns v2
        "connect-campaigns": ["connectcampaignsv2"],
        # Elasticsearch -> OpenSearch
        "es": ["opensearch"],
        # Execute API (API Gateway WebSocket/HTTP management)
        "execute-api": ["apigatewaymanagementapi"],
        # Forecast - forecastquery is runtime-only
        "forecast": ["forecast"],
        # Kinesis Analytics v2
        "kinesisanalytics": ["kinesisanalyticsv2"],
        # Kinesis Video - other clients are for media streaming
        "kinesisvideo": ["kinesisvideo"],
        # Migration Hub
        "mgh": ["mgh"],
        # Partner Central has multiple sub-clients
        "partnercentral": [
            "partnercentral-account",
            "partnercentral-benefits",
            "partnercentral-channel",
            "partnercentral-selling",
        ],
        # Payment Cryptography - payment-cryptography-data is for crypto operations
        "payment-cryptography": ["payment-cryptography"],
        # Personalize - events/runtime are runtime-only
        "personalize": ["personalize"],
        # AWS Private 5G uses privatenetworks client
        "private-networks": ["privatenetworks"],
        # RDS - docdb/neptune share ARN format but are different engines
        "rds": ["rds"],
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

    # Discontinued/EOL services
    EXCLUDES_DISCONTINUED = {
        "a4b",  # Alexa for Business
        "bugbust",  # AWS BugBust
        "codestar",  # CodeStar
        "elastic-inference",  # EOL April 2024
        "elastictranscoder",  # Replaced by MediaConvert
        "honeycode",  # Honeycode
        "iotfleethub",  # EOL October 2025
        "lookoutmetrics",  # Lookout for Metrics
        "lookoutvision",  # Lookout for Vision
        "monitron",  # Monitron
        "nimble",  # Nimble Studio
        "opsworks",  # OpsWorks Stacks - EOL May 2024
        "opsworks-cm",  # OpsWorks Chef/Puppet - EOL 2024
        "qldb",  # QLDB - EOL 2025
        "robomaker",  # RoboMaker - EOL 2025
        "worklink",  # WorkLink
    }

    # Console-only services (no SDK)
    EXCLUDES_CONSOLE = {
        "appstudio",  # AWS App Studio
        "cloudshell",  # AWS CloudShell
        "consoleapp",  # Console Mobile App
        "elemental-appliances-software",  # Physical hardware
        "elemental-support-cases",  # Support tickets
        "identity-sync",  # Identity sync
        "iq",  # AWS IQ
        "iq-permission",  # AWS IQ
        "mapcredits",  # AWS MAP credits
        "one",  # Amazon One Enterprise (palm recognition)
        "payments",  # Billing payments
        "pricingplanmanager",  # Pricing plans
        "purchase-orders",  # Billing purchase orders
        "securityagent",  # AWS Security Agent (preview)
        "sqlworkbench",  # Redshift Query Editor
        "ts",  # AWS Diagnostic Tools
        "vendor-insights",  # Marketplace Vendor Insights
    }

    # Services using non-boto3 SDK (IDE plugins, CLI, OpenAI SDK, etc.)
    EXCLUDES_NOSDK = {
        "apptest",  # AWS Application Testing
        "bedrock-mantle",  # Uses OpenAI SDK
        "codewhisperer",  # IDE extension (now Q Developer)
        "freertos",  # FreeRTOS device SDK
        "qdeveloper",  # IDE plugins only
        "transform",  # CLI only
        "transform-custom",  # CLI only
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
            excludes = self.EXCLUDES_DISCONTINUED | self.EXCLUDES_CONSOLE | self.EXCLUDES_NOSDK
            if arn_service in excludes:
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
