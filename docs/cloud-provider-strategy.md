# Cloud provider strategy

Azure Blob and AWS S3 are manual setup targets. Personal OS reports setup state but does not create paid resources.

- Azure Blob: use an existing container and a container-scoped SAS with write/create/list only. Do not provide an account key or subscription-owner credential.
- AWS S3: use an existing bucket and a bucket-scoped IAM role/profile with object write/list only. Never provide AWS root credentials or administrator access.

Provider-native encryption at rest should be enabled in addition to Personal OS client-side backup encryption. Cost, retention, immutability, and lifecycle policies remain explicit operator decisions.
