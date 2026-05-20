# Changelog

All notable changes to `arnmatch` will be documented in this file.

This project uses CalVer in the format `YYYY.MM.MICRO`.

## [Unreleased]

## [2026.5.1] - 2026-05-20

### Highlights

This release tightens PyPI packaging so source distributions contain only the files needed to install and inspect the package.

### Improvements

- **Cleaner source distributions**: Restricted sdist contents to package source, project metadata, README, changelog, and license files, removing development-only directories such as codegen caches, tests, docs, and GitHub configuration from future PyPI artifacts.

## [2026.5.0] - 2026-05-20

### Highlights

This release refreshes the generated AWS ARN data, improves CloudFormation and Resource Groups Tagging API mappings, and expands public documentation for users and contributors.

### Improvements

- **Expanded AWS coverage**: Regenerated ARN data now covers 364 AWS services and 2,151 ARN patterns.
- **Improved resource mappings**: Added CloudFormation and Tagging API mapping rules and excludes for newly discovered AWS resources, including S3 Express, Direct Connect, AppTest, and AWS Marketplace Catalog resources.
- **Documentation refresh**: Added a public docs set with installation, quickstart, API, CLI, mappings, troubleshooting, and code generation reference pages.
- **Project discoverability**: Expanded README positioning, examples, package metadata, CI, and community files to better explain `arnmatch` as an auto-generated AWS ARN parser.

### Internal

- **Codegen reliability**: Updated codegen to handle CloudFormation overrides for services without boto3 clients and remove stale missing-mapping reports after gaps are resolved.

## [2026.3.3] - 2026-03-26

### Maintenance

- **Version update**: Released version `2026.3.3`.

## [2026.3.2] - 2026-03-26

### Improvements

- **Developer documentation**: Added code generation command references and ARN pattern troubleshooting guidance.

## [2026.3.1] - 2026-03-24

### Bug Fixes

- **EC2 ARN coverage**: Added support for optional account segments in selected EC2 image and snapshot ARN patterns.

[Unreleased]: https://github.com/andreygubarev/arnmatch/compare/2026.5.1...HEAD
[2026.5.1]: https://github.com/andreygubarev/arnmatch/releases/tag/2026.5.1
[2026.5.0]: https://github.com/andreygubarev/arnmatch/releases/tag/2026.5.0
[2026.3.3]: https://github.com/andreygubarev/arnmatch/releases/tag/2026.3.3
[2026.3.2]: https://github.com/andreygubarev/arnmatch/releases/tag/2026.3.2
[2026.3.1]: https://github.com/andreygubarev/arnmatch/releases/tag/2026.3.1
