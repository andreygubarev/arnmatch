"""Transform resource data before export.

This module normalizes resource type names to kebab-case for consistency.
"""

import logging
import re

log = logging.getLogger(__name__)


class Transformer:
    """Transforms resource type names at export time."""

    def __init__(self):
        self.transformed_count = 0
        self.total_count = 0

    def process(self, name):
        """Transform a resource type name through all phases.

        Args:
            name: Original resource type name.

        Returns:
            Transformed name in kebab-case.
        """
        self.total_count += 1
        result = self.process_camel_case(name)
        if result != name:
            self.transformed_count += 1
        return result

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

    @property
    def metrics(self):
        return {
            "total": self.total_count,
            "transformed": self.transformed_count,
        }
