# /// script
# requires-python = ">=3.10"
# dependencies = ["boto3"]
# ///

"""Maps ARN service names to AWS SDK (boto3) client names."""

import gzip
import json
import os
from pathlib import Path


class SDKServiceIndexer:
    """Builds mapping from ARN service names to AWS SDK client names."""

    # Phase 3: Manual overrides for services where botocore metadata doesn't match
    # Format: "arn_service" -> ["sdk_client1", "sdk_client2", ...]
    OVERRIDES = {
        # AI DevOps uses aiops client
        "aidevops": ["aiops"],
        # AppMesh preview uses appmesh client
        "appmesh-preview": ["appmesh"],
        # Service Catalog uses 'catalog' in ARNs but 'servicecatalog' client
        "catalog": ["servicecatalog"],
        # CloudWatch uses 'monitoring' as endpointPrefix but 'cloudwatch' in ARNs
        "cloudwatch": ["cloudwatch"],
        # Partner Central has multiple sub-clients
        "partnercentral": [
            "partnercentral-account",
            "partnercentral-benefits",
            "partnercentral-channel",
            "partnercentral-selling",
        ],
        # AWS Private 5G uses privatenetworks client
        "private-networks": ["privatenetworks"],
        # RDS IAM auth uses rds client
        "rds-db": ["rds"],
        # Route53 recovery services
        "route53-recovery-control": [
            "route53-recovery-cluster",
            "route53-recovery-control-config",
        ],
        # S3 variants map to s3 client
        "s3-object-lambda": ["s3"],
        "s3express": ["s3"],
    }

    # Discontinued/EOL services
    EXCLUDES_DISCONTINUED = {
        "a4b",  # Alexa for Business
        "bugbust",  # AWS BugBust
        "codestar",  # CodeStar
        "elastic-inference",  # EOL April 2024
        "elastictranscoder",  # Replaced by MediaConvert
        "honeycode",  # Honeycode
        "iotfleethub",  # EOL October 2025
        "lookoutmetrics",  # Lookout for Metrics
        "lookoutvision",  # Lookout for Vision
        "monitron",  # Monitron
        "nimble",  # Nimble Studio
        "opsworks",  # OpsWorks Stacks - EOL May 2024
        "opsworks-cm",  # OpsWorks Chef/Puppet - EOL 2024
        "qldb",  # QLDB - EOL 2025
        "robomaker",  # RoboMaker - EOL 2025
        "worklink",  # WorkLink
    }

    # Console-only services (no SDK)
    EXCLUDES_CONSOLE = {
        "appstudio",  # AWS App Studio
        "cloudshell",  # AWS CloudShell
        "consoleapp",  # Console Mobile App
        "elemental-appliances-software",  # Physical hardware
        "elemental-support-cases",  # Support tickets
        "identity-sync",  # Identity sync
        "iq",  # AWS IQ
        "iq-permission",  # AWS IQ
        "mapcredits",  # AWS MAP credits
        "one",  # Amazon One Enterprise (palm recognition)
        "payments",  # Billing payments
        "pricingplanmanager",  # Pricing plans
        "purchase-orders",  # Billing purchase orders
        "securityagent",  # AWS Security Agent (preview)
        "sqlworkbench",  # Redshift Query Editor
        "ts",  # AWS Diagnostic Tools
        "vendor-insights",  # Marketplace Vendor Insights
    }

    # Services using non-boto3 SDK (IDE plugins, CLI, OpenAI SDK, etc.)
    EXCLUDES_NOSDK = {
        "apptest",  # AWS Application Testing
        "bedrock-mantle",  # Uses OpenAI SDK
        "codewhisperer",  # IDE extension (now Q Developer)
        "freertos",  # FreeRTOS device SDK
        "qdeveloper",  # IDE plugins only
        "transform",  # CLI only
        "transform-custom",  # CLI only
    }

    # Resource type -> SDK client overrides for services with multiple SDK clients
    # Format: "arn_service" -> [(resource_type_prefix, sdk_client), ...]
    # Order matters: more specific prefixes must come before less specific ones
    SDK_RESOURCE_OVERRIDES = {
        "aws-marketplace": [
            ("ChangeSet", "marketplace-catalog"),
            ("DeploymentParameter", "marketplace-catalog"),
            ("Entity", "marketplace-catalog"),
        ],
        "connect-campaigns": [
            ("campaign", "connectcampaignsv2"),
        ],
        "connect": [
            # All management resources use connect client
            ("agent-status", "connect"),
            ("attached-file", "connect"),
            ("authentication-profile", "connect"),
            ("aws-managed-view", "connect"),
            ("contact-evaluation", "connect"),
            ("contact-flow-module", "connect"),
            ("contact-flow", "connect"),
            ("contact", "connect"),
            ("customer-managed-view-version", "connect"),
            ("customer-managed-view", "connect"),
            ("data-table", "connect"),
            ("email-address", "connect"),
            ("evaluation-form", "connect"),
            ("hierarchy-group", "connect"),
            ("hours-of-operation", "connect"),
            ("instance", "connect"),
            ("integration-association", "connect"),
            ("legacy-phone-number", "connect"),
            ("phone-number", "connect"),
            ("prompt", "connect"),
            ("qualified-aws-managed-view", "connect"),
            ("qualified-customer-managed-view", "connect"),
            ("queue", "connect"),
            ("quick-connect", "connect"),
            ("routing-profile", "connect"),
            ("rule", "connect"),
            ("security-profile", "connect"),
            ("task-template", "connect"),
            ("traffic-distribution-group", "connect"),
            ("use-case", "connect"),
            ("user", "connect"),
            ("vocabulary", "connect"),
            ("workspace", "connect"),
        ],
        "cloudhsm": [
            ("backup", "cloudhsmv2"),
            ("cluster", "cloudhsmv2"),
        ],
        "cloudsearch": [
            ("domain", "cloudsearch"),
        ],
        "cassandra": [
            ("keyspace", "keyspaces"),
            ("stream", "keyspaces"),
            ("table", "keyspaces"),
        ],
        "bedrock-agentcore": [
            # All resources use bedrock-agentcore-control for management
            ("apikeycredentialprovider", "bedrock-agentcore-control"),
            ("browser-custom", "bedrock-agentcore-control"),
            ("browser", "bedrock-agentcore-control"),
            ("code-interpreter-custom", "bedrock-agentcore-control"),
            ("code-interpreter", "bedrock-agentcore-control"),
            ("evaluator", "bedrock-agentcore-control"),
            ("gateway", "bedrock-agentcore-control"),
            ("memory", "bedrock-agentcore-control"),
            ("oauth2credentialprovider", "bedrock-agentcore-control"),
            ("online-evaluation-config", "bedrock-agentcore-control"),
            ("policy-engine", "bedrock-agentcore-control"),
            ("policy-generation", "bedrock-agentcore-control"),
            ("policy", "bedrock-agentcore-control"),
            ("runtime-endpoint", "bedrock-agentcore-control"),
            ("runtime", "bedrock-agentcore-control"),
            ("token-vault", "bedrock-agentcore-control"),
            ("workload-identity-directory", "bedrock-agentcore-control"),
            ("workload-identity", "bedrock-agentcore-control"),
        ],
        "bedrock": [
            # bedrock-agent client resources
            ("agent-alias", "bedrock-agent"),
            ("agent", "bedrock-agent"),
            ("default-prompt-router", "bedrock-agent"),
            ("flow-alias", "bedrock-agent"),
            ("flow-execution", "bedrock-agent"),
            ("flow", "bedrock-agent"),
            ("knowledge-base", "bedrock-agent"),
            ("prompt-router", "bedrock-agent"),
            ("prompt-version", "bedrock-agent"),
            ("prompt", "bedrock-agent"),
            # bedrock-agent-runtime for sessions
            ("session", "bedrock-agent-runtime"),
            # bedrock-runtime for inference
            ("async-invoke", "bedrock-runtime"),
            # bedrock client for model management
            ("application-inference-profile", "bedrock"),
            ("automated-reasoning-policy-version", "bedrock"),
            ("automated-reasoning-policy", "bedrock"),
            ("bedrock-marketplace-model-endpoint", "bedrock"),
            ("blueprint", "bedrock"),
            ("custom-model-deployment", "bedrock"),
            ("custom-model", "bedrock"),
            ("data-automation-invocation-job", "bedrock"),
            ("data-automation-profile", "bedrock"),
            ("data-automation-project", "bedrock"),
            ("evaluation-job", "bedrock"),
            ("foundation-model", "bedrock"),
            ("guardrail-profile", "bedrock"),
            ("guardrail", "bedrock"),
            ("imported-model", "bedrock"),
            ("inference-profile", "bedrock"),
            ("model-copy-job", "bedrock"),
            ("model-customization-job", "bedrock"),
            ("model-evaluation-job", "bedrock"),
            ("model-import-job", "bedrock"),
            ("model-invocation-job", "bedrock"),
            ("provisioned-model", "bedrock"),
            ("system-tool", "bedrock"),
        ],
        "appconfig": [
            # appconfigdata is only for runtime data retrieval, all resources use appconfig
            ("application", "appconfig"),
            ("configuration", "appconfig"),
            ("configurationprofile", "appconfig"),
            ("deployment", "appconfig"),
            ("deploymentstrategy", "appconfig"),
            ("environment", "appconfig"),
            ("extension", "appconfig"),
            ("extensionassociation", "appconfig"),
            ("hostedconfigurationversion", "appconfig"),
        ],
        "apigateway": [
            # v2 (HTTP/WebSocket API) resources
            ("ApiMappings", "apigatewayv2"),
            ("ApiMapping", "apigatewayv2"),
            ("Apis", "apigatewayv2"),
            ("Api", "apigatewayv2"),
            ("Cors", "apigatewayv2"),
            ("ExportedAPI", "apigatewayv2"),
            ("Integrations", "apigatewayv2"),
            ("RouteRequestParameter", "apigatewayv2"),
            ("RouteResponses", "apigatewayv2"),
            ("RouteResponse", "apigatewayv2"),
            ("RouteSettings", "apigatewayv2"),
            ("Routes", "apigatewayv2"),
            ("Route", "apigatewayv2"),
            # v1 (REST API) and shared resources
            ("AccessLogSettings", "apigateway"),
            ("Account", "apigateway"),
            ("ApiKeys", "apigateway"),
            ("ApiKey", "apigateway"),
            ("AuthorizersCache", "apigateway"),
            ("Authorizers", "apigateway"),
            ("Authorizer", "apigateway"),
            ("BasePathMappings", "apigateway"),
            ("BasePathMapping", "apigateway"),
            ("ClientCertificates", "apigateway"),
            ("ClientCertificate", "apigateway"),
            ("Deployments", "apigateway"),
            ("Deployment", "apigateway"),
            ("DocumentationParts", "apigateway"),
            ("DocumentationPart", "apigateway"),
            ("DocumentationVersions", "apigateway"),
            ("DocumentationVersion", "apigateway"),
            ("DomainNameAccessAssociations", "apigateway"),
            ("DomainNameAccessAssociation", "apigateway"),
            ("DomainNames", "apigateway"),
            ("DomainName", "apigateway"),
            ("GatewayResponses", "apigateway"),
            ("GatewayResponse", "apigateway"),
            ("IntegrationResponses", "apigateway"),
            ("IntegrationResponse", "apigateway"),
            ("Integration", "apigateway"),
            ("MethodResponse", "apigateway"),
            ("Method", "apigateway"),
            ("ModelTemplate", "apigateway"),
            ("Models", "apigateway"),
            ("Model", "apigateway"),
            ("Portal", "apigateway"),
            ("PortalProduct", "apigateway"),
            ("PrivateBasePathMappings", "apigateway"),
            ("PrivateBasePathMapping", "apigateway"),
            ("PrivateDomainName", "apigateway"),
            ("ProductPage", "apigateway"),
            ("ProductRestEndpointPage", "apigateway"),
            ("RequestValidators", "apigateway"),
            ("RequestValidator", "apigateway"),
            ("Resources", "apigateway"),
            ("Resource", "apigateway"),
            ("RestApis", "apigateway"),
            ("RestApi", "apigateway"),
            ("RoutingRule", "apigateway"),
            ("Sdk", "apigateway"),
            ("Stages", "apigateway"),
            ("Stage", "apigateway"),
            ("Tags", "apigateway"),
            ("Template", "apigateway"),
            ("UsagePlanKeys", "apigateway"),
            ("UsagePlanKey", "apigateway"),
            ("UsagePlans", "apigateway"),
            ("UsagePlan", "apigateway"),
            ("VpcLinks", "apigateway"),
            ("VpcLink", "apigateway"),
            ("apigateway", "apigateway"),
        ],
        "elasticloadbalancing": [
            ("listener-rule/app", "elbv2"),
            ("listener-rule/net", "elbv2"),
            ("listener/app", "elbv2"),
            ("listener/gwy", "elbv2"),
            ("listener/net", "elbv2"),
            ("loadbalancer/app", "elbv2"),
            ("loadbalancer/gwy", "elbv2"),
            ("loadbalancer/net", "elbv2"),
            ("targetgroup", "elbv2"),
            ("truststore", "elbv2"),
            ("loadbalancer", "elb"),  # classic - must be last
        ],
        "es": [
            ("domain", "opensearch"),
        ],
        "payment-cryptography": [
            ("alias", "payment-cryptography"),
            ("key", "payment-cryptography"),
        ],
        "route53-recovery-control": [
            # All resources use route53-recovery-control-config for management
            ("cluster", "route53-recovery-control-config"),
            ("controlpanel", "route53-recovery-control-config"),
            ("routingcontrol", "route53-recovery-control-config"),
            ("safetyrule", "route53-recovery-control-config"),
        ],
        "rds": [
            # RDS, DocumentDB, and Neptune share ARN format - default to rds
            ("auto-backup", "rds"),
            ("cev", "rds"),
            ("cluster-auto-backup", "rds"),
            ("cluster-endpoint", "rds"),
            ("cluster-pg", "rds"),
            ("cluster-snapshot", "rds"),
            ("cluster", "rds"),
            ("db", "rds"),
            ("deployment", "rds"),
            ("es", "rds"),
            ("global-cluster", "rds"),
            ("integration", "rds"),
            ("og", "rds"),
            ("pg", "rds"),
            ("proxy-endpoint", "rds"),
            ("proxy", "rds"),
            ("ri", "rds"),
            ("secgrp", "rds"),
            ("shardgrp", "rds"),
            ("snapshot-tenant-database", "rds"),
            ("snapshot", "rds"),
            ("subgrp", "rds"),
            ("target-group", "rds"),
            ("tenant-database", "rds"),
        ],
        "personalize": [
            # All resources use personalize for management
            ("algorithm", "personalize"),
            ("batchInferenceJob", "personalize"),
            ("batchSegmentJob", "personalize"),
            ("campaign", "personalize"),
            ("dataDeletionJob", "personalize"),
            ("dataInsightsJob", "personalize"),
            ("datasetExportJob", "personalize"),
            ("datasetGroup", "personalize"),
            ("datasetImportJob", "personalize"),
            ("dataset", "personalize"),
            ("eventTracker", "personalize"),
            ("featureTransformation", "personalize"),
            ("filter", "personalize"),
            ("metricAttribution", "personalize"),
            ("recipe", "personalize"),
            ("recommender", "personalize"),
            ("schema", "personalize"),
            ("solution", "personalize"),
        ],
        "partnercentral": [
            # Benefits-related
            ("BenefitAllocation", "partnercentral-benefits"),
            ("BenefitApplication", "partnercentral-benefits"),
            ("Benefit", "partnercentral-benefits"),
            # Channel-related
            ("ChannelHandshake", "partnercentral-channel"),
            # Account-related
            ("ProgramManagementAccount", "partnercentral-account"),
            # Selling-related (default)
            ("ConnectionInvitation", "partnercentral-selling"),
            ("ConnectionPreferences", "partnercentral-selling"),
            ("Connection", "partnercentral-selling"),
            ("Dashboard", "partnercentral-selling"),
            ("Engagement", "partnercentral-selling"),
            ("OpportunityFromEngagementTask", "partnercentral-selling"),
            ("Opportunity", "partnercentral-selling"),
            ("Partner", "partnercentral-selling"),
            ("Relationship", "partnercentral-selling"),
            ("ResourceSnapshot", "partnercentral-selling"),
            ("Solution", "partnercentral-selling"),
            ("engagement-by-accepting-invitation-task", "partnercentral-selling"),
            ("engagement-from-opportunity-task", "partnercentral-selling"),
            ("engagement-invitation", "partnercentral-selling"),
            ("resource-snapshot-job", "partnercentral-selling"),
        ],
        "mediastore": [
            ("container", "mediastore"),
            ("folder", "mediastore-data"),
            ("object", "mediastore-data"),
        ],
        "mgh": [
            # All resources use mgh for management
            ("AutomationRunResource", "mgh"),
            ("AutomationUnitResource", "mgh"),
            ("ConnectionResource", "mgh"),
            ("migrationTask", "mgh"),
            ("progressUpdateStream", "mgh"),
        ],
        "lex": [
            # v1 specific resources
            ("channel", "lex-models"),
            ("intent version", "lex-models"),
            ("slottype version", "lex-models"),
            # v2 specific resources
            ("test set", "lexv2-models"),
            # Shared - default to v2 (recommended)
            ("bot alias", "lexv2-models"),
            ("bot version", "lexv2-models"),
            ("bot", "lexv2-models"),
        ],
        "kinesisanalytics": [
            # v2 is the current version
            ("application", "kinesisanalyticsv2"),
        ],
        "kinesisvideo": [
            # All resources use kinesisvideo for management
            ("channel", "kinesisvideo"),
            ("stream", "kinesisvideo"),
        ],
        "ivs": [
            # ivs-realtime resources
            ("Composition", "ivs-realtime"),
            ("Encoder-Configuration", "ivs-realtime"),
            ("Ingest-Configuration", "ivs-realtime"),
            ("Public-Key", "ivs-realtime"),
            ("Stage", "ivs-realtime"),
            ("Storage-Configuration", "ivs-realtime"),
            # ivs resources
            ("Channel", "ivs"),
            ("Playback-Key-Pair", "ivs"),
            ("Playback-Restriction-Policy", "ivs"),
            ("Recording-Configuration", "ivs"),
            ("Stream-Key", "ivs"),
        ],
        "greengrass": [
            # v2 resources
            ("componentVersion", "greengrassv2"),
            ("component", "greengrassv2"),
            ("coreDevice", "greengrassv2"),
            ("deployment", "greengrassv2"),
            # v1 resources
            ("bulkDeployment", "greengrass"),
            ("certificateAuthority", "greengrass"),
            ("connectivityInfo", "greengrass"),
            ("connectorDefinitionVersion", "greengrass"),
            ("connectorDefinition", "greengrass"),
            ("coreDefinitionVersion", "greengrass"),
            ("coreDefinition", "greengrass"),
            ("deviceDefinitionVersion", "greengrass"),
            ("deviceDefinition", "greengrass"),
            ("functionDefinitionVersion", "greengrass"),
            ("functionDefinition", "greengrass"),
            ("groupVersion", "greengrass"),
            ("group", "greengrass"),
            ("loggerDefinitionVersion", "greengrass"),
            ("loggerDefinition", "greengrass"),
            ("resourceDefinitionVersion", "greengrass"),
            ("resourceDefinition", "greengrass"),
            ("subscriptionDefinitionVersion", "greengrass"),
            ("subscriptionDefinition", "greengrass"),
            ("thingRuntimeConfig", "greengrass"),
        ],
        "forecast": [
            # forecastquery is only for runtime queries, all resources use forecast
            ("algorithm", "forecast"),
            ("datasetGroup", "forecast"),
            ("datasetImportJob", "forecast"),
            ("dataset", "forecast"),
            ("endpoint", "forecast"),
            ("explainabilityExport", "forecast"),
            ("explainability", "forecast"),
            ("forecastExport", "forecast"),
            ("forecast", "forecast"),
            ("monitor", "forecast"),
            ("predictorBacktestExportJob", "forecast"),
            ("predictor", "forecast"),
            ("whatIfAnalysis", "forecast"),
            ("whatIfForecastExport", "forecast"),
            ("whatIfForecast", "forecast"),
        ],
        "execute-api": [
            ("execute-api-domain", "apigatewaymanagementapi"),
            ("execute-api-general", "apigatewaymanagementapi"),
        ],
        "dynamodb": [
            ("stream", "dynamodbstreams"),
            ("backup", "dynamodb"),
            ("export", "dynamodb"),
            ("global-table", "dynamodb"),
            ("import", "dynamodb"),
            ("index", "dynamodb"),
            ("table", "dynamodb"),
        ],
        "s3": [
            ("accessgrant", "s3control"),
            ("accessgrantslocation", "s3control"),
            ("accessgrantsinstance", "s3control"),
            ("accesspoint", "s3control"),
            ("accesspointobject", "s3control"),
            ("job", "s3control"),
            ("multiregionaccesspoint", "s3control"),
            ("multiregionaccesspointrequestarn", "s3control"),
            ("storagelensconfiguration", "s3control"),
            ("storagelensgroup", "s3control"),
            ("bucket", "s3"),
            ("object", "s3"),
        ],
        "chime": [
            ("meeting", "chime-sdk-meetings"),
            ("app-instance", "chime-sdk-identity"),
            ("app-instance-bot", "chime-sdk-identity"),
            ("app-instance-user", "chime-sdk-identity"),
            ("channel", "chime-sdk-messaging"),
            ("channel-flow", "chime-sdk-messaging"),
            ("media-insights-pipeline-configuration", "chime-sdk-media-pipelines"),
            ("media-pipeline", "chime-sdk-media-pipelines"),
            ("media-pipeline-kinesis-video-stream-pool", "chime-sdk-media-pipelines"),
            ("sip-media-application", "chime-sdk-voice"),
            ("voice-connector-group", "chime-sdk-voice"),
            ("voice-connector", "chime-sdk-voice"),
            ("voice-profile", "chime-sdk-voice"),
            ("voice-profile-domain", "chime-sdk-voice"),
        ],
    }

    def __init__(self):
        import botocore
        self.botocore_data = Path(botocore.__file__).parent / "data"

    def process(self, arn_services):
        """Build ARN service -> SDK clients mapping."""
        # Get all boto3 client metadata
        metadata = self.metadata_load()

        result = {}

        for arn_service in sorted(arn_services):
            # Phase 3: Check manual overrides first
            if arn_service in self.OVERRIDES:
                result[arn_service] = self.OVERRIDES[arn_service]
                continue

            # Known no-SDK services
            excludes = self.EXCLUDES_DISCONTINUED | self.EXCLUDES_CONSOLE | self.EXCLUDES_NOSDK
            if arn_service in excludes:
                result[arn_service] = []
                continue

            # Phase 1: Direct name match
            if arn_service in metadata:
                result[arn_service] = [arn_service]
                # Also check for additional clients via metadata
                additional = self.metadata_match(
                    arn_service, metadata, exclude={arn_service}
                )
                if additional:
                    result[arn_service].extend(sorted(additional))
                continue

            # Phase 2: Find via botocore metadata (signingName/endpointPrefix)
            clients = self.metadata_match(arn_service, metadata)
            if clients:
                result[arn_service] = sorted(clients)
                continue

            # No mapping found
            raise ValueError(f"No SDK client mapping for ARN service: {arn_service}")

        return result

    def metadata_load(self):
        """Load metadata for all boto3 clients."""
        metadata = {}

        for sdk_service in os.listdir(self.botocore_data):
            client_path = self.botocore_data / sdk_service
            if not client_path.is_dir():
                continue

            # Find latest version
            versions = sorted(
                [d for d in os.listdir(client_path) if d[0].isdigit()],
                reverse=True,
            )
            if not versions:
                continue

            # Load service metadata
            service_file = client_path / versions[0] / "service-2.json.gz"
            if not service_file.exists():
                continue

            with gzip.open(service_file) as f:
                data = json.load(f)
                metadata[sdk_service] = data.get("metadata", {})

        return metadata

    def metadata_match(self, arn_service, metadata, exclude=None):
        """Find SDK clients whose signingName or endpointPrefix matches ARN service."""
        exclude = exclude or set()
        matches = set()

        for sdk_service, meta in metadata.items():
            if sdk_service in exclude:
                continue

            # Check signingName first (more specific)
            signing_name = meta.get("signingName")
            if signing_name == arn_service:
                matches.add(sdk_service)
                continue

            # Check endpointPrefix (fallback)
            endpoint_prefix = meta.get("endpointPrefix")
            if endpoint_prefix == arn_service:
                matches.add(sdk_service)

        return matches
