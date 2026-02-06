# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "joblib", "beautifulsoup4", "boto3", "ruamel.yaml"]
# ///

import json
import logging
import re
from pathlib import Path

from ruamel.yaml import YAML

from scraper import AWSScraper
from index_arn import ARNIndexer
from index_cfn import CFNServiceIndexer
from index_cfn_resources import CFNResourceIndexer
from index_sdk import SDKServiceIndexer
from index_sdk_resources import SDKResourceIndexer
from index_tag import TagServiceIndexer
from index_tag_resources import TagResourceIndexer
from transform import Transformer

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
        type_aliases_count = 0
        for r in resources:
            service = r["arn_service"]
            if service not in by_service:
                by_service[service] = []
            regex = self.pattern_to_regex(r["arn_pattern"])
            type_names = self.get_type_names(service, r["resource_type"])
            if len(type_names) > 1:
                type_aliases_count += 1
            by_service[service].append((regex, type_names))

        self.metrics = {
            "services": len(by_service),
            "patterns": sum(len(p) for p in by_service.values()),
            "type_aliases": type_aliases_count,
        }

        return by_service

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

    def get_botoclient(self, arn_service, resource_type, sdk_mapping):
        """Get the boto3 client for a resource type."""
        clients = sdk_mapping.get(arn_service, [])
        if not clients:
            return None
        if len(clients) == 1:
            return clients[0]
        # Multi-SDK: check override first, then default
        overrides = SDKResourceIndexer.OVERRIDE_SERVICE.get(arn_service, {})
        if resource_type in overrides:
            return overrides[resource_type]
        return SDKResourceIndexer.DEFAULT_SERVICE[arn_service]

    def export(self, resources, sdk_mapping, cfn_resources_mapping, tag_resources_mapping, transformer, output_path):
        """Export patterns to YAML source of truth format."""
        # Group resources by (arn_service, resource_type) to collect multiple ARN patterns
        grouped = {}
        for r in resources:
            key = (r["arn_service"], r["resource_type"])
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(r["arn_pattern"])

        # Build structure grouped by arn_service
        by_service = {}
        for (arn_service, resource_type), arns in grouped.items():
            if arn_service not in by_service:
                by_service[arn_service] = []

            # Get type names (canonical + aliases)
            original_names = self.get_type_names(arn_service, resource_type)
            # Build names list: transformed first, then originals (deduplicated)
            names = []
            for n in original_names:
                transformed = transformer.process(n)
                names.append(transformed)
                if transformed != n:
                    names.append(n)
            names = list(dict.fromkeys(names))  # Dedupe preserving order

            # Get botoclient
            botoclient = self.get_botoclient(arn_service, resource_type, sdk_mapping)

            # Get cloudformation type (lookup with original name)
            cfn_type = cfn_resources_mapping.get(arn_service, {}).get(resource_type)

            # Get tagging type (lookup with original name)
            tag_type = tag_resources_mapping.get(arn_service, {}).get(resource_type)

            # Transform resource_type for output
            transformed_type = transformer.process(resource_type)

            entry = {
                "name": transformed_type,
                "names": names,
                "arns": arns,
                "botoclient": botoclient,
                "cloudformation": cfn_type,
                "tagging": tag_type,
            }
            by_service[arn_service].append(entry)

        # Sort services alphabetically, resources alphabetically by name
        from ruamel.yaml.comments import CommentedMap, CommentedSeq

        output = CommentedMap()
        sorted_services = sorted(by_service.keys())
        for i, service in enumerate(sorted_services):
            # Add blank line before each service (except first)
            if i > 0:
                output.yaml_set_comment_before_after_key(service, before="\n")
            entries = sorted(by_service[service], key=lambda r: r["name"])
            service_list = CommentedSeq()
            for entry in entries:
                item = CommentedMap()
                item["name"] = entry["name"]
                item["names"] = CommentedSeq(entry["names"])
                item["arns"] = CommentedSeq(entry["arns"])
                item["botoclient"] = entry["botoclient"]
                item["cloudformation"] = entry["cloudformation"]
                item["tagging"] = entry["tagging"]
                service_list.append(item)
            output[service] = service_list

        yml = YAML()
        yml.default_flow_style = False
        yml.indent(mapping=2, sequence=4, offset=2)
        with open(output_path, "w") as f:
            yml.dump(output, f)

        log.info(f"Wrote {output_path}")


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

    # Build Tagging API services mapping
    tag_indexer = TagServiceIndexer()
    tag_mapping = tag_indexer.process(sdk_mapping)

    # Generate
    generator = CodeGenerator()
    by_service = generator.process(resources)

    cfn_resource_indexer = CFNResourceIndexer()
    cfn_resources_mapping = cfn_resource_indexer.process(by_service, cfn_mapping)

    tag_resource_indexer = TagResourceIndexer()
    tag_resources_mapping = tag_resource_indexer.process(by_service, tag_mapping)

    # Transform resource names at export time
    transformer = Transformer()

    generator.export(resources, sdk_mapping, cfn_resources_mapping, tag_resources_mapping, transformer, BUILD_DIR / "arn_patterns.yaml")

    # Collect and save metrics
    metrics = {
        "scraper": {"services": len(services), "resources_raw": len(raw_resources)},
        "arn_indexer": indexer.metrics,
        "sdk_service_indexer": sdk_indexer.metrics,
        "sdk_resource_indexer": sdk_resource_indexer.metrics,
        "cfn_service_indexer": cfn_indexer.metrics,
        "cfn_resource_indexer": cfn_resource_indexer.metrics,
        "tag_service_indexer": tag_indexer.metrics,
        "tag_resource_indexer": tag_resource_indexer.metrics,
        "transformer": transformer.metrics,
        "generator": generator.metrics,
    }
    with open(BUILD_DIR / "codegen_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print_summary(metrics)


def print_summary(metrics):
    """Print a concise summary of codegen metrics."""
    print("\n=== Codegen Metrics ===")

    s = metrics["scraper"]
    print(f"Scrape:        {s['services']} services, {s['resources_raw']} resources")

    a = metrics["arn_indexer"]
    print(f"ARN Index:     in={a['input']} → filter=-{a['filtered_by_arn'] + a['filtered_by_resource']} "
          f"dedupe=-{a['duplicates_removed']} override={a['overrides_applied']} "
          f"include=+{a['includes_added']} → out={a['output']}")

    sdk = metrics["sdk_service_indexer"]
    print(f"SDK Services:  in={sdk['input']} → direct={sdk['direct_match']} meta={sdk['metadata_match']} "
          f"override={sdk['override']} exclude={sdk['excluded']} multi={sdk['multi_sdk']} → out={sdk['output']}")

    sdkr = metrics["sdk_resource_indexer"]
    print(f"SDK Resources: multi={sdkr['multi_sdk_services']} defaults={sdkr['with_default']} "
          f"overrides={sdkr['with_overrides']}")

    cfn = metrics["cfn_service_indexer"]
    print(f"CFN Services:  in={cfn['cfn_services_total']} → direct={cfn['direct_match']} "
          f"override={cfn['override']} exclude={cfn['excluded']} → mapped={cfn['mapped_to_arn']}")

    cfnr = metrics["cfn_resource_indexer"]
    print(f"CFN Resources: exact={cfnr['exact_match']} plural={cfnr['plural_match']} "
          f"override={cfnr['override']} exclude={cfnr['excluded']} missing={cfnr['missing']} → mapped={cfnr['mapped']}")

    tag = metrics["tag_service_indexer"]
    print(f"Tag Services:  in={tag['tagging_services_total']} → direct={tag['direct_match']} "
          f"override={tag['override']} exclude={tag['excluded']} → mapped={tag['mapped_to_arn']}")

    tagr = metrics["tag_resource_indexer"]
    print(f"Tag Resources: exact={tagr['exact_match']} plural={tagr['plural_match']} "
          f"override={tagr['override']} exclude={tagr['excluded']} missing={tagr['missing']} → mapped={tagr['mapped']}")

    t = metrics["transformer"]
    print(f"Transform:     total={t['total']} transformed={t['transformed']}")

    g = metrics["generator"]
    print(f"Generator:     {g['services']} services, {g['patterns']} patterns, {g['type_aliases']} aliases")


if __name__ == "__main__":
    main()
