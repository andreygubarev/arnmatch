"""Tests for ARN pattern matching."""

from arnmatch import arnmatch


def test_acm():
    result = arnmatch(
        "arn:aws:acm:us-east-1:012345678901:certificate/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    assert result.resource_type == "certificate"
    assert result.attributes["CertificateId"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_apigateway():
    result = arnmatch("arn:aws:apigateway:us-east-1::/restapis/abc123def4")
    assert result.resource_type == "RestApi"
    assert result.attributes["RestApiId"] == "abc123def4"


def test_athena():
    result = arnmatch("arn:aws:athena:us-east-1:012345678901:workgroup/workgroup1")
    assert result.resource_type == "workgroup"
    assert result.attributes["WorkGroupName"] == "workgroup1"


def test_autoscaling():
    result = arnmatch(
        "arn:aws:autoscaling:us-east-1:012345678901:autoScalingGroup:aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee:autoScalingGroupName/asg1"
    )
    assert result.resource_type == "autoScalingGroup"
    assert result.attributes["GroupId"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert result.attributes["GroupFriendlyName"] == "asg1"


def test_backup():
    result = arnmatch("arn:aws:backup:us-east-1:012345678901:backup-vault:vault1")
    assert result.resource_type == "backupVault"
    assert result.attributes["BackupVaultName"] == "vault1"


def test_cloudformation():
    result = arnmatch(
        "arn:aws:cloudformation:us-east-1:012345678901:stack/stack1/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    assert result.resource_type == "stack"
    assert result.attributes["StackName"] == "stack1"
    assert result.attributes["Id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_cloudfront():
    result = arnmatch("arn:aws:cloudfront::012345678901:distribution/ABCDEFGHIJKLMN")
    assert result.resource_type == "distribution"
    assert result.attributes["DistributionId"] == "ABCDEFGHIJKLMN"


def test_cloudtrail():
    result = arnmatch("arn:aws:cloudtrail:us-east-1:012345678901:trail/trailname1")
    assert result.resource_type == "trail"
    assert result.attributes["TrailName"] == "trailname1"


def test_cloudwatch():
    result = arnmatch(
        "arn:aws:cloudwatch:us-east-1:012345678901:alarm:CPU Utilization - High Warning - service-production-1"
    )
    assert result.resource_type == "alarm"
    assert (
        result.attributes["AlarmName"]
        == "CPU Utilization - High Warning - service-production-1"
    )


def test_codebuild():
    result = arnmatch("arn:aws:codebuild:us-east-1:012345678901:project/build_image")
    assert result.resource_type == "project"
    assert result.attributes["ProjectName"] == "build_image"


def test_codecommit():
    result = arnmatch("arn:aws:codecommit:us-east-1:012345678901:repository1")
    assert result.resource_type == "repository"
    assert result.attributes["RepositoryName"] == "repository1"


def test_codepipeline():
    result = arnmatch("arn:aws:codepipeline:us-east-1:012345678901:deploy_pipeline")
    assert result.resource_type == "pipeline"
    assert result.attributes["PipelineName"] == "deploy_pipeline"


def test_datasync():
    result = arnmatch(
        "arn:aws:datasync:us-east-1:012345678901:task/task-0123456789abcdef0"
    )
    assert result.resource_type == "task"
    assert result.attributes["TaskId"] == "task-0123456789abcdef0"


def test_dynamodb():
    result = arnmatch("arn:aws:dynamodb:us-east-1:012345678901:table/table1")
    assert result.resource_type == "table"
    assert result.attributes["TableName"] == "table1"


def test_ec2():
    result = arnmatch("arn:aws:ec2:us-east-1:012345678901:instance/i-0123456789abcdef0")
    assert result.resource_type == "instance"
    assert result.attributes["InstanceId"] == "i-0123456789abcdef0"

    result = arnmatch("arn:aws:ec2:us-east-1:012345678901:volume/vol-0123456789abcdef0")
    assert result.resource_type == "volume"
    assert result.attributes["VolumeId"] == "vol-0123456789abcdef0"

    result = arnmatch(
        "arn:aws:ec2:us-east-1:012345678901:snapshot/snap-0123456789abcdef0"
    )
    assert result.resource_type == "snapshot"
    assert result.attributes["SnapshotId"] == "snap-0123456789abcdef0"

    result = arnmatch("arn:aws:ec2:us-east-1:012345678901:image/ami-0123456789abcdef0")
    assert result.resource_type == "image"
    assert result.attributes["ImageId"] == "ami-0123456789abcdef0"

    result = arnmatch(
        "arn:aws:ec2:us-east-1:012345678901:elastic-ip/eipalloc-0123456789abcdef0"
    )
    assert result.resource_type == "elastic-ip"
    assert result.attributes["AllocationId"] == "eipalloc-0123456789abcdef0"

    result = arnmatch(
        "arn:aws:ec2:us-east-1:012345678901:natgateway/nat-0123456789abcdef0"
    )
    assert result.resource_type == "natgateway"
    assert result.attributes["NatGatewayId"] == "nat-0123456789abcdef0"

    result = arnmatch(
        "arn:aws:ec2:us-east-1:012345678901:vpc-endpoint/vpce-0123456789abcdef0"
    )
    assert result.resource_type == "vpc-endpoint"
    assert result.attributes["VpcEndpointId"] == "vpce-0123456789abcdef0"

    result = arnmatch(
        "arn:aws:ec2:us-east-1:012345678901:launch-template/lt-0123456789abcdef0"
    )
    assert result.resource_type == "launch-template"
    assert result.attributes["LaunchTemplateId"] == "lt-0123456789abcdef0"

    result = arnmatch(
        "arn:aws:ec2:us-east-1:012345678901:reserved-instances/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    assert result.resource_type == "reserved-instances"
    assert result.attributes["ReservationId"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    result = arnmatch(
        "arn:aws:ec2:us-east-1:012345678901:spot-instances-request/sir-abcd1234"
    )
    assert result.resource_type == "spot-instances-request"
    assert result.attributes["SpotInstanceRequestId"] == "sir-abcd1234"


def test_ecr():
    result = arnmatch("arn:aws:ecr:us-east-1:012345678901:repository/web-service")
    assert result.resource_type == "repository"
    assert result.attributes["RepositoryName"] == "web-service"


def test_eks():
    result = arnmatch("arn:aws:eks:us-east-1:012345678901:cluster/c1")
    assert result.resource_type == "cluster"
    assert result.attributes["ClusterName"] == "c1"


def test_elasticache():
    result = arnmatch(
        "arn:aws:elasticache:us-east-1:012345678901:cluster:redis-cluster-node-001"
    )
    assert result.resource_type == "cluster"
    assert result.attributes["CacheClusterId"] == "redis-cluster-node-001"

    result = arnmatch(
        "arn:aws:elasticache:us-east-1:012345678901:parametergroup:redis-cluster-params-redis7"
    )
    assert result.resource_type == "parametergroup"
    assert result.attributes["CacheParameterGroupName"] == "redis-cluster-params-redis7"

    result = arnmatch(
        "arn:aws:elasticache:us-east-1:012345678901:replicationgroup:redis-repl-group1"
    )
    assert result.resource_type == "replicationgroup"
    assert result.attributes["ReplicationGroupId"] == "redis-repl-group1"

    result = arnmatch(
        "arn:aws:elasticache:us-east-1:012345678901:reserved-instance:reserved-node-prod1"
    )
    assert result.resource_type == "reserved-instance"
    assert result.attributes["ReservedCacheNodeId"] == "reserved-node-prod1"

    result = arnmatch(
        "arn:aws:elasticache:us-east-1:012345678901:subnetgroup:cache-subnet-group1"
    )
    assert result.resource_type == "subnetgroup"
    assert result.attributes["CacheSubnetGroupName"] == "cache-subnet-group1"

    result = arnmatch("arn:aws:elasticache:us-east-1:012345678901:user:default")
    assert result.resource_type == "user"
    assert result.attributes["UserId"] == "default"


def test_elasticfilesystem():
    result = arnmatch(
        "arn:aws:elasticfilesystem:us-east-1:012345678901:file-system/fs-01234567"
    )
    assert result.resource_type == "file-system"
    assert result.attributes["FileSystemId"] == "fs-01234567"


def test_elasticloadbalancing():
    # Classic LB
    result = arnmatch(
        "arn:aws:elasticloadbalancing:us-east-1:012345678901:loadbalancer/a0123456789abcdef0123456789abcde"
    )
    assert result.resource_type == "loadbalancer"
    assert result.attributes["LoadBalancerName"] == "a0123456789abcdef0123456789abcde"

    # ALB
    result = arnmatch(
        "arn:aws:elasticloadbalancing:us-east-1:012345678901:loadbalancer/app/alb-application-lb-name/0123456789abcdef"
    )
    assert result.resource_type == "loadbalancer/app/"
    assert result.attributes["LoadBalancerName"] == "alb-application-lb-name"
    assert result.attributes["LoadBalancerId"] == "0123456789abcdef"

    # NLB
    result = arnmatch(
        "arn:aws:elasticloadbalancing:us-east-1:012345678901:loadbalancer/net/nlb-network-load-balancer/0123456789abcdef"
    )
    assert result.resource_type == "loadbalancer/net/"
    assert result.attributes["LoadBalancerName"] == "nlb-network-load-balancer"
    assert result.attributes["LoadBalancerId"] == "0123456789abcdef"

    # Target group
    result = arnmatch(
        "arn:aws:elasticloadbalancing:us-east-1:012345678901:targetgroup/target-grp-1/0123456789abcdef"
    )
    assert result.resource_type == "targetgroup"
    assert result.attributes["TargetGroupName"] == "target-grp-1"
    assert result.attributes["TargetGroupId"] == "0123456789abcdef"


def test_es():
    result = arnmatch("arn:aws:es:us-east-1:012345678901:domain/search-domain-prod")
    assert result.resource_type == "domain"
    assert result.attributes["DomainName"] == "search-domain-prod"


def test_events():
    result = arnmatch("arn:aws:events:us-east-1:012345678901:event-bus/default")
    assert result.resource_type == "event-bus"
    assert result.attributes["EventBusName"] == "default"

    result = arnmatch("arn:aws:events:us-east-1:012345678901:rule/ScheduledEventRule01")
    assert result.resource_type == "rule-on-default-event-bus"
    assert result.attributes["RuleName"] == "ScheduledEventRule01"


def test_guardduty():
    result = arnmatch(
        "arn:aws:guardduty:us-east-1:012345678901:detector/0123456789abcdef0123456789abcdef"
    )
    assert result.resource_type == "detector"
    assert result.attributes["DetectorId"] == "0123456789abcdef0123456789abcdef"


def test_iam():
    result = arnmatch("arn:aws:iam::012345678901:user/admin")
    assert result.resource_type == "user"
    assert result.attributes["AwsUserName"] == "admin"

    result = arnmatch("arn:aws:iam::012345678901:role/lambda-execution-role")
    assert result.resource_type == "role"
    assert result.attributes["RoleNameWithPath"] == "lambda-execution-role"

    result = arnmatch("arn:aws:iam::012345678901:policy/custom-policy")
    assert result.resource_type == "policy"
    assert result.attributes["PolicyNameWithPath"] == "custom-policy"

    result = arnmatch("arn:aws:iam::012345678901:group/developers")
    assert result.resource_type == "group"
    assert result.attributes["GroupNameWithPath"] == "developers"

    result = arnmatch("arn:aws:iam::012345678901:instance-profile/ec2-profile")
    assert result.resource_type == "instance-profile"
    assert result.attributes["InstanceProfileNameWithPath"] == "ec2-profile"


def test_kms():
    result = arnmatch(
        "arn:aws:kms:us-east-1:012345678901:key/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    assert result.resource_type == "key"
    assert result.attributes["KeyId"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_lambda():
    result = arnmatch(
        "arn:aws:lambda:us-east-1:012345678901:function:ProcessDataHandler"
    )
    assert result.resource_type == "function"
    assert result.attributes["FunctionName"] == "ProcessDataHandler"


def test_logs():
    result = arnmatch(
        "arn:aws:logs:us-east-1:012345678901:log-group:/aws/lambda/function-logs"
    )
    assert result.resource_type == "log-group"
    assert result.attributes["LogGroupName"] == "/aws/lambda/function-logs"


def test_rds():
    result = arnmatch("arn:aws:rds:us-east-1:012345678901:cluster:database-cluster-1")
    assert result.resource_type == "cluster"
    assert result.attributes["DbClusterInstanceName"] == "database-cluster-1"

    result = arnmatch("arn:aws:rds:us-east-1:012345678901:cluster-snapshot:snap001")
    assert result.resource_type == "cluster-snapshot"
    assert result.attributes["ClusterSnapshotName"] == "snap001"

    result = arnmatch("arn:aws:rds:us-east-1:012345678901:db:database-instance-1")
    assert result.resource_type == "db"
    assert result.attributes["DbInstanceName"] == "database-instance-1"

    result = arnmatch("arn:aws:rds:us-east-1:012345678901:ri:reserved01")
    assert result.resource_type == "ri"
    assert result.attributes["ReservedDbInstanceName"] == "reserved01"

    result = arnmatch(
        "arn:aws:rds:us-east-1:012345678901:snapshot:final-database-backup-01234567"
    )
    assert result.resource_type == "snapshot"
    assert result.attributes["SnapshotName"] == "final-database-backup-01234567"


def test_route53():
    result = arnmatch(
        "arn:aws:route53:::healthcheck/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    assert result.resource_type == "healthcheck"
    assert result.attributes["Id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    result = arnmatch("arn:aws:route53:::hostedzone/Z0123456789ABCDEFGHIJ")
    assert result.resource_type == "hostedzone"
    assert result.attributes["Id"] == "Z0123456789ABCDEFGHIJ"


def test_s3():
    result = arnmatch("arn:aws:s3:::example-bucket-01")
    assert result.resource_type == "bucket"
    assert result.attributes["BucketName"] == "example-bucket-01"


def test_secretsmanager():
    result = arnmatch(
        "arn:aws:secretsmanager:us-east-1:012345678901:secret:/app/secrets/service-name/production-AbCdEf"
    )
    assert result.resource_type == "Secret"
    assert result.attributes["SecretId"] == "/app/secrets/service-name/production-AbCdEf"


def test_sns():
    result = arnmatch("arn:aws:sns:us-east-1:012345678901:topic1")
    assert result.resource_type == "topic"
    assert result.attributes["TopicName"] == "topic1"


def test_sqs():
    result = arnmatch("arn:aws:sqs:us-east-1:012345678901:processing-queue-1")
    assert result.resource_type == "queue"
    assert result.attributes["QueueName"] == "processing-queue-1"


def test_ssm():
    result = arnmatch("arn:aws:ssm:us-east-1:012345678901:parameter/config_val")
    assert result.resource_type == "parameter"
    assert result.attributes["ParameterNameWithoutLeadingSlash"] == "config_val"


def test_wafv2():
    result = arnmatch(
        "arn:aws:wafv2:us-east-1:012345678901:global/webacl/WebACL-for-CloudFront-01/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    assert result.resource_type == "webacl"
    assert result.attributes["Scope"] == "global"
    assert result.attributes["Name"] == "WebACL-for-CloudFront-01"
    assert result.attributes["Id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    result = arnmatch(
        "arn:aws:wafv2:us-east-1:012345678901:regional/webacl/webacl-production-acl/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )
    assert result.resource_type == "webacl"
    assert result.attributes["Scope"] == "regional"
    assert result.attributes["Name"] == "webacl-production-acl"
    assert result.attributes["Id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
