"""Transform resource data before export.

This module normalizes resource type names to kebab-case for consistency.
"""

import logging

log = logging.getLogger(__name__)


class Transformer:
    """Transforms resource data before code generation."""

    def process(self, resources):
        """Transform resources, normalizing resource_type names.

        Args:
            resources: List of resource dicts with keys:
                - service, arn_service, resource_type, arn_pattern

        Returns:
            List of transformed resource dicts.
        """
        # TODO: Implement kebab-case normalization for resource_type
        result = resources

        self.metrics = {
            "input": len(resources),
            "transformed": 0,  # Count of names that changed
            "output": len(result),
        }

        return result
