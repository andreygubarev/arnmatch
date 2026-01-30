"""Maps ARN resource types to specific SDK clients for multi-SDK services.

Why aws_sdk_services (plural) exists alongside aws_sdk_service (singular):

Some services share identical ARN formats but are fundamentally different engines.
For example, RDS, Neptune, and DocumentDB all use the same ARN structure:
  arn:aws:rds:region:account:db:instance-name

The ARN alone cannot distinguish between these engines - you need external context
(tags, API calls, or prior knowledge) to determine the correct SDK. In these cases,
aws_sdk_service returns the default (rds), while aws_sdk_services returns all
possible SDKs [rds, neptune, docdb] for the caller to disambiguate.
"""

from utils import load_rules


class SDKResourceIndexer:
    """SDK defaults for services with multiple SDK clients.

    DEFAULT_SERVICE: Service-level default where all resources use a single SDK.
    Format: "arn_service" -> "sdk_client"

    OVERRIDE_SERVICE: Resource-level overrides where different resources use different SDKs.
    Format: "arn_service" -> {"resource_type": "sdk_client", ...}
    """

    # Service-level default - the SDK responsible for most resources
    DEFAULT_SERVICE = load_rules("sdk_resources_defaults.json")

    # Resource-level overrides - only non-default SDK mappings
    OVERRIDE_SERVICE = load_rules("sdk_resources_overrides.json")

    def process(self, sdk_mapping):
        """Validate all multi-SDK services have a DEFAULT_SERVICE entry."""
        missing = {}
        for arn_service, sdks in sdk_mapping.items():
            if len(sdks) > 1 and arn_service not in self.DEFAULT_SERVICE:
                missing[arn_service] = sdks
        if missing:
            raise RuntimeError(f"Missing DEFAULT_SERVICE for multi-SDK services: {missing}")

        self.metrics = {
            "multi_sdk_services": len([s for s in sdk_mapping.values() if len(s) > 1]),
            "with_default": len(self.DEFAULT_SERVICE),
            "with_overrides": len(self.OVERRIDE_SERVICE),
        }
