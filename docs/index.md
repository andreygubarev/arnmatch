# arnmatch documentation

`arnmatch` is a zero-dependency Python library and CLI for parsing AWS ARNs (Amazon Resource Names) into structured resource data. It recognizes 350+ AWS services and 2,100+ resource patterns, and maps each ARN to CloudFormation resource types, Resource Groups Tagging API types, and boto3 SDK service names.

## Who this is for

- Developers building AWS inventory, CSPM, and asset management tools.
- Engineers normalizing ARNs from multiple AWS APIs.
- Operators who need to map discovered resources to CloudFormation or boto3 clients.

## Getting started

New to arnmatch? Start here:

- [Installation](getting-started/installation.md): Install the package with pip or uv.
- [Quickstart](getting-started/quickstart.md): Parse your first ARN in under five minutes.

## Concepts

- [How it works](concepts/how-it-works.md): Learn how arnmatch generates its parser data from AWS documentation and why it stays current.

## Reference

- [Python API](reference/api.md): Complete reference for `arnmatch()`, the `ARN` dataclass, and error handling.
- [CLI](reference/cli.md): Command-line usage and output format.
- [Mappings](reference/mappings.md): CloudFormation, Tagging API, and boto3 SDK mappings explained.

## Troubleshooting

- [Common errors](troubleshooting/common-errors.md): Fix parsing errors, unknown services, and missing mappings.

## Support

- Report issues on [GitHub](https://github.com/andreygubarev/arnmatch/issues).
- View releases on the [GitHub changelog](https://github.com/andreygubarev/arnmatch/releases).
