# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3"]
# ///

"""Maps ARN service names to AWS SDK (boto3) client names."""

import gzip
import json
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)


class SDKServiceIndexer:
    """Builds mapping from ARN service names to AWS SDK client names."""

    # Phase 3: Manual overrides for services where botocore metadata doesn't match
    # Format: "arn_service" -> ["sdk_client1", "sdk_client2", ...]
    OVERRIDES = {
        # CloudWatch uses 'monitoring' as endpointPrefix but 'cloudwatch' in ARNs
        "cloudwatch": ["cloudwatch"],
        # Route53 recovery services
        "route53-recovery-control": [
            "route53-recovery-cluster",
            "route53-recovery-control-config",
        ],
        # S3 variants map to s3 client
        "s3-object-lambda": ["s3"],
        "s3express": ["s3"],
        # RDS IAM auth uses rds client
        "rds-db": ["rds"],
    }

    # Services that are deprecated/console-only and have no SDK client
    # These will be explicitly mapped to empty list
    EXCLUDES = {
        "a4b",  # Alexa for Business - discontinued
        "bugbust",  # AWS BugBust - discontinued
        "codestar",  # CodeStar - discontinued
        "consoleapp",  # Console Mobile App
        "honeycode",  # Honeycode - discontinued
        "iq",  # AWS IQ
        "iq-permission",  # AWS IQ
        "lookoutmetrics",  # Lookout for Metrics - discontinued
        "lookoutvision",  # Lookout for Vision - discontinued
        "monitron",  # Monitron - discontinued
        "nimble",  # Nimble Studio - discontinued
        "qldb",  # QLDB - end of life 2025
        "robomaker",  # RoboMaker - end of life 2025
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
            log.warning(f"No SDK client mapping for ARN service: {arn_service}")
            result[arn_service] = []

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

            try:
                with gzip.open(service_file) as f:
                    data = json.load(f)
                    metadata[sdk_service] = data.get("metadata", {})
            except Exception as e:
                log.warning(f"Failed to load {service_file}: {e}")

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
