# arnmatch - AI Agent Guide

## Project Overview

arnmatch is a zero-dependency Python library that parses AWS ARNs (Amazon Resource Names) into structured data. It supports 300+ AWS services and 2000+ resource types. The library provides both a programmatic API and a CLI interface.

Key characteristics:
- **Zero runtime dependencies** - only standard library
- **Auto-generated patterns** - scraped from AWS official documentation
- **Dual interface** - CLI (`arnmatch <arn>`) and library (`arnmatch.arnmatch()`)
- **Versioning** - CalVer format `YYYY.0M.MICRO` (e.g., `2026.01.3`)

## Technology Stack

- **Language**: Python 3.10+
- **Build System**: [hatchling](https://hatch.pypa.io/)
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (required for development)
- **Linter**: [ruff](https://docs.astral.sh/ruff/)
- **Testing**: pytest

## Project Structure

```
├── src/arnmatch/              # Core library (zero runtime deps)
│   ├── __init__.py            # Main module: ARN dataclass, arnmatch() function
│   └── arn_patterns.py        # GENERATED FILE - compiled regex patterns
├── codegen/                   # Code generation (has external deps)
│   ├── scraper.py             # Scrapes AWS service authorization reference pages
│   ├── codegen.py             # Main code generator
│   ├── index_arn.py           # Processes raw ARN resources, applies overrides
│   ├── index_sdk.py           # Maps ARN service names to boto3 client names
│   ├── index_sdk_resources.py # Resource-level SDK client mappings
│   ├── index_cfn.py           # Maps services to CloudFormation resource types
│   ├── index_cfn_resources.py # Maps ARN resources to CFN resource types
│   ├── utils.py               # Shared utilities (botocore metadata loader)
│   └── build/                 # Build output (generated patterns)
│       └── arn_patterns.py    # Generated patterns (copied to src/)
├── tests/                     # pytest test suite
│   └── test_arnmatch.py       # Tests for various AWS services
├── Makefile                   # Build automation
├── pyproject.toml             # Project configuration
└── .cache/                    # Scraper cache (joblib)
```

## Build and Development Commands

All commands use `make` and require `uv` to be installed:

```bash
# Linting
make lint               # Run ruff linter

# Testing
make test               # Run pytest tests
make check              # Run both lint and test

# Building
make build              # Copy generated patterns + build wheel/tarball
                        # NOTE: This copies codegen/build/arn_patterns.py to src/arnmatch/

# Publishing
make publish            # Build and upload to PyPI (requires credentials)

# Cleanup
make clean              # Remove build artifacts
```

## Code Generation Workflow

The ARN patterns are auto-generated from AWS documentation. To regenerate:

```bash
cd codegen && uv run codegen.py
```

This will:
1. Scrape AWS service authorization reference pages (cached with joblib)
2. Process resources, apply overrides, filter, deduplicate
3. Build SDK service mappings using botocore metadata
4. Build CloudFormation resource mappings
5. Generate `codegen/build/arn_patterns.py`

After regeneration, run `make build` to copy the patterns to `src/arnmatch/`.

### Code Generation Architecture

**Data Flow:**
```
AWS Docs → scraper.py → raw resources → index_arn.py → processed resources
                                                ↓
botocore metadata → index_sdk.py → SDK mappings → codegen.py
                                                ↓
CFN spec → index_cfn.py → CFN mappings → index_cfn_resources.py
                                                ↓
                                    codegen/build/arn_patterns.py
                                                ↓
                                        make build
                                                ↓
                                    src/arnmatch/arn_patterns.py
```

**Key Components:**

| File | Purpose |
|------|---------|
| `scraper.py` | Fetches AWS docs, extracts service prefixes and resource patterns |
| `index_arn.py` | Processes resources: deduplicates, sorts by specificity, applies `PATTERN_OVERRIDES` and `PATTERN_INCLUDES` |
| `index_sdk.py` | Maps ARN service names to boto3 client names using botocore metadata |
| `index_sdk_resources.py` | Defines `DEFAULT_SERVICE` and `OVERRIDE_SERVICE` for multi-SDK services |
| `index_cfn.py` | Maps services to CloudFormation resource types using CFN spec |
| `index_cfn_resources.py` | Maps ARN resource types to CFN resource types |
| `codegen.py` | Main generator, produces Python file with compiled regex patterns |

### Important Override Files

When AWS docs have errors or omissions, edit these in `codegen/`:

- **`index_arn.py:PATTERN_OVERRIDES`** - Fix incorrect ARN patterns in AWS docs
- **`index_arn.py:PATTERN_INCLUDES`** - Add patterns not in AWS docs (e.g., EKS k8s resources)
- **`index_sdk.py:OVERRIDES`** - Manual ARN service → SDK client mappings
- **`index_sdk.py:EXCLUDES_*`** - Services to exclude (discontinued, console-only, no SDK)
- **`index_sdk_resources.py:DEFAULT_SERVICE`** - Default SDK for multi-SDK services
- **`index_sdk_resources.py:OVERRIDE_SERVICE`** - Resource-level SDK overrides
- **`index_cfn.py:OVERRIDES`** - Manual CFN service → SDK service mappings

## Core Library Architecture

### Main API (`src/arnmatch/__init__.py`)

```python
from arnmatch import arnmatch

result = arnmatch("arn:aws:lambda:us-east-1:123456789012:function:my-function")

# Available attributes:
result.aws_partition      # "aws"
result.aws_service        # "lambda"
result.aws_region         # "us-east-1"
result.aws_account        # "123456789012"
result.resource_type      # "function" (canonical)
result.resource_types     # ["function"] (all known names)
result.attributes         # {"FunctionName": "my-function", ...}

# Properties (computed):
result.resource_id        # "my-function" (heuristic: prefers *Id, then *Name)
result.resource_name      # "my-function" (heuristic: prefers *Name, falls back to resource_id)
result.aws_sdk_services   # ["lambda"] (all possible boto3 clients)
result.aws_sdk_service    # "lambda" (specific client for this resource)
result.cloudformation_resource  # "AWS::Lambda::Function" or None
```

### ARN Dataclass

The `ARN` dataclass is frozen and stores:
- `aws_partition`, `aws_service`, `aws_region`, `aws_account` - ARN components
- `resource_type` - canonical type from AWS docs
- `resource_types` - all known aliases for this type
- `attributes` - dict of all regex capture groups

Properties use `@cached_property` for lazy evaluation.

### Pattern Matching Algorithm

1. Split ARN by `:` into 6 parts (arn, partition, service, region, account, resource)
2. Look up service in `ARN_PATTERNS` dict (O(1))
3. Iterate through patterns for that service (most specific first)
4. Return first match with all capture groups

Pattern ordering is critical - patterns are sorted by specificity:
- More segments come first
- Literal segments come before wildcards
- Variables come before wildcards

## Testing Strategy

Tests are in `tests/test_arnmatch.py` and use pytest:

```bash
make test
```

Test patterns:
- Each major service has a test function (e.g., `test_lambda()`, `test_s3()`)
- Tests verify: resource_type, attributes, SDK mappings, CFN mappings
- Edge cases: multi-SDK services, resource-level overrides

When adding new features or fixing bugs, add corresponding test cases.

## Development Guidelines

### Code Style

- Follow existing code style (ruff enforces this)
- Run `make lint` before committing
- Use type hints where appropriate
- Document public APIs with docstrings

### Adding New Patterns

If AWS docs are missing a pattern:

1. Add to `codegen/index_arn.py:PATTERN_INCLUDES`:
```python
PATTERN_INCLUDES = [
    # (service, arn_pattern, resource_type)
    ("eks", "arn:${Partition}:eks:${Region}:${Account}:pod/${ClusterName}/${Namespace}/${PodName}/${UUID}", "pod"),
]
```

2. Regenerate: `cd codegen && uv run codegen.py`
3. Rebuild: `make build`
4. Test: `make test`

### Fixing Pattern Issues

If AWS docs have incorrect patterns (e.g., wildcards instead of capture groups):

1. Add to `codegen/index_arn.py:PATTERN_OVERRIDES`:
```python
PATTERN_OVERRIDES = {
    ("service", "resource-type"): "arn:${Partition}:service:${Region}:${Account}:resource/${ResourceId}",
}
```

### Version Updates

Version is in `src/arnmatch/__init__.py:__version__` (CalVer format).

Update this when:
- Regenerating patterns (if AWS docs changed)
- Adding new features
- Fixing bugs

## Key Design Decisions

1. **Zero runtime dependencies** - Only standard library in `src/arnmatch/`
2. **Compiled regex patterns** - Generated once, not parsed at runtime
3. **Service-indexed patterns** - O(1) lookup before pattern matching
4. **Specificity-based sorting** - More specific patterns match first
5. **Multi-SDK support** - Some services map to multiple boto3 clients (e.g., `rds` → `["rds", "docdb", "neptune"]`)

## Common Tasks

### Test a specific ARN locally

```bash
uv run arnmatch "arn:aws:lambda:us-east-1:123456789012:function:my-function"
```

### Regenerate all patterns from AWS docs

```bash
cd codegen && uv run codegen.py
make build
make test
```

### Clear scraper cache

If AWS docs changed significantly and caching causes issues:

```bash
rm -rf .cache/
```

### Add support for a new service

Usually automatic via code generation. If the service has special cases:

1. Check `codegen/index_sdk.py` - add override if SDK name differs
2. Check `codegen/index_sdk_resources.py` - add to `DEFAULT_SERVICE` or `OVERRIDE_SERVICE` if multi-SDK
3. Check `codegen/index_cfn.py` - add to `OVERRIDES` if CFN service name differs
4. Regenerate and test

## Security Considerations

- The library only parses ARN strings, never makes AWS API calls
- No credentials or sensitive data is handled
- Generated patterns come from official AWS documentation
- The scraper only reads public AWS documentation pages

## Troubleshooting

**Issue**: Pattern not matching
- Check if pattern exists in `codegen/build/arn_resources.json`
- Check `PATTERN_OVERRIDES` if AWS docs use wildcards
- Check `PATTERN_INCLUDES` if pattern is missing from docs

**Issue**: Wrong SDK client returned
- Check `index_sdk.py:OVERRIDES` for service-level mapping
- Check `index_sdk_resources.py:OVERRIDE_SERVICE` for resource-level mapping

**Issue**: Tests fail after regeneration
- AWS docs may have changed - verify changes are correct
- Some services may have been discontinued - check `EXCLUDES_*` sets

**Issue**: Import errors
- Ensure `make build` was run (copies patterns to src/)
- Check that `uv sync` was run to install dependencies
