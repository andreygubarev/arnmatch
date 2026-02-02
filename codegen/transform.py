"""Transform resource data before export.

This module normalizes resource type names to kebab-case for consistency.
"""

import json
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

RULES_DIR = Path(__file__).parent / "rules"


class Transformer:
    """Transforms resource type names at export time."""

    def __init__(self):
        self.transformed_count = 0
        self.total_count = 0
        self.lowercase_transforms = self._load_lowercase_transforms()

    def _load_lowercase_transforms(self):
        """Load lowercase compound word transforms from rules file."""
        path = RULES_DIR / "lowercase_transforms.json"
        with open(path) as f:
            data = json.load(f)
        # Filter out empty values (no transform needed)
        return {k: v for k, v in data.items() if v}

    def process(self, name):
        """Transform a resource type name through all phases.

        Args:
            name: Original resource type name.

        Returns:
            Transformed name in kebab-case.
        """
        self.total_count += 1
        result = name
        result = self.process_camel_case(result)
        result = self.process_spaces(result)
        result = self.process_underscores(result)
        result = self.process_slashes(result)
        result = self.process_lowercase(result)
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

    def process_spaces(self, name):
        """Replace spaces with hyphens.

        Examples:
            bot alias -> bot-alias
            code signing config -> code-signing-config
        """
        if " " not in name:
            return name
        return name.replace(" ", "-")

    def process_underscores(self, name):
        """Replace underscores with hyphens.

        Examples:
            es_role -> es-role
            harvest_jobs -> harvest-jobs
        """
        if "_" not in name:
            return name
        return name.replace("_", "-")

    def process_slashes(self, name):
        """Replace slashes with hyphens and strip trailing hyphens.

        Examples:
            loadbalancer/app/ -> loadbalancer-app
            listener/net -> listener-net
            listener-rule/app -> listener-rule-app
        """
        if "/" not in name:
            return name
        return name.replace("/", "-").rstrip("-")

    def process_lowercase(self, name):
        """Transform all-lowercase compound words using rules file.

        Examples:
            accesspoint -> access-point
            loadbalancer -> load-balancer
            storagelensconfiguration -> storage-lens-configuration
        """
        return self.lowercase_transforms.get(name, name)

    @property
    def metrics(self):
        return {
            "total": self.total_count,
            "transformed": self.transformed_count,
        }
