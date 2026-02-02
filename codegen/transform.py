"""Transform resource data before export.

This module normalizes resource type names to kebab-case for consistency.
"""

import logging
import re

log = logging.getLogger(__name__)


class Transformer:
    """Transforms resource data before code generation."""

    def process_camel_case(self, name):
        """Convert camelCase or PascalCase to kebab-case.

        Only transforms if the name contains uppercase letters [A-Z].
        Handles abbreviations by treating consecutive uppercase as a unit.

        Examples:
            backupVault -> backup-vault
            Analyzer -> analyzer
            CodeSigningConfig -> code-signing-config
            API -> api
            APIGateway -> api-gateway
            EC2Instance -> ec2-instance
            bucket -> bucket (unchanged)
            certificate-authority -> certificate-authority (unchanged)
        """
        if not re.search(r"[A-Z]", name):
            return name
        # Split before last char of uppercase sequence followed by lowercase (APIGateway -> API-Gateway)
        result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", name)
        # Split between lowercase/digit and uppercase (backupVault -> backup-Vault, EC2Instance -> EC2-Instance)
        result = re.sub(r"([a-z\d])([A-Z])", r"\1-\2", result)
        return result.lower()

    def process(self, resources):
        """Transform resources, normalizing resource_type names.

        Args:
            resources: List of resource dicts with keys:
                - service, arn_service, resource_type, arn_pattern

        Returns:
            List of transformed resource dicts.
        """
        transformed_count = 0
        result = []
        for r in resources:
            original = r["resource_type"]
            normalized = self.process_camel_case(original)
            if normalized != original:
                transformed_count += 1
                r = {**r, "resource_type": normalized}
            result.append(r)

        self.metrics = {
            "input": len(resources),
            "transformed": transformed_count,
            "output": len(result),
        }

        return result

    def process_by_service(self, by_service):
        """Transform type_names in the by_service structure.

        Args:
            by_service: Dict of service -> list of (regex, type_names) tuples

        Returns:
            Transformed by_service dict with normalized type_names.
        """
        result = {}
        for service, patterns in by_service.items():
            result[service] = [
                (regex, [self.process_camel_case(name) for name in type_names])
                for regex, type_names in patterns
            ]
        return result
