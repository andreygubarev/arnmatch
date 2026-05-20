# How it works

`arnmatch` generates its parser data instead of hand-writing ARN definitions. This lets it stay current with AWS as services and resource types evolve.

## Data pipeline

```text
AWS docs + service metadata
        ↓
   codegen pipeline
        ↓
generated ARN regex patterns and mappings
        ↓
zero-dependency Python parser
```

## Sources

The code generation pipeline collects and reconciles metadata from:

1. **AWS Service Authorization Reference** — ARN patterns for IAM actions.
2. **CloudFormation resource specifications** — CFN resource type names.
3. **Resource Groups Tagging API resource mappings** — Tagging API type names.
4. **botocore/boto3 service metadata** — SDK client names.
5. **Project override rules** — Corrections for AWS documentation edge cases.

## Generated output

The pipeline produces `src/arnmatch/arn_patterns.py`, which contains:

- Compiled regex patterns for each AWS service.
- Mappings to CloudFormation resource types.
- Mappings to Resource Groups Tagging API types.
- Mappings to boto3 SDK client names.

At runtime, `arnmatch` looks up the service in a compiled dictionary and tries each pattern in order of specificity. The first match returns an `ARN` object with all captured groups and mappings.

## Why zero dependencies?

The generated module contains only Python literals and compiled `re.Pattern` objects. There are no network calls, no JSON or YAML parsers, and no external packages required at runtime. This makes arnmatch safe to embed in security tools, lambdas, and CLI utilities where dependency trees matter.

## Updating patterns

For most users, installing the latest published version from PyPI is enough.

If you are contributing new AWS service or resource support, regenerate the patterns from the repository root:

```bash
make generate
make build
make check
```

The generated files are based on cached AWS metadata in `codegen/cache/`. Refresh those caches when AWS has released new resource types and the generated mappings look stale.

For detailed contributor instructions, including CloudFormation and Resource Groups Tagging API cache refreshes, see the [code generation reference](../reference/codegen.md).
