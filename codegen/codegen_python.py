# /// script
# requires-python = ">=3.10"
# dependencies = ["ruamel.yaml"]
# ///

"""Generate arn_patterns.py from arn_patterns.yaml."""

import json
import re
from pathlib import Path

from ruamel.yaml import YAML

CODEGEN_DIR = Path(__file__).parent
BUILD_DIR = CODEGEN_DIR / "build"
CACHE_DIR = CODEGEN_DIR / "cache"

PLACEHOLDER_PATTERNS = {
    "Partition": r"[\w-]+",
    "Region": r"[\w-]*",
    "Account": r"\d{12}",
}


class PythonGenerator:
    def load_yaml(self, path: Path) -> dict:
        yaml = YAML()
        with open(path) as f:
            return yaml.load(f)

    def load_json(self, path: Path) -> dict:
        with open(path) as f:
            return json.load(f)

    def pattern_to_regex(self, arn_pattern: str) -> str:
        """Convert ${Placeholder} to regex capture groups."""
        placeholders = []

        def capture_var(m):
            placeholders.append(m.group(1))
            return f"\x00{len(placeholders) - 1}\x00"

        result = re.sub(r"\$\{([^}]+)\}", capture_var, arn_pattern)
        result = result.replace("*", "\x01")
        result = re.escape(result)
        result = result.replace("\\-", "-")

        for i, name in enumerate(placeholders):
            optional = name.endswith("?")
            if optional:
                name = name[:-1]
            pattern = PLACEHOLDER_PATTERNS.get(name, ".+?")
            group = f"(?P<{name}>{pattern})?" if optional else f"(?P<{name}>{pattern})"
            result = result.replace(f"\x00{i}\x00", group)

        result = result.replace("\x01", ".*")
        return f"^{result}$"

    def sort_key(self, arn_pattern: str):
        """Sort patterns by specificity (more segments first)."""
        parts = arn_pattern.split(":", 5)
        resource = parts[5] if len(parts) > 5 else ""
        segments = re.split(r"[/:]", resource)

        def normalize(v):
            v = re.sub(r"\$\{[^}]+\}", "~", v)
            return v.replace("*", "~~")

        return (
            normalize(parts[2] if len(parts) > 2 else ""),
            normalize(parts[3] if len(parts) > 3 else ""),
            normalize(parts[4] if len(parts) > 4 else ""),
            -len(segments),
            [normalize(s) for s in segments],
        )

    def generate(self, yaml_path: Path, sdk_cache_path: Path, output_path: Path):
        data = self.load_yaml(yaml_path)

        # Load SDK services mapping (service-level, from cache)
        sdk_services = self.load_json(sdk_cache_path)

        # Build patterns
        arn_patterns = {}

        for service, resources in data.items():
            patterns = []

            for resource in resources:
                sdk = resource.get("botoclient")
                cfn = resource.get("cloudformation")
                tag = resource.get("tagging")
                names = resource["names"]

                for arn in resource["arns"]:
                    patterns.append({
                        "arn": arn,
                        "regex": self.pattern_to_regex(arn),
                        "names": names,
                        "sdk": sdk,
                        "cfn": cfn,
                        "tag": tag,
                    })

            # Sort by specificity
            patterns.sort(key=lambda p: self.sort_key(p["arn"]))
            arn_patterns[service] = patterns

        # Write Python file
        with open(output_path, "w") as f:
            f.write("# Auto-generated from arn_patterns.yaml\n")
            f.write("import re\n\n")

            f.write("ARN_PATTERNS = {\n")
            for service in sorted(arn_patterns.keys()):
                f.write(f"    {service!r}: [\n")
                for p in arn_patterns[service]:
                    f.write(f"        {{'regex': re.compile(r\"{p['regex']}\"), ")
                    f.write(f"'names': {p['names']!r}, ")
                    f.write(f"'sdk': {p['sdk']!r}, ")
                    f.write(f"'cfn': {p['cfn']!r}, ")
                    f.write(f"'tag': {p['tag']!r}}},\n")
                f.write("    ],\n")
            f.write("}\n\n")

            f.write("AWS_SDK_SERVICES = {\n")
            for service in sorted(sdk_services.keys()):
                f.write(f"    {service!r}: {sdk_services[service]!r},\n")
            f.write("}\n")


def main():
    generator = PythonGenerator()
    generator.generate(
        BUILD_DIR / "arn_patterns.yaml",
        CACHE_DIR / "SDKServices.json",
        BUILD_DIR / "arn_patterns.py",
    )
    print(f"Generated {BUILD_DIR / 'arn_patterns.py'}")


if __name__ == "__main__":
    main()
