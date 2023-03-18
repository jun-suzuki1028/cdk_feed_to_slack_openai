import * as lambdaPython from "@aws-cdk/aws-lambda-python-alpha";
import {
  aws_lambda as lambda,
  aws_ssm as ssm,
  aws_iam as iam,
  aws_events as events,
  aws_events_targets as targets,
  Stack,
  StackProps,
  Duration,
} from "aws-cdk-lib";
import { Construct } from "constructs";
import * as path from "path";

export class FeedToSlackOpenaiStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // OpenAI含むLambdaレイヤー
    const OpenaiLayer = new lambdaPython.PythonLayerVersion(
      this,
      "OpenaiLayer",
      {
        description: "Openai layer",
        layerVersionName: "Openai-layer",
        entry: path.resolve(__dirname, "../src/layer"),
        compatibleRuntimes: [lambda.Runtime.PYTHON_3_8],
        bundling: {
          // translates to `rsync --exclude='.venv'`
          assetExcludes: ['.venv'],
        },
      }
    );
    new ssm.StringParameter(this, "OpenaiLayerArnParameter", {
      parameterName: "/lambda-layer/OpenAI-layer-arn",
      stringValue: OpenaiLayer.layerVersionArn,
    });

    const policy = new iam.ManagedPolicy(this, "FeedToSlackLambdaPolicy", {
      managedPolicyName: "FeedToSlackLambdaPolicy",
      statements: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
          ],
          resources: ["arn:aws:logs:*:*:*"],
        }),
      ],
    });
    const lambdaRole = new iam.Role(this, "FeedToSlackLambdaRole", {
      roleName: "FeedToSlackLambdaRole",
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        policy,
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonSSMReadOnlyAccess"),
      ],
    });

    // AWS Lambdaの作成
    const lambdaFn = new lambda.Function(this, "FeedToSlackOpenaiFn", {
      runtime: lambda.Runtime.PYTHON_3_8,
      code: lambda.Code.fromAsset("src"),
      handler: "feed_to_slack.lambda_handler",
      timeout: Duration.seconds(300),
      layers: [OpenaiLayer],
      role: lambdaRole,
    });

    // Eventルールの作成
    const eventRule = new events.Rule(this, "FeedToSlackRule", {
      schedule: events.Schedule.cron({
        minute: "0", // 毎時0分に実行
      }),
    });

    // LambdaをEventルールのターゲットに設定
    eventRule.addTarget(new targets.LambdaFunction(lambdaFn));
  }
}
