const { awscdk } = require('projen');
const project = new awscdk.AwsCdkTypeScriptApp({
  cdkVersion: '2.65.0',
  defaultReleaseBranch: 'main',
  name: 'amazon-chime-sdk-sma-meeting-dialer',
  license: 'MIT-0',
  author: 'Court Schuett',
  copyrightOwner: 'Amazon.com, Inc.',
  authorAddress: 'https://aws.amazon.com',
  defaultReleaseBranch: 'main',
  appEntrypoint: 'amazon-chime-sdk-sma-meeting-dialer.ts',
  depsUpgradeOptions: {
    ignoreProjen: false,
    workflowOptions: {
      labels: ['auto-approve', 'auto-merge'],
    },
  },
  autoApproveOptions: {
    secret: 'GITHUB_TOKEN',
    allowedUsernames: ['schuettc'],
  },
  autoApproveUpgrades: true,
  devDeps: ['esbuild'],
  deps: ['cdk-amazon-chime-resources@latest', 'fs-extra', '@types/fs-extra'],
  projenUpgradeSecret: 'PROJEN_GITHUB_TOKEN',
  defaultReleaseBranch: 'main',
});

const common_exclude = [
  'cdk.out',
  'cdk.context.json',
  'yarn-error.log',
  'dependabot.yml',
  '.DS_Store',
];

project.addTask('launch', {
  exec: 'yarn && yarn projen && yarn build && yarn cdk bootstrap && yarn cdk deploy --require-approval never && yarn configLocal',
});
project.addTask('getBucket', {
  exec: "aws cloudformation describe-stacks --stack-name SMAMeetingDialer --region us-east-1 --query 'Stacks[0].Outputs[?OutputKey==`siteBucket`].OutputValue' --output text",
});

project.addTask('configLocal', {
  exec: 'aws s3 cp s3://$(yarn run --silent getBucket)/config.json site/public/',
});

project.gitignore.exclude(...common_exclude);
project.synth();
