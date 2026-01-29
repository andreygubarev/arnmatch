# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "boto3"]
# ///

"""Maps ARN service names to CloudFormation resource types."""

import json
from pathlib import Path

import requests

from utils import botocore_metadata

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

    @property
    def excludes(self):
        return self.EXCLUDES_DISCONTINUED | self.EXCLUDES_NO_SDK | self.EXCLUDES_NO_ARN


    def download(self):
        """Download and cache CloudFormation Resource Specification."""
        if self.CACHE_FILE.exists():
            return json.loads(self.CACHE_FILE.read_text())

        resp = requests.get(CLOUDFORMATION_SPEC, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.CACHE_FILE.write_text(json.dumps(data))
        return data

    def metadata_load(self):
        """Build lookup: normalized name -> SDK client."""
        lookup = {}
        for sdk_service, meta in botocore_metadata().items():
            for name in [sdk_service, meta.get("signingName"), meta.get("endpointPrefix"), meta.get("serviceId")]:
                if name:
                    lookup[name.lower().replace(" ", "")] = sdk_service
        return lookup

    def process(self, sdk_mapping):
        """Build ARN service -> CFN services mapping."""
        cfn_services = {rt.split("::")[1] for rt in self.download().get("ResourceTypes", {}).keys()}
        cfn_services = {s for s in cfn_services if s.lower() not in self.excludes}

        metadata = self.metadata_load()
        sdk_services = {}
        for cfn_service in cfn_services:
            metadata_service = cfn_service.lower().replace("-", "").replace(" ", "")

            sdk_service = None
            if cfn_service in self.OVERRIDES:
                sdk_service = self.OVERRIDES[cfn_service]
            elif metadata_service in metadata:
                sdk_service = metadata[metadata_service]

            if not sdk_service:
                raise ValueError(f"No SDK client mapping for CFN service: {cfn_service}")

            if cfn_service in sdk_services:
                raise ValueError(f"Duplicate SDK client mapping for CFN service: {cfn_service}")
            sdk_services[cfn_service] = sdk_service

        sdk_services = dict(sorted(sdk_services.items()))
        self.CACHE_SERVICES_FILE.write_text(json.dumps(sdk_services, indent=2))
        return


if __name__ == "__main__":
    CFNServiceIndexer().process({})
