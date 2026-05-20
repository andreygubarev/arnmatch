# Contributing to arnmatch

Thanks for helping improve `arnmatch`. Contributions that add missing ARN patterns,
fix resource mappings, improve documentation, or strengthen tests are welcome.

## Development setup

Prerequisite: [uv](https://github.com/astral-sh/uv)

```bash
git clone https://github.com/andreygubarev/arnmatch.git
cd arnmatch
uv sync --all-groups
make check
```

Useful commands:

```bash
make lint       # Run ruff
make test       # Run pytest
make check      # Run lint and tests
make generate   # Regenerate ARN pattern data from AWS docs
make build      # Build package artifacts
```

## Reporting missing or incorrect ARN support

If an ARN does not parse, or parses to the wrong resource type/mapping, please
open an issue with:

- The ARN format, with account IDs or sensitive names redacted
- The expected AWS service and resource type
- The expected CloudFormation or Resource Groups Tagging API type, if known
- A link to the relevant AWS documentation, if available

Example redaction:

```text
arn:aws:lambda:us-east-1:123456789012:function:example-function
```

## Fixing ARN patterns or mappings

Most parser data is generated. Prefer updating code generation rules instead of
editing `src/arnmatch/arn_patterns.py` directly.

Common rule files:

- `codegen/rules/arn_overrides.json` — fix documented ARN patterns
- `codegen/rules/arn_includes.json` — add missing AWS documentation entries
- `codegen/rules/arn_excludes.json` — remove problematic entries
- `codegen/rules/cfn_resources_overrides.json` — fix CloudFormation mappings
- `codegen/rules/tag_resources_overrides.json` — fix Tagging API mappings
- `codegen/rules/sdk_overrides.json` — fix boto3 service mappings

After changing codegen inputs, regenerate and test:

```bash
make generate
make build
make check
```

## Pull request checklist

Before opening a pull request, please verify:

- [ ] `make check` passes
- [ ] New behavior has a test when practical
- [ ] Generated files are updated when codegen inputs changed
- [ ] README or docs are updated for user-facing changes
- [ ] No real AWS account IDs, ARNs, or credentials are committed

## Release process

Maintainers publish releases by tagging CalVer versions in the format
`YYYY.MM.MICRO`, for example `2026.3.3`. The release workflow builds and
publishes the package to PyPI.
