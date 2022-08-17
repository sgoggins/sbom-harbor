from aws_cdk import (
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_events as eventbridge,
    Duration,
)
from constructs import Construct

from cyclonedx.constants import (
    SBOM_BUCKET_NAME_KEY,
)
from deploy.constants import (
    PRIVATE,
    SBOM_API_PYTHON_RUNTIME,
    SBOM_ENRICHMENT_LN,
)
from deploy.util import create_asset


class EnrichmentIngressLambda(Construct):

    """Create the Lambda Function responsible for listening on the S3 Bucket
    for SBOMs being inserted so they can be inserted into the enrichment process."""

    def __init__(
        self,
        scope: Construct,
        s3_bucket: s3.IBucket,
        *,
        vpc: ec2.Vpc,
        event_bus: eventbridge.EventBus,
    ):

        super().__init__(scope, SBOM_ENRICHMENT_LN)

        self.func = lambda_.Function(
            self,
            SBOM_ENRICHMENT_LN,
            function_name="EnrichmentIngressLambda",
            runtime=SBOM_API_PYTHON_RUNTIME,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=PRIVATE),
            handler="cyclonedx.enrichment.enrichment_ingress_handler",
            code=create_asset(self),
            environment={
                SBOM_BUCKET_NAME_KEY: s3_bucket.bucket_name,
            },
            timeout=Duration.seconds(10),
            memory_size=512,
        )

        # Bucket rights granted
        s3_bucket.grant_read(self.func)

        # Write to EventBridge
        event_bus.grant_put_events_to(self.func)

        # Set up the S3 Bucket to send a notification to the Lambda
        # if someone puts something in the bucket.
        s3_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self.func),
            s3.NotificationKeyFilter(
                prefix="sbom",
            ),
        )

    def get_lambda_function(self):
        return self.func