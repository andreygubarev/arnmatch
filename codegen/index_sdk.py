# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3"]
# ///

"""Maps ARN service names to AWS SDK (boto3) client names."""

from utils import botocore_metadata, load_rules


class SDKServiceIndexer:
    """Builds mapping from ARN service names to AWS SDK client names."""

    # Manual overrides: ARN service -> SDK clients
    OVERRIDES = load_rules("sdk_overrides.json")

    # Excluded services by category
    _EXCLUDES = load_rules("sdk_excludes.json")
    EXCLUDES = set(_EXCLUDES["discontinued"]) | set(_EXCLUDES["console_only"]) | set(_EXCLUDES["non_boto3"])

    def process(self, arn_services):
        """Build ARN service -> SDK clients mapping."""
        # Get all boto3 client metadata
        metadata = self.metadata_load()

        result = {}

        for arn_service in sorted(arn_services):
            # Check manual overrides first
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
            sdk_services = self.metadata_match(arn_service, metadata)
            if sdk_services:
                result[arn_service] = sorted(sdk_services)
                continue

            # No mapping found
            raise ValueError(f"No SDK client mapping for ARN service: {arn_service}")

        return result

    def metadata_load(self):
        """Load metadata for all boto3 clients."""
        return botocore_metadata()

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
