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

    # Manual mapping: CFN service -> SDK client (for unmatched)
    OVERRIDES = {
        "ASK": "alexaforbusiness",
        "AmazonMQ": "mq",
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

    def load_boto_metadata(self) -> dict[str, str]:
        """Build lookup: normalized name -> SDK client."""
        botocore_data = Path(botocore.__file__).parent / "data"
        lookup = {}

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
                    lookup[name.lower().replace(" ", "")] = sdk_service

        return lookup

    def process(self, sdk_mapping: dict) -> dict[str, str]:
        """Build ARN service -> CFN service mapping."""
        spec = self.download()
        cfn_services = {rt.split("::")[1] for rt in spec.get("ResourceTypes", {}).keys()}
        cfn_services = {s for s in cfn_services if s.lower() not in self.EXCLUDES_DISCONTINUED}

        # Build CFN -> SDK client mapping
        boto_lookup = self.load_boto_metadata()
        cfn_to_sdk = {}
        for cfn in cfn_services:
            if cfn in self.OVERRIDES:
                cfn_to_sdk[cfn] = self.OVERRIDES[cfn]
            elif cfn.lower() in boto_lookup:
                cfn_to_sdk[cfn] = boto_lookup[cfn.lower()]

        # Reverse sdk_mapping: SDK client -> ARN service
        sdk_to_arn = {}
        for arn_svc, clients in sdk_mapping.items():
            for client in clients:
                sdk_to_arn[client] = arn_svc

        # Build final: ARN service -> CFN service
        result = {}
        for cfn, sdk_client in cfn_to_sdk.items():
            if sdk_client in sdk_to_arn:
                arn_svc = sdk_to_arn[sdk_client]
                result[arn_svc] = cfn

        self.CACHE_SERVICES_FILE.write_text(json.dumps(result, indent=2))
        return result


if __name__ == "__main__":
    CFNServiceIndexer().process({})
