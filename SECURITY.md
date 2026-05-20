# Security Policy

## Supported versions

Security fixes are provided for the latest released version of `arnmatch`.
Please upgrade to the newest PyPI release before reporting issues that may
already be fixed.

## Reporting a vulnerability

If you believe you have found a security vulnerability, please do not publish it
publicly before it has been reviewed.

Email the maintainer at `andrey@andreygubarev.com` with:

- A description of the issue
- Steps to reproduce, if applicable
- The affected version
- Any suggested remediation

For non-sensitive bugs such as missing ARN patterns or incorrect mappings, open a
normal GitHub issue instead.

## Runtime security model

`arnmatch` performs local ARN parsing only:

- No runtime network calls
- No runtime package dependencies for parsing
- No AWS credentials required for parsing
- Generated regex patterns are compiled from repository-controlled source data

The optional `ARN.client()` helper imports `boto3` from the caller's environment
and uses the caller's configured AWS credentials/session.
