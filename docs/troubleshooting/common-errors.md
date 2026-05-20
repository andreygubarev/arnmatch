# Common errors

This page lists common issues when parsing ARNs and how to resolve them.

## "Invalid ARN format"

**Error:**

```text
Error: Invalid ARN format: <arn>
```

**Cause:** The input does not follow the ARN structure `arn:partition:service:region:account:resource`.

**Fix:**
- Check for typos in the ARN string.
- Ensure the ARN starts with `arn:`.
- Verify that there are exactly five colons separating the six components.

## "Unknown service"

**Error:**

```text
Error: Unknown service: <service>
```

**Cause:** The service name in the ARN is not in the generated pattern set.

**Fix:**
- Check that the service name is correct (for example, `lambda` not `lamba`).
- If the service is new or rare, the pattern data may need to be regenerated. Update to the latest arnmatch version or regenerate patterns with `cd codegen && make clean && make`.

## "No pattern matched ARN"

**Error:**

```text
Error: No pattern matched ARN: <arn>
```

**Cause:** The service is known, but the specific resource format does not match any generated pattern.

**Fix:**
- Verify the ARN against AWS documentation for the service.
- Some services use non-standard separators (`:` vs `/`). AWS documentation inconsistencies can cause mismatches.
- If you believe the pattern is correct but missing, open an issue with the ARN and expected resource type.

## Missing CloudFormation or Tagging API mapping

**Symptom:** `cloudformation_resource` or `tagging_resource` is `None` for a valid ARN.

**Cause:** Not all AWS resource types have corresponding CloudFormation or Tagging API types. Common reasons include:
- The resource is an async operation or task (for example, a training job or export task).
- The resource is a sub-resource configured as a property on a parent resource.
- CloudFormation or Tagging API coverage is not yet available for the service.

**Fix:**
- No action is required for the parser; this is expected behavior.
- If you need a specific mapping, you can add an override in `codegen/rules/cfn_overrides.json` or `codegen/rules/tag_overrides.json` and regenerate patterns.

## "No SDK service mapping for service"

**Error:**

```text
ValueError: No SDK service mapping for service '<service>'
```

**Cause:** `ARN.client()` was called for a service that has no boto3 client mapping.

**Fix:**
- Check `resource.aws_sdk_services` to see if any clients are mapped.
- If the service is new or niche, it may not yet have a boto3 client name in the generated data.
- You can still use the parsed ARN fields directly with a boto3 client you create manually.

## Slow import or large memory use

**Symptom:** Importing arnmatch takes longer than expected.

**Cause:** The generated `arn_patterns.py` module compiles thousands of regex patterns at import time.

**Fix:**
- This is a one-time cost per process. In long-running applications the impact is negligible.
- For short-lived processes (such as AWS Lambda cold starts), consider caching the import or using a keep-warm strategy.
