# AGENTS.md - AI Coding Agent Guide for arnmatch

This file provides essential context for AI coding agents working with the arnmatch codebase.

## Project Overview

**arnmatch** is a Python library that parses AWS ARNs (Amazon Resource Names) into structured data. It supports 300+ AWS services and 2000+ resource types. The library has zero runtime dependencies.

Key capabilities:
- Parse ARNs into structured components (service, region, account, resource type, resource ID)
- Map ARNs to CloudFormation resource types (e.g., `AWS::Lambda::Function`)
- Map ARNs to Resource Groups Tagging API types
- Provide boto3 SDK service mappings for programmatic access

## Technology Stack

- **Language**: Python 3.10+
- **Build System**: Hatchling (PEP 517)
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (required for development)
- **Linter**: Ruff
- **Testing**: pytest
- **Versioning**: CalVer (`YYYY.MM.MICRO`, e.g., `2026.3.1`)

## Project Structure

```
arnmatch/
├── src/arnmatch/              # Core library (zero runtime deps)
│   ├── __init__.py            # Main module: arnmatch() function, ARN dataclass
│   └── arn_patterns.py        # Generated file with compiled regex patterns
├── codegen/                   # Code generation pipeline (has external deps)
│   ├── scraper.py             # Scrapes AWS Service Authorization Reference
│   ├── codegen.py             # Main orchestrator: generates arn_patterns.yaml
│   ├── codegen_python.py      # Converts YAML to Python module
│   ├── index_*.py             # Indexers for ARN/SDK/CFN/Tagging mappings
│   ├── rules/                 # JSON override/exclude rules
│   ├── build/                 # Generated artifacts (YAML, Python)
│   └── cache/                 # Cached intermediate data
├── tests/
│   ├── test_arnmatch.py       # Unit tests for core library
│   └── integration/           # Integration tests (requires AWS credentials)
├── pyproject.toml             # Project config, dependencies, tool settings
├── Makefile                   # Build automation
└── README.md                  # User documentation
```

## Build Commands

All commands use `uv` for dependency management:

```bash
make lint              # Run ruff linter
make test              # Run pytest tests
make check             # Run lint + test
make generate          # Regenerate patterns from AWS docs (runs codegen pipeline)
make build             # Copy generated patterns to src + build wheel/tarball
make publish           # Build and upload to PyPI
make clean             # Remove build artifacts
make test-integration  # Run integration test (requires AWS credentials)
```

Test locally:
```bash
uv run arnmatch <arn>   # Test CLI locally
```

## Code Architecture

### Core Library (`src/arnmatch/`)

**`arnmatch(arn: str) -> ARN`** - Main entry point. Splits ARN, looks up patterns by service, returns structured data.

**`ARN` dataclass** - Contains:
- `aws_partition`, `aws_service`, `aws_region`, `aws_account` - Standard ARN components
- `resource_type` - Canonical type name
- `resource_types` - All known aliases for the type
- `attributes` - Captured groups from regex match
- `aws_sdk_service` - Primary boto3 client name
- `cloudformation_resource` - CFN type string
- `tagging_resource` - Tagging API type string

**Properties:**
- `resource_id` - Heuristic extraction (prefers *Id, then *Name, then last attribute)
- `resource_name` - Heuristic extraction (prefers *Name, falls back to resource_id)
- `aws_sdk_services` - List of all boto3 clients for this service

**`client(session=None)` method** - Returns boto3 client for the service.

### Code Generation Pipeline (`codegen/`)

Data flow:
```
AWS docs → scraper.py → raw resources → codegen.py → arn_patterns.yaml → codegen_python.py → build/arn_patterns.py → (copied by make build) → src/arnmatch/arn_patterns.py
```

