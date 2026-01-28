"""Maps ARN resource types to specific SDK clients for multi-SDK services."""


class SDKResourceIndexer:
    """SDK defaults for services with multiple SDK clients.

    DEFAULT_SERVICE: Service-level default where all resources use a single SDK.
    Format: "arn_service" -> "sdk_client"

    OVERRIDES_RESOURCES: Resource-level overrides where different resources use different SDKs.
    Format: "arn_service" -> [(resource_type_prefix, sdk_client), ...]
    Order matters: more specific prefixes must come before less specific ones.
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

    # Resource-level overrides - different resources use different SDKs
    OVERRIDES_RESOURCES = {
        # "apigateway": [
        #     # v2 (HTTP/WebSocket API) resources
        #     ("ApiMappings", "apigatewayv2"),
        #     ("ApiMapping", "apigatewayv2"),
        #     ("Apis", "apigatewayv2"),
        #     ("Api", "apigatewayv2"),
        #     ("Cors", "apigatewayv2"),
        #     ("ExportedAPI", "apigatewayv2"),
        #     ("Integrations", "apigatewayv2"),
        #     ("RouteRequestParameter", "apigatewayv2"),
        #     ("RouteResponses", "apigatewayv2"),
        #     ("RouteResponse", "apigatewayv2"),
        #     ("RouteSettings", "apigatewayv2"),
        #     ("Routes", "apigatewayv2"),
        #     ("Route", "apigatewayv2"),
        #     # v1 (REST API) and shared resources
        #     ("AccessLogSettings", "apigateway"),
        #     ("Account", "apigateway"),
        #     ("ApiKeys", "apigateway"),
        #     ("ApiKey", "apigateway"),
        #     ("AuthorizersCache", "apigateway"),
        #     ("Authorizers", "apigateway"),
        #     ("Authorizer", "apigateway"),
        #     ("BasePathMappings", "apigateway"),
        #     ("BasePathMapping", "apigateway"),
        #     ("ClientCertificates", "apigateway"),
        #     ("ClientCertificate", "apigateway"),
        #     ("Deployments", "apigateway"),
        #     ("Deployment", "apigateway"),
        #     ("DocumentationParts", "apigateway"),
        #     ("DocumentationPart", "apigateway"),
        #     ("DocumentationVersions", "apigateway"),
        #     ("DocumentationVersion", "apigateway"),
        #     ("DomainNameAccessAssociations", "apigateway"),
        #     ("DomainNameAccessAssociation", "apigateway"),
        #     ("DomainNames", "apigateway"),
        #     ("DomainName", "apigateway"),
        #     ("GatewayResponses", "apigateway"),
        #     ("GatewayResponse", "apigateway"),
        #     ("IntegrationResponses", "apigateway"),
        #     ("IntegrationResponse", "apigateway"),
        #     ("Integration", "apigateway"),
        #     ("MethodResponse", "apigateway"),
        #     ("Method", "apigateway"),
        #     ("ModelTemplate", "apigateway"),
        #     ("Models", "apigateway"),
        #     ("Model", "apigateway"),
        #     ("Portal", "apigateway"),
        #     ("PortalProduct", "apigateway"),
        #     ("PrivateBasePathMappings", "apigateway"),
        #     ("PrivateBasePathMapping", "apigateway"),
        #     ("PrivateDomainName", "apigateway"),
        #     ("ProductPage", "apigateway"),
        #     ("ProductRestEndpointPage", "apigateway"),
        #     ("RequestValidators", "apigateway"),
        #     ("RequestValidator", "apigateway"),
        #     ("Resources", "apigateway"),
        #     ("Resource", "apigateway"),
        #     ("RestApis", "apigateway"),
        #     ("RestApi", "apigateway"),
        #     ("RoutingRule", "apigateway"),
        #     ("Sdk", "apigateway"),
        #     ("Stages", "apigateway"),
        #     ("Stage", "apigateway"),
        #     ("Tags", "apigateway"),
        #     ("Template", "apigateway"),
        #     ("UsagePlanKeys", "apigateway"),
        #     ("UsagePlanKey", "apigateway"),
        #     ("UsagePlans", "apigateway"),
        #     ("UsagePlan", "apigateway"),
        #     ("VpcLinks", "apigateway"),
        #     ("VpcLink", "apigateway"),
        #     ("apigateway", "apigateway"),
        # ],
        # "aws-marketplace": [
        #     ("ChangeSet", "marketplace-catalog"),
        #     ("DeploymentParameter", "marketplace-catalog"),
        #     ("Entity", "marketplace-catalog"),
        # ],
        # "bedrock": [
        #     # bedrock-agent client resources
        #     ("agent-alias", "bedrock-agent"),
        #     ("agent", "bedrock-agent"),
        #     ("default-prompt-router", "bedrock-agent"),
        #     ("flow-alias", "bedrock-agent"),
        #     ("flow-execution", "bedrock-agent"),
        #     ("flow", "bedrock-agent"),
        #     ("knowledge-base", "bedrock-agent"),
        #     ("prompt-router", "bedrock-agent"),
        #     ("prompt-version", "bedrock-agent"),
        #     ("prompt", "bedrock-agent"),
        #     # bedrock-agent-runtime for sessions
        #     ("session", "bedrock-agent-runtime"),
        #     # bedrock-runtime for inference
        #     ("async-invoke", "bedrock-runtime"),
        #     # bedrock client for model management
        #     ("application-inference-profile", "bedrock"),
        #     ("automated-reasoning-policy-version", "bedrock"),
        #     ("automated-reasoning-policy", "bedrock"),
        #     ("bedrock-marketplace-model-endpoint", "bedrock"),
        #     ("blueprint", "bedrock"),
        #     ("custom-model-deployment", "bedrock"),
        #     ("custom-model", "bedrock"),
        #     ("data-automation-invocation-job", "bedrock"),
        #     ("data-automation-profile", "bedrock"),
        #     ("data-automation-project", "bedrock"),
        #     ("evaluation-job", "bedrock"),
        #     ("foundation-model", "bedrock"),
        #     ("guardrail-profile", "bedrock"),
        #     ("guardrail", "bedrock"),
        #     ("imported-model", "bedrock"),
        #     ("inference-profile", "bedrock"),
        #     ("model-copy-job", "bedrock"),
        #     ("model-customization-job", "bedrock"),
        #     ("model-evaluation-job", "bedrock"),
        #     ("model-import-job", "bedrock"),
        #     ("model-invocation-job", "bedrock"),
        #     ("provisioned-model", "bedrock"),
        #     ("system-tool", "bedrock"),
        # ],
        # "bedrock-agentcore": [
        #     # All resources use bedrock-agentcore-control for management
        #     ("apikeycredentialprovider", "bedrock-agentcore-control"),
        #     ("browser-custom", "bedrock-agentcore-control"),
        #     ("browser", "bedrock-agentcore-control"),
        #     ("code-interpreter-custom", "bedrock-agentcore-control"),
        #     ("code-interpreter", "bedrock-agentcore-control"),
        #     ("evaluator", "bedrock-agentcore-control"),
        #     ("gateway", "bedrock-agentcore-control"),
        #     ("memory", "bedrock-agentcore-control"),
        #     ("oauth2credentialprovider", "bedrock-agentcore-control"),
        #     ("online-evaluation-config", "bedrock-agentcore-control"),
        #     ("policy-engine", "bedrock-agentcore-control"),
        #     ("policy-generation", "bedrock-agentcore-control"),
        #     ("policy", "bedrock-agentcore-control"),
        #     ("runtime-endpoint", "bedrock-agentcore-control"),
        #     ("runtime", "bedrock-agentcore-control"),
        #     ("token-vault", "bedrock-agentcore-control"),
        #     ("workload-identity-directory", "bedrock-agentcore-control"),
        #     ("workload-identity", "bedrock-agentcore-control"),
        # ],
        # "chime": [
        #     ("meeting", "chime-sdk-meetings"),
        #     ("app-instance", "chime-sdk-identity"),
        #     ("app-instance-bot", "chime-sdk-identity"),
        #     ("app-instance-user", "chime-sdk-identity"),
        #     ("channel", "chime-sdk-messaging"),
        #     ("channel-flow", "chime-sdk-messaging"),
        #     ("media-insights-pipeline-configuration", "chime-sdk-media-pipelines"),
        #     ("media-pipeline", "chime-sdk-media-pipelines"),
        #     ("media-pipeline-kinesis-video-stream-pool", "chime-sdk-media-pipelines"),
        #     ("sip-media-application", "chime-sdk-voice"),
        #     ("voice-connector-group", "chime-sdk-voice"),
        #     ("voice-connector", "chime-sdk-voice"),
        #     ("voice-profile", "chime-sdk-voice"),
        #     ("voice-profile-domain", "chime-sdk-voice"),
        # ],
        # "dynamodb": [
        #     ("stream", "dynamodbstreams"),
        #     ("backup", "dynamodb"),
        #     ("export", "dynamodb"),
        #     ("global-table", "dynamodb"),
        #     ("import", "dynamodb"),
        #     ("index", "dynamodb"),
        #     ("table", "dynamodb"),
        # ],
        # "elasticloadbalancing": [
        #     ("listener-rule/app", "elbv2"),
        #     ("listener-rule/net", "elbv2"),
        #     ("listener/app", "elbv2"),
        #     ("listener/gwy", "elbv2"),
        #     ("listener/net", "elbv2"),
        #     ("loadbalancer/app", "elbv2"),
        #     ("loadbalancer/gwy", "elbv2"),
        #     ("loadbalancer/net", "elbv2"),
        #     ("targetgroup", "elbv2"),
        #     ("truststore", "elbv2"),
        #     ("loadbalancer", "elb"),  # classic - must be last
        # ],
        # "greengrass": [
        #     # v2 resources
        #     ("componentVersion", "greengrassv2"),
        #     ("component", "greengrassv2"),
        #     ("coreDevice", "greengrassv2"),
        #     ("deployment", "greengrassv2"),
        #     # v1 resources
        #     ("bulkDeployment", "greengrass"),
        #     ("certificateAuthority", "greengrass"),
        #     ("connectivityInfo", "greengrass"),
        #     ("connectorDefinitionVersion", "greengrass"),
        #     ("connectorDefinition", "greengrass"),
        #     ("coreDefinitionVersion", "greengrass"),
        #     ("coreDefinition", "greengrass"),
        #     ("deviceDefinitionVersion", "greengrass"),
        #     ("deviceDefinition", "greengrass"),
        #     ("functionDefinitionVersion", "greengrass"),
        #     ("functionDefinition", "greengrass"),
        #     ("groupVersion", "greengrass"),
        #     ("group", "greengrass"),
        #     ("loggerDefinitionVersion", "greengrass"),
        #     ("loggerDefinition", "greengrass"),
        #     ("resourceDefinitionVersion", "greengrass"),
        #     ("resourceDefinition", "greengrass"),
        #     ("subscriptionDefinitionVersion", "greengrass"),
        #     ("subscriptionDefinition", "greengrass"),
        #     ("thingRuntimeConfig", "greengrass"),
        # ],
        # "ivs": [
        #     # ivs-realtime resources
        #     ("Composition", "ivs-realtime"),
        #     ("Encoder-Configuration", "ivs-realtime"),
        #     ("Ingest-Configuration", "ivs-realtime"),
        #     ("Public-Key", "ivs-realtime"),
        #     ("Stage", "ivs-realtime"),
        #     ("Storage-Configuration", "ivs-realtime"),
        #     # ivs resources
        #     ("Channel", "ivs"),
        #     ("Playback-Key-Pair", "ivs"),
        #     ("Playback-Restriction-Policy", "ivs"),
        #     ("Recording-Configuration", "ivs"),
        #     ("Stream-Key", "ivs"),
        # ],
        # "lex": [
        #     # v1 specific resources
        #     ("channel", "lex-models"),
        #     ("intent version", "lex-models"),
        #     ("slottype version", "lex-models"),
        #     # v2 specific resources
        #     ("test set", "lexv2-models"),
        #     # Shared - default to v2 (recommended)
        #     ("bot alias", "lexv2-models"),
        #     ("bot version", "lexv2-models"),
        #     ("bot", "lexv2-models"),
        # ],
        # "mediastore": [
        #     ("container", "mediastore"),
        #     ("folder", "mediastore-data"),
        #     ("object", "mediastore-data"),
        # ],
        # "partnercentral": [
        #     # Benefits-related
        #     ("BenefitAllocation", "partnercentral-benefits"),
        #     ("BenefitApplication", "partnercentral-benefits"),
        #     ("Benefit", "partnercentral-benefits"),
        #     # Channel-related
        #     ("ChannelHandshake", "partnercentral-channel"),
        #     # Account-related
        #     ("ProgramManagementAccount", "partnercentral-account"),
        #     # Selling-related (default)
        #     ("ConnectionInvitation", "partnercentral-selling"),
        #     ("ConnectionPreferences", "partnercentral-selling"),
        #     ("Connection", "partnercentral-selling"),
        #     ("Dashboard", "partnercentral-selling"),
        #     ("Engagement", "partnercentral-selling"),
        #     ("OpportunityFromEngagementTask", "partnercentral-selling"),
        #     ("Opportunity", "partnercentral-selling"),
        #     ("Partner", "partnercentral-selling"),
        #     ("Relationship", "partnercentral-selling"),
        #     ("ResourceSnapshot", "partnercentral-selling"),
        #     ("Solution", "partnercentral-selling"),
        #     ("engagement-by-accepting-invitation-task", "partnercentral-selling"),
        #     ("engagement-from-opportunity-task", "partnercentral-selling"),
        #     ("engagement-invitation", "partnercentral-selling"),
        #     ("resource-snapshot-job", "partnercentral-selling"),
        # ],
        # "route53-recovery-control": [
        #     ("cluster", "route53-recovery-control-config"),
        #     ("controlpanel", "route53-recovery-control-config"),
        #     ("routingcontrol", "route53-recovery-control-config"),
        #     ("safetyrule", "route53-recovery-control-config"),
        # ],
        # "s3": [
        #     ("accessgrant", "s3control"),
        #     ("accessgrantslocation", "s3control"),
        #     ("accessgrantsinstance", "s3control"),
        #     ("accesspoint", "s3control"),
        #     ("accesspointobject", "s3control"),
        #     ("job", "s3control"),
        #     ("multiregionaccesspoint", "s3control"),
        #     ("multiregionaccesspointrequestarn", "s3control"),
        #     ("storagelensconfiguration", "s3control"),
        #     ("storagelensgroup", "s3control"),
        #     ("bucket", "s3"),
        #     ("object", "s3"),
        # ],
        # "servicecatalog": [
        #     # AppRegistry resources
        #     ("Application", "servicecatalog-appregistry"),
        #     ("AttributeGroup", "servicecatalog-appregistry"),
        # ],
    }

    def process(self, sdk_mapping):
        """Validate all multi-SDK services have a DEFAULT_SERVICE entry."""
        missing = {}
        for arn_service, sdks in sdk_mapping.items():
            if len(sdks) > 1 and arn_service not in self.DEFAULT_SERVICE:
                missing[arn_service] = sdks
        if missing:
            raise RuntimeError(f"Missing DEFAULT_SERVICE for multi-SDK services: {missing}")
