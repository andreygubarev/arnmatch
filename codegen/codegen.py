# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "joblib", "beautifulsoup4", "boto3"]
# ///

import json
import logging
import re
from pathlib import Path

from scraper import AWSScraper
from index_arn import ARNIndexer
from index_cfn import CFNServiceIndexer
from index_sdk import SDKServiceIndexer
from index_sdk_resources import SDKResourceIndexer

log = logging.getLogger(__name__)

CODEGEN_DIR = Path(__file__).parent
BUILD_DIR = CODEGEN_DIR / "build"


class CodeGenerator:
    """Generates Python code from processed ARN resources."""

    # Placeholder patterns: map placeholder name -> regex pattern
    # Based on AWS regex: ^arn:[\w+=/,.@-]+:service:[\w+=/,.@-]*:[0-9]+:...
    PLACEHOLDER_PATTERNS = {
        "Partition": r"[\w-]+",  # aws, aws-cn, aws-us-gov
        "Region": r"[\w-]*",  # us-east-1, eu-west-1, or empty
        "Account": r"\d{12}",  # AWS accounts are always 12 digits
    }

    # Type aliases: map AWS doc type -> list of known aliases
    TYPE_ALIASES = {
        ("elasticloadbalancing", "loadbalancer/app/"): ["loadbalancer/app"],
        ("elasticloadbalancing", "loadbalancer/net/"): ["loadbalancer/net"],
        ("elasticloadbalancing", "loadbalancer/gwy/"): ["loadbalancer/gwy"],
        ("events", "rule-on-default-event-bus"): ["rule"],
        ("secretsmanager", "Secret"): ["secret"],
        ("mq", "configurations"): ["configuration"],
        ("inspector", "target-template"): ["target/template"],
        ("backup", "backupPlan"): ["backup-plan"],
        ("backup", "backupVault"): ["backup-vault"],
        ("ssm", "resourcedatasync"): ["resource-data-sync"],
        ("s3", "storagelensconfiguration"): ["storage-lens"],
        ("dms", "ReplicationSubnetGroup"): ["subgrp"],
    }

    def process(self, resources):
        """Process resources into service-grouped patterns with regexes."""
        by_service = {}
        for r in resources:
            service = r["arn_service"]
            if service not in by_service:
                by_service[service] = []
            regex = self.pattern_to_regex(r["arn_pattern"])
            type_names = self.get_type_names(service, r["resource_type"])
            by_service[service].append((regex, type_names))
        return by_service

    def generate(self, by_service, sdk_services_mapping, output_path):
        """Generate Python file with ARN patterns and SDK services mapping."""
        with open(output_path, "w") as f:
            f.write("# Auto-generated ARN patterns for matching\n")
            f.write("# Patterns are ordered: most specific first\n")
            f.write("import re\n\n")
            f.write("ARN_PATTERNS = {\n")

            for service, patterns in by_service.items():
                f.write(f"    {service!r}: [\n")
                for regex, type_names in patterns:
                    f.write(f'        (re.compile(r"{regex}"), {type_names!r}),\n')
                f.write("    ],\n")

            f.write("}\n\n")

            # Write SDK services mapping
            f.write("# Auto-generated mapping: ARN service -> AWS SDK client names\n")
            f.write("AWS_SDK_SERVICES = {\n")
            for arn_service, clients in sorted(sdk_services_mapping.items()):
                f.write(f"    {arn_service!r}: {clients!r},\n")
            f.write("}\n\n")

            # Write SDK default service mapping
            f.write("# Default SDK for multi-SDK services\n")
            f.write("AWS_SDK_SERVICES_DEFAULT = {\n")
            for arn_service, sdk in sorted(SDKResourceIndexer.DEFAULT_SERVICE.items()):
                f.write(f"    {arn_service!r}: {sdk!r},\n")
            f.write("}\n\n")

            # Write SDK service overrides (resource-level)
            f.write("# Resource-level SDK overrides: resource_type -> sdk_client\n")
            f.write("AWS_SDK_SERVICES_OVERRIDE = {\n")
            for arn_service, overrides in sorted(SDKResourceIndexer.OVERRIDE_SERVICE.items()):
                f.write(f"    {arn_service!r}: {overrides!r},\n")
            f.write("}\n")

        pattern_count = sum(len(patterns) for patterns in by_service.values())
        log.info(f"Wrote {pattern_count} patterns for {len(by_service)} services to {output_path}")
        log.info(f"Wrote SDK mapping for {len(sdk_services_mapping)} services")

    def pattern_to_regex(self, arn_pattern):
        """Convert ARN pattern to regex with named capture groups."""
        placeholders = []

        def capture_var(m):
            placeholders.append(m.group(1))
            return f"\x00{len(placeholders) - 1}\x00"

        result = re.sub(r"\$\{([^}]+)\}", capture_var, arn_pattern)
        result = result.replace("*", "\x01")
        result = re.escape(result)
        result = result.replace("\\-", "-")

        for i, name in enumerate(placeholders):
            pattern = self.PLACEHOLDER_PATTERNS.get(name, ".+?")
            result = result.replace(f"\x00{i}\x00", f"(?P<{name}>{pattern})")

        result = result.replace("\x01", ".*")
        return f"^{result}$"

    def get_type_names(self, service, resource_type):
        """Get list of type names: primary type + any aliases."""
        types = [resource_type]
        aliases = self.TYPE_ALIASES.get((service, resource_type), [])
        types.extend(aliases)
        return types


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Scrape
    scraper = AWSScraper()
    services = scraper.get_services()
    resources = []
    for svc in services:
        resources.extend(scraper.get_resources(svc["href"]))

    # Save raw resources to JSON (for reference/debugging)
    BUILD_DIR.mkdir(exist_ok=True)
    raw_resources = sorted(
        [dict(t) for t in {tuple(r.items()) for r in resources}],
        key=lambda r: (r["service"], r["resource_type"], -len(r["arn_pattern"]), r["arn_pattern"]),
    )
    with open(BUILD_DIR / "arn_resources.json", "w") as f:
        json.dump(raw_resources, f, indent=2)
    log.info(f"Wrote {len(raw_resources)} raw resources to arn_resources.json")

    # Process ARN patterns
    indexer = ARNIndexer()
    resources = indexer.process(resources)

    # Build SDK services mapping
    arn_services = {r["arn_service"] for r in resources}
    sdk_indexer = SDKServiceIndexer()
    sdk_mapping = sdk_indexer.process(arn_services)

    # Validate multi-SDK services have DEFAULT_SERVICE entries
    sdk_resource_indexer = SDKResourceIndexer()
    sdk_resource_indexer.process(sdk_mapping)

    # Save SDK mapping to cache
    with open(CODEGEN_DIR / "cache" / "SDKServices.json", "w") as f:
        json.dump(sdk_mapping, f, indent=2)

    cfn_indexer = CFNServiceIndexer()
    cfn_mapping = cfn_indexer.process(sdk_mapping)

    # Generate
    generator = CodeGenerator()
    by_service = generator.process(resources)
    generator.generate(by_service, sdk_mapping, BUILD_DIR / "arn_patterns.py")


if __name__ == "__main__":
    main()
