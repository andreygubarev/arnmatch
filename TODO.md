# TODO

## Resource Type Name Normalization

Normalize resource type names to kebab-case for consistency.

### Problem

AWS Service Authorization Reference uses inconsistent naming for resource types:
- `bucket` (lowercase)
- `Analyzer` (PascalCase)
- `backupVault` (camelCase)
- `certificate-authority` (kebab-case)

Current stats from our YAML export:
- Total: 2063 resource types
- All lowercase: 1522
- Has uppercase: 541 (153 camelCase, 388 PascalCase)
- With hyphens: 582

Even within the same service we have mixed naming (e.g., backup: `framework` vs `backupVault`).

### Why We Can Normalize

Resource type names are metadata we assign — they don't appear literally in ARN patterns. ARNs use placeholders like `${BucketName}` not the resource type string. So we're free to define our own convention.

AWS themselves normalized to lowercase in their cfn_to_arn_map.json (used by aws-cloudformation-iam-policy-validator). They have 437 resource types, all lowercase/kebab-case.

### Proposed Convention

**kebab-case** for all resource types:
- `backup-vault` (not `backupVault`)
- `code-signing-config` (not `CodeSigningConfig`)
- `analyzer` (not `Analyzer`)
- `certificate-authority` (already correct)

### Implementation

- [ ] Add `normalize_resource_type()` function to convert any format to kebab-case
- [ ] Apply normalization in YAML export
- [ ] Keep original name from docs in a separate field if needed for reference

---

## Migration-based Pattern Management

Replace codegen-as-source-of-truth with artifact-as-source-of-truth using a migration approach similar to SQL migrations.

### Motivation

- AWS docs are unreliable (deprecations, format changes, repo removals)
- Codegen is fragile and depends on external sources
- ARN formats are immutable contracts — AWS can't break backwards compatibility
- Captured patterns are durable knowledge that won't become wrong, only incomplete
- Direct fixes are simpler than "how do I make codegen produce X"

### Proposed Structure

```
patterns/
  migrations/
    0001_initial.yaml           # Full codegen dump (baseline)
    0002_fix_s3_object_lambda.yaml
    0003_add_bedrock_agents.yaml
    0004_codegen_discovery_2026_02.yaml  # Cherry-picked from codegen
    ...

  compiled/
    arn_patterns.json           # Merged result (intermediate)

src/arnmatch/
  arn_patterns.py               # Generated from compiled JSON
```

### Migration Format

```yaml
# 0002_fix_s3_object_lambda.yaml
meta:
  date: 2026-01-30
  description: "Fix S3 Object Lambda pattern - was using wildcard instead of capture"
  source: manual  # or: codegen-discovery, user-report

changes:
  s3-object-lambda:
    modify:
      - pattern: "arn:${Partition}:s3-object-lambda:${Region}:${Account}:accesspoint/${AccessPointName}"
        # replaces existing pattern that had wildcard

  bedrock:
    add:
      - pattern: "arn:${Partition}:bedrock:${Region}:${Account}:agent/${AgentId}"
        resource_type: "agent"

  some-deprecated-service:
    remove:
      - pattern: "arn:..."  # if ever needed
```

### Workflow / Makefile Targets

```bash
# Apply all migrations → compiled JSON → arn_patterns.py
make compile

# Discover new patterns from AWS docs (doesn't modify anything, just shows diff)
make discover

# Create new migration from discovery or manual
make migration name=add_new_stuff
```

### Implementation Tasks

- [x] Update codegen to output YAML instead of (or in addition to) Python
- [ ] Create `0001_initial.yaml` from current codegen output
- [ ] Write migration compiler (merge migrations → JSON → arn_patterns.py)
- [ ] Add `make compile` target
- [ ] Modify `make discover` to diff against current compiled state
- [ ] Add `make migration` helper to scaffold new migration files
- [ ] Update CLAUDE.md with new workflow
- [ ] Keep codegen in `codegen/` for discovery purposes
