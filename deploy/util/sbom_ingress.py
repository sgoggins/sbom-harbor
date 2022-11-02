"""
-> Module to house SbomIngressLambda
"""
from aws_cdk import Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3 as i_bucket
from constructs import Construct

from cyclonedx.constants import SBOM_BUCKET_NAME_KEY
from deploy.constants import PRIVATE, SBOM_API_PYTHON_RUNTIME, SBOM_INGRESS_LN
from deploy.util import create_asset


class SbomIngressLambda(Construct):

    """Constructs a Lambda that can take
    SBOMS and puts them in the S3 Bucket"""

    def __init__(
        self,
        scope: Construct,
        *,
        vpc: ec2.Vpc,
        s3_bucket: i_bucket,
    ):

        super().__init__(scope, SBOM_INGRESS_LN)

        self.sbom_ingress_func = lambda_.Function(
            self,
            SBOM_INGRESS_LN,
            function_name="SbomIngressLambda",
            runtime=SBOM_API_PYTHON_RUNTIME,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=PRIVATE),
            handler="cyclonedx.handlers.sbom_ingress_handler",
            code=create_asset(self),
            environment={
                SBOM_BUCKET_NAME_KEY: s3_bucket.bucket_name,
            },
            timeout=Duration.seconds(10),
            memory_size=512,
        )

        s3_bucket.grant_put(self.sbom_ingress_func)

        self.sbom_ingress_func.grant_invoke(
            iam.ServicePrincipal("apigateway.amazonaws.com"),
        )

    def get_lambda_function(self):

        """
        -> Get the CDK Lambda Construct
        """

        return self.sbom_ingress_func
