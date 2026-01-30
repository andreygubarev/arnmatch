# TODO

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

- [ ] Update codegen to output YAML instead of (or in addition to) Python
- [ ] Create `0001_initial.yaml` from current codegen output
- [ ] Write migration compiler (merge migrations → JSON → arn_patterns.py)
- [ ] Add `make compile` target
- [ ] Modify `make discover` to diff against current compiled state
- [ ] Add `make migration` helper to scaffold new migration files
- [ ] Update CLAUDE.md with new workflow
- [ ] Keep codegen in `codegen/` for discovery purposes
