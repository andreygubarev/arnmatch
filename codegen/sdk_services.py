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
    MANUAL_OVERRIDES = {
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
    NO_SDK_CLIENT = {
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

    def __init__(self, botocore_data_path: str | None = None):
        """Initialize with path to botocore data directory."""
        if botocore_data_path:
            self.botocore_data = Path(botocore_data_path)
        else:
            # Find botocore data directory
            import botocore

            self.botocore_data = Path(botocore.__file__).parent / "data"

    def build_mapping(self, arn_services: set[str]) -> dict[str, list[str]]:
        """Build ARN service -> SDK clients mapping.

        Args:
            arn_services: Set of ARN service names to map

        Returns:
            Dict mapping ARN service name to list of SDK client names
        """
        # Get all boto3 client metadata
        client_metadata = self.load_client_metadata()

        result = {}

        for arn_svc in sorted(arn_services):
            # Phase 3: Check manual overrides first
            if arn_svc in self.MANUAL_OVERRIDES:
                result[arn_svc] = self.MANUAL_OVERRIDES[arn_svc]
                continue

            # Known no-SDK services
            if arn_svc in self.NO_SDK_CLIENT:
                result[arn_svc] = []
                continue

            # Phase 1: Direct name match
            if arn_svc in client_metadata:
                result[arn_svc] = [arn_svc]
                # Also check for additional clients via metadata
                additional = self.find_clients_by_metadata(
                    arn_svc, client_metadata, exclude={arn_svc}
                )
                if additional:
                    result[arn_svc].extend(sorted(additional))
                continue

            # Phase 2: Find via botocore metadata (signingName/endpointPrefix)
            clients = self.find_clients_by_metadata(arn_svc, client_metadata)
            if clients:
                result[arn_svc] = sorted(clients)
                continue

            # No mapping found
            log.warning(f"No SDK client mapping for ARN service: {arn_svc}")
            result[arn_svc] = []

        return result

    def load_client_metadata(self) -> dict[str, dict]:
        """Load metadata for all boto3 clients.

        Returns:
            Dict mapping client name to its metadata
        """
        metadata = {}

        for client_name in os.listdir(self.botocore_data):
            client_path = self.botocore_data / client_name
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
                    metadata[client_name] = data.get("metadata", {})
            except Exception as e:
                log.warning(f"Failed to load {service_file}: {e}")

        return metadata

    def find_clients_by_metadata(
        self,
        arn_service: str,
        client_metadata: dict[str, dict],
        exclude: set[str] | None = None,
    ) -> set[str]:
        """Find SDK clients whose signingName or endpointPrefix matches ARN service.

        Args:
            arn_service: ARN service name to match
            client_metadata: Dict of client name -> metadata
            exclude: Client names to exclude from results

        Returns:
            Set of matching client names
        """
        exclude = exclude or set()
        matches = set()

        for client_name, meta in client_metadata.items():
            if client_name in exclude:
                continue

            # Check signingName first (more specific)
            signing_name = meta.get("signingName")
            if signing_name == arn_service:
                matches.add(client_name)
                continue

            # Check endpointPrefix (fallback)
            endpoint_prefix = meta.get("endpointPrefix")
            if endpoint_prefix == arn_service:
                matches.add(client_name)

        return matches

    def generate_code(self, mapping: dict[str, list[str]]) -> str:
        """Generate Python code for AWS_SDK_SERVICES dict.

        Args:
            mapping: ARN service -> SDK clients mapping

        Returns:
            Python code as string
        """
        lines = [
            "# Auto-generated mapping: ARN service -> AWS SDK client names",
            "AWS_SDK_SERVICES = {",
        ]

        for arn_svc, clients in sorted(mapping.items()):
            lines.append(f"    {arn_svc!r}: {clients!r},")

        lines.append("}")
        lines.append("")

        return "\n".join(lines)
