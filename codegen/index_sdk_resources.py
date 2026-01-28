"""Maps ARN resource types to specific SDK clients for multi-SDK services."""


class SDKResourceIndexer:
    """SDK defaults for services with multiple SDK clients.

    DEFAULT_SERVICE: Service-level default where all resources use a single SDK.
    Format: "arn_service" -> "sdk_client"

    OVERRIDE_SERVICE: Resource-level overrides where different resources use different SDKs.
    Format: "arn_service" -> {"resource_type": "sdk_client", ...}
    """

    # Service-level default - the SDK responsible for most resources
    # (other auto-detected SDKs are typically runtime/data/query clients)
    DEFAULT_SERVICE = {
        "apigateway": "apigateway",  # v1 REST API; v2 is HTTP/WebSocket
        "appconfig": "appconfig",  # appconfigdata is runtime-only
        "aws-marketplace": "marketplace-catalog",  # entity management
        "bedrock": "bedrock",  # model management
        "bedrock-agentcore": "bedrock-agentcore-control",  # control plane
        "cassandra": "keyspaces",  # keyspacesstreams is CDC
        "chime": "chime",  # others are specialized SDKs
        "cloudhsm": "cloudhsmv2",  # v1 deprecated
        "cloudsearch": "cloudsearch",  # domain is query-only
        "connect": "connect",  # contact-lens is analytics
        "connect-campaigns": "connectcampaignsv2",  # v1 deprecated
        "dynamodb": "dynamodb",  # streams is CDC
        "elasticloadbalancing": "elbv2",  # ALB/NLB/GLB; elb is classic
        "es": "opensearch",  # Elasticsearch rebranded
        "execute-api": "apigatewaymanagementapi",  # WebSocket management
        "forecast": "forecast",  # forecastquery is runtime
        "greengrass": "greengrassv2",  # v1 deprecated
        "ivs": "ivs",  # ivs-realtime is stages
        "kinesisanalytics": "kinesisanalyticsv2",  # v1 deprecated
        "kinesisvideo": "kinesisvideo",  # others are media streaming
        "lex": "lexv2-models",  # v1 deprecated
        "mediastore": "mediastore",  # data is object operations
        "mgh": "mgh",  # config is home region only
        "partnercentral": "partnercentral-selling",  # primary module
        "payment-cryptography": "payment-cryptography",  # data is crypto ops
        "personalize": "personalize",  # events/runtime are runtime
        "rds": "rds",  # docdb/neptune are different engines
        "route53-recovery-control": "route53-recovery-control-config",  # cluster is data plane
        "s3": "s3",  # s3control is account-level
        "sagemaker": "sagemaker",  # others are runtime/edge/metrics
        "servicecatalog": "servicecatalog",  # appregistry is separate
        "ses": "sesv2",  # v1 deprecated
        "sms-voice": "pinpoint-sms-voice-v2",  # v1 deprecated
        "sso": "sso-admin",  # sso is portal access
        "timestream": "timestream-write",  # query is queries only
        "wisdom": "qconnect",  # rebranded to Q Connect
    }

    # Resource-level overrides - only non-default SDK mappings
    # Format: "arn_service" -> {"resource_type": "sdk_client", ...}
    OVERRIDE_SERVICE = {
        "apigateway": {
            # v2 (HTTP/WebSocket API) resources
            "ApiMappings": "apigatewayv2",
            "ApiMapping": "apigatewayv2",
            "Apis": "apigatewayv2",
            "Api": "apigatewayv2",
            "Cors": "apigatewayv2",
            "ExportedAPI": "apigatewayv2",
            "Integrations": "apigatewayv2",
            "RouteRequestParameter": "apigatewayv2",
            "RouteResponses": "apigatewayv2",
            "RouteResponse": "apigatewayv2",
            "RouteSettings": "apigatewayv2",
            "Routes": "apigatewayv2",
            "Route": "apigatewayv2",
        },
        "bedrock": {
            # bedrock-agent resources
            "agent-alias": "bedrock-agent",
            "agent": "bedrock-agent",
            "default-prompt-router": "bedrock-agent",
            "flow-alias": "bedrock-agent",
            "flow-execution": "bedrock-agent",
            "flow": "bedrock-agent",
            "knowledge-base": "bedrock-agent",
            "prompt-router": "bedrock-agent",
            "prompt-version": "bedrock-agent",
            "prompt": "bedrock-agent",
            # bedrock-agent-runtime
            "session": "bedrock-agent-runtime",
            # bedrock-runtime
            "async-invoke": "bedrock-runtime",
        },
        "chime": {
            "meeting": "chime-sdk-meetings",
            "app-instance": "chime-sdk-identity",
            "app-instance-bot": "chime-sdk-identity",
            "app-instance-user": "chime-sdk-identity",
            "channel": "chime-sdk-messaging",
            "channel-flow": "chime-sdk-messaging",
            "media-insights-pipeline-configuration": "chime-sdk-media-pipelines",
            "media-pipeline": "chime-sdk-media-pipelines",
            "media-pipeline-kinesis-video-stream-pool": "chime-sdk-media-pipelines",
            "sip-media-application": "chime-sdk-voice",
            "voice-connector-group": "chime-sdk-voice",
            "voice-connector": "chime-sdk-voice",
            "voice-profile": "chime-sdk-voice",
            "voice-profile-domain": "chime-sdk-voice",
        },
        "dynamodb": {
            "stream": "dynamodbstreams",
        },
        "elasticloadbalancing": {
            "loadbalancer": "elb",  # classic
        },
        "greengrass": {
            # v1 resources (v2 is default)
            "bulkDeployment": "greengrass",
            "certificateAuthority": "greengrass",
            "connectivityInfo": "greengrass",
            "connectorDefinitionVersion": "greengrass",
            "connectorDefinition": "greengrass",
            "coreDefinitionVersion": "greengrass",
            "coreDefinition": "greengrass",
            "deviceDefinitionVersion": "greengrass",
            "deviceDefinition": "greengrass",
            "functionDefinitionVersion": "greengrass",
            "functionDefinition": "greengrass",
            "groupVersion": "greengrass",
            "group": "greengrass",
            "loggerDefinitionVersion": "greengrass",
            "loggerDefinition": "greengrass",
            "resourceDefinitionVersion": "greengrass",
            "resourceDefinition": "greengrass",
            "subscriptionDefinitionVersion": "greengrass",
            "subscriptionDefinition": "greengrass",
            "thingRuntimeConfig": "greengrass",
        },
        "ivs": {
            # ivs-realtime resources
            "Composition": "ivs-realtime",
            "Encoder-Configuration": "ivs-realtime",
            "Ingest-Configuration": "ivs-realtime",
            "Public-Key": "ivs-realtime",
            "Stage": "ivs-realtime",
            "Storage-Configuration": "ivs-realtime",
        },
        "lex": {
            # v1 resources
            "channel": "lex-models",
            "intent version": "lex-models",
            "slottype version": "lex-models",
        },
        "mediastore": {
            "folder": "mediastore-data",
            "object": "mediastore-data",
        },
        "partnercentral": {
            "BenefitAllocation": "partnercentral-benefits",
            "BenefitApplication": "partnercentral-benefits",
            "Benefit": "partnercentral-benefits",
            "ChannelHandshake": "partnercentral-channel",
            "ProgramManagementAccount": "partnercentral-account",
        },
        "s3": {
            "accessgrant": "s3control",
            "accessgrantslocation": "s3control",
            "accessgrantsinstance": "s3control",
            "accesspoint": "s3control",
            "accesspointobject": "s3control",
            "job": "s3control",
            "multiregionaccesspoint": "s3control",
            "multiregionaccesspointrequestarn": "s3control",
            "storagelensconfiguration": "s3control",
            "storagelensgroup": "s3control",
        },
        "servicecatalog": {
            "Application": "servicecatalog-appregistry",
            "AttributeGroup": "servicecatalog-appregistry",
        },
    }

    def process(self, sdk_mapping):
        """Validate all multi-SDK services have a DEFAULT_SERVICE entry."""
        missing = {}
        for arn_service, sdks in sdk_mapping.items():
            if len(sdks) > 1 and arn_service not in self.DEFAULT_SERVICE:
                missing[arn_service] = sdks
        if missing:
            raise RuntimeError(f"Missing DEFAULT_SERVICE for multi-SDK services: {missing}")
