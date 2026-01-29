# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "boto3"]
# ///

"""Maps ARN service names to CloudFormation resource types."""

import json
from pathlib import Path
import collections

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

    @property
    def cloudformation_services(self) -> list[str]:
        """Get all CloudFormation services from the specification."""
        data = self.download()
        services = {rt.split("::")[1] for rt in data["ResourceTypes"].keys()}
        services = {s for s in services if s.lower() not in self.excludes}
        return list(sorted(services))

    def save(self, services):
        services = dict(sorted(services.items()))
        self.CACHE_SERVICES_FILE.write_text(json.dumps(services, indent=2))

    def sdk_to_names(self):
        metadata = botocore_metadata()
        n = lambda n: n.lower().replace("-", "").replace(" ", "")

        sdk_to_names = collections.defaultdict(set)
        for sdk, names in metadata.items():
            sdk_to_names[sdk].add(n(sdk))
            sdk_to_names[sdk].add(n(names["endpointPrefix"]))
            sdk_to_names[sdk].add(n(names["serviceId"]))
            sdk_to_names[sdk].add(n(names["serviceFullName"]))
            if names.get("signingName"):
                sdk_to_names[sdk].add(n(names["signingName"]))

        return sdk_to_names


    def process(self, arn_to_sdk):
        """Build ARN service -> CFN services mapping."""
        cfns: list[str] = self.cloudformation_services
        sdk_to_names = self.sdk_to_names()

        cfn_to_sdk = {}
        n = lambda n: n.lower().replace("-", "").replace(" ", "")
        for cfn in cfns:
            ncfn = n(cfn)
            for sdk, names in sdk_to_names.items():
                if ncfn in names:
                    cfn_to_sdk[cfn] = sdk
                    break
            else:
                if cfn in self.OVERRIDES:
                    cfn_to_sdk[cfn] = self.OVERRIDES[cfn]
                    continue
                raise ValueError(f"No SDK mapping for CFN service: {cfn}")


        # self.save(cfns)
        return


if __name__ == "__main__":
    CFNServiceIndexer().process({})
