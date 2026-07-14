#!/usr/bin/env bash
# Build the Lambda package with uv and provision infra via CloudFormation.
# Idempotent: re-run to ship new code / update the stack.
set -euo pipefail
cd "$(dirname "$0")/.."

REGION="${AWS_REGION:-eu-west-1}"
STACK="${STACK:-ai-engineering-gym}"
DOMAIN="${DOMAIN:-gym.dtcdev.click}"
ZONE="${ZONE:-Z05963572WVWFHDQZH5NE}"        # authoritative dtcdev.click zone
PASSPHRASE="${GYM_PASSPHRASE:-aislgym}"

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="ai-eng-gym-deploy-${ACCOUNT}-${REGION}"
KEY="lambda/build-$(date +%s).zip"
SESSION_SECRET="${SESSION_SECRET:-$(uv run python -c 'import secrets;print(secrets.token_hex(32))')}"
AUTH_STACK="${AUTH_STACK:-dtcdev-shared-auth}"
auth_output() {
  aws cloudformation describe-stacks --region us-east-1 --stack-name "$AUTH_STACK" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
AUTH_CLIENT_ID="${AUTH_CLIENT_ID:-$(auth_output GymClientId)}"
AUTH_ISSUER="${AUTH_ISSUER:-$(auth_output IssuerUrl)}"
AUTH_JWKS_URL="${AUTH_JWKS_URL:-$(auth_output JwksUrl)}"

echo "==> building package with uv"
rm -rf build && mkdir -p build/pkg
uv pip install --target build/pkg . --quiet
cp -r content build/pkg/content
echo "    prebuilding content bundle (fast cold-start ingest)"
INGEST_INCLUDE_DRAFTS=true uv run python -c "from app.ingest import build_items_bundle; print('    bundle items:', build_items_bundle('content','build/pkg/content_bundle.json'))"
find build/pkg -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
uv run python -c "import shutil; shutil.make_archive('build/lambda','zip','build/pkg')"
echo "    package: $(du -h build/lambda.zip | cut -f1)"

echo "==> ensuring code bucket ${BUCKET}"
if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  aws s3api create-bucket --bucket "$BUCKET" --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION" >/dev/null
fi
aws s3 cp build/lambda.zip "s3://${BUCKET}/${KEY}" >/dev/null

echo "==> deploying CloudFormation stack ${STACK} (region ${REGION})"
aws cloudformation deploy --region "$REGION" --stack-name "$STACK" \
  --template-file infra/cloudformation.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    CodeBucket="$BUCKET" CodeKey="$KEY" \
    Passphrase="$PASSPHRASE" SessionSecret="$SESSION_SECRET" \
    DomainName="$DOMAIN" HostedZoneId="$ZONE" \
    AuthClientId="$AUTH_CLIENT_ID" AuthIssuer="$AUTH_ISSUER" AuthJwksUrl="$AUTH_JWKS_URL"

echo "==> outputs"
aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs" --output table
