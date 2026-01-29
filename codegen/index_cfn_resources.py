"""Maps ARN resource types to CloudFormation resource types."""


class CFNResourceIndexer:
    """Maps ARN resources to CloudFormation resource types."""

    def process(self, by_service, arn_to_cfn):
        """Build ARN service to resource types mapping."""
        arn_with_cfn = [arn for arn, cfn in arn_to_cfn.items() if cfn]

        arn_to_rt = {}
        for service, patterns in by_service.items():
            if service not in arn_with_cfn:
                continue
            resource_types = set()
            for regex, type_names in patterns:
                resource_types.update(type_names)
            arn_to_rt[service] = sorted(resource_types)

        import pprint
        pprint.pprint(arn_to_rt)
        return arn_to_rt
