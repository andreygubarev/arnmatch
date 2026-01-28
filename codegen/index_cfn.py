# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "boto3"]
# ///

"""Maps ARN service names to CloudFormation resource types."""

import gzip
import json
import os
from pathlib import Path

import botocore
import requests

CLOUDFORMATION_SPEC = "https://d1uauaxba7bl26.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json"


class CFNServiceIndexer:
    """Builds mapping from ARN service names to CloudFormation resource types."""

    CACHE_FILE = Path(__file__).parent / "cache" / "CloudFormationResourceSpecification.json"
    CACHE_SERVICES_FILE = Path(__file__).parent / "cache" / "CloudFormationServices.json"

    # Discontinued/EOL services (lowercase for comparison)
    EXCLUDES_DISCONTINUED = {
        "codestar",
        "lookoutvision",
        "opsworks",
        "qldb",
        "robomaker",
    }

    # CFN services with no SDK (excluded from mapping)
    EXCLUDES_NO_SDK = {
        "ask",  # Alexa Skills Kit - uses SMAPI
    }

    # CFN services with no ARN patterns (excluded from mapping)
    EXCLUDES_NO_ARN = {
        "applicationinsights",
        "apptest",
        "arczonalshift",
        "autoscalingplans",
        "devopsguru",
        "iotthingsgraph",
        "lakeformation",
        "rtbfabric",
        "ssmguiconnect",
        "supportapp",
    }

    # Manual mapping: CFN service -> SDK service (for unmatched)
    OVERRIDES = {
        "AmazonMQ": "mq",
        "Macie": "macie2",
        "AppTest": "apptest",
        "CertificateManager": "acm",
        "Cognito": "cognito-idp",
        "DevOpsAgent": "aiops",
        "Elasticsearch": "es",
        "EventSchemas": "schemas",
        "HealthImaging": "medical-imaging",
        "InspectorV2": "inspector2",
        "IoTCoreDeviceAdvisor": "iotdeviceadvisor",
        "KinesisFirehose": "firehose",
        "MSK": "kafka",
        "OpenSearchService": "opensearch",
        "RefactorSpaces": "migration-hub-refactor-spaces",
        "Route53RecoveryControl": "route53-recovery-control-config",
        "S3Express": "s3",
        "S3ObjectLambda": "s3",
        "SMSVOICE": "pinpoint-sms-voice",
        "SystemsManagerSAP": "ssm-sap",
    }

    def download(self) -> dict:
        """Download and cache CloudFormation Resource Specification."""
        if self.CACHE_FILE.exists():
            return json.loads(self.CACHE_FILE.read_text())

        resp = requests.get(CLOUDFORMATION_SPEC, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.CACHE_FILE.write_text(json.dumps(data))
        return data

    def metadata_load(self) -> dict[str, str]:
        """Build lookup: normalized name -> SDK client."""
        botocore_data = Path(botocore.__file__).parent / "data"
        metadata = {}

        for sdk_service in os.listdir(botocore_data):
            client_path = botocore_data / sdk_service
            if not client_path.is_dir():
                continue

            versions = sorted([d for d in os.listdir(client_path) if d[0].isdigit()], reverse=True)
            if not versions:
                continue

            service_file = client_path / versions[0] / "service-2.json.gz"
            if not service_file.exists():
                continue

            with gzip.open(service_file) as f:
                meta = json.load(f).get("metadata", {})

            for name in [sdk_service, meta.get("signingName"), meta.get("endpointPrefix"), meta.get("serviceId")]:
                if name:
                    metadata[name.lower().replace(" ", "")] = sdk_service

        return metadata

    def process(self, sdk_mapping: dict) -> dict[str, list[str]]:
        """Build ARN service -> CFN services mapping."""
        spec = self.download()
        cfn_services = {rt.split("::")[1] for rt in spec.get("ResourceTypes", {}).keys()}
        cfn_services_excludes = self.EXCLUDES_DISCONTINUED | self.EXCLUDES_NO_SDK | self.EXCLUDES_NO_ARN
        cfn_services = {s for s in cfn_services if s.lower() not in cfn_services_excludes}

        # Build CFN -> SDK service mapping
        metadata = self.metadata_load()
        cfn_to_sdk = {}
        for cfn in cfn_services:
            if cfn in self.OVERRIDES:
                cfn_to_sdk[cfn] = self.OVERRIDES[cfn]
            elif cfn.lower() in metadata:
                cfn_to_sdk[cfn] = metadata[cfn.lower()]

        cfn_services_missing = set(cfn_services) - set(cfn_to_sdk.keys())
        if cfn_services_missing:
            raise ValueError(f"CFN services not matched to SDK: {sorted(cfn_services_missing)}")

        # Reverse sdk_mapping: SDK service -> ARN service
        sdk_to_arn = {}
        for arn_service, clients in sdk_mapping.items():
            for client in clients:
                sdk_to_arn[client] = arn_service

        # Build final: ARN service -> CFN services (list)
        result = {}
        unmapped = []
        for cfn_service, sdk_service in cfn_to_sdk.items():
            if sdk_service in sdk_to_arn:
                arn_service = sdk_to_arn[sdk_service]
                if arn_service not in result:
                    result[arn_service] = []
                result[arn_service].append(cfn_service)
            else:
                unmapped.append(f"{cfn_service} -> {sdk_service}")

        if unmapped:
            raise ValueError(f"CFN services not mapped to ARN: {sorted(unmapped)}")

        # Sort keys and values
        result = {k: sorted(v) for k, v in sorted(result.items())}
        self.CACHE_SERVICES_FILE.write_text(json.dumps(result, indent=2))
        return result


if __name__ == "__main__":
    CFNServiceIndexer().process({})