**Key Components:**
- `scraper.py` - Uses requests + BeautifulSoup to scrape AWS documentation, cached with joblib
- `index_arn.py` - Processes raw resources: applies overrides, filters, deduplicates
- `index_sdk.py` - Maps ARN service names to boto3 client names using botocore metadata
- `index_cfn.py` / `index_cfn_resources.py` - CloudFormation service/resource mappings
- `index_tag.py` / `index_tag_resources.py` - Tagging API mappings
- `transform.py` - Normalizes resource type names (kebab-case)

**Rules System (`codegen/rules/`):**
All indexers use JSON rule files for overrides and exclusions:
- `*_overrides.json` - Replace incorrect/missing patterns
- `*_excludes.json` - Remove problematic entries
- `*_includes.json` - Add patterns not in AWS docs

## Development Conventions

### Code Style

- **Ruff** handles all linting and formatting
- No strict line length limits
- Type hints encouraged but not strictly enforced
- Docstrings use Google style

### Pattern Matching Logic

1. **Service Index**: O(1) lookup by service name before pattern matching
2. **Pattern Ordering**: Patterns sorted by specificity (more literal segments first) for correct matching
3. **Multi-SDK Services**: Services like `elasticloadbalancing` map to multiple boto3 clients (`elb`, `elbv2`)

### Resource Type Naming

- Canonical names are transformed to kebab-case (e.g., `loadbalancer/app/` → `loadbalancer-app`)
- Type aliases preserve original AWS doc names
- Override rules in `codegen/rules/` fix edge cases

## Testing Strategy

### Unit Tests (`tests/test_arnmatch.py`)

- Tests for major AWS services (EC2, Lambda, S3, IAM, RDS, etc.)
- Validates resource type parsing, SDK mapping, CFN mapping, tagging mapping
- Tests `client()` method with mocked boto3

### Integration Tests (`tests/integration/`)

- `test_resource_explorer.py` - Fetches real ARNs from AWS Resource Explorer 2 and validates parsing
- **Requires**: AWS credentials + Resource Explorer enabled with aggregator index
- Not run in CI; manual execution only

## Build and Release Process

1. **Development**: Edit code, run `make check` to verify
2. **Regenerate Patterns**: Run `make generate` if AWS docs changed
3. **Build**: `make build` copies `codegen/build/arn_patterns.py` to `src/arnmatch/arn_patterns.py` and creates wheel
4. **Version**: Update `__version__` in `src/arnmatch/__init__.py` (CalVer format)
5. **Publish**: `make publish` uploads to PyPI

**Important**: Always run `make build` before publishing to ensure patterns are current.

## Cache Management

- `codegen/.cache/` - joblib cache for scraped AWS docs
- `codegen/cache/` - JSON cache for SDK mappings and intermediate data
- Delete `.cache/` if AWS docs change significantly to force re-scrape

## Common Tasks

### Adding Support for New Resource Types

If AWS adds new resource types that aren't being picked up:

1. Check if they're in the AWS Service Authorization Reference
2. If docs are correct but patterns are wrong: add to `codegen/rules/arn_overrides.json`
3. If resource type needs exclusion: add to `codegen/rules/arn_excludes.json`
4. If completely missing from docs: add to `codegen/rules/arn_includes.json`
5. Run `make generate` and `make check`

### Fixing SDK Service Mapping

If a service maps to wrong boto3 client:

1. Check `codegen/rules/sdk_overrides.json` for existing overrides
2. Add override if needed: `"arn_service": ["boto3_client_name"]`
3. For multi-SDK services, also update `codegen/rules/sdk_resources_overrides.json` or `sdk_resources_defaults.json`

### Fixing CloudFormation Mapping

If CFN type is incorrect or missing:

1. Check `codegen/rules/cfn_overrides.json` or `cfn_resources_overrides.json`
2. Add override: `"arn_service": {"resource_type": "AWS::Service::ResourceType"}`

## Security Considerations

- **Zero runtime dependencies**: No supply chain risk for library users
- Codegen dependencies (requests, boto3) are dev-only
- Regex patterns are compiled at import time from generated code
- No network calls during runtime parsing
- AWS credentials only needed for integration tests, not unit tests
