# SECURITY.md

Argus automates authenticated browser activity and must be treated as a high-risk system.

## Core Principles

1. **Isolate execution**: run Argus in a dedicated VM/container/secondary workstation.
2. **Least privilege**: use low-privilege accounts with minimum permissions.
3. **No hardcoded secrets**: credentials must come from approved secret providers.
4. **Constrained navigation**: enforce strict domain allowlist and blocked-domain policy.
5. **Human control for high-risk actions**: purchases/payments/deletions/account changes require explicit confirmation.

## Credential Handling

Supported providers:

- `EnvCredentialProvider`
- `KeyringCredentialProvider`
- `CompositeCredentialProvider`

Guidance:

- Prefer OS keyring over plaintext environment files.
- Never commit `.env`, session state, or screenshots.
- Rotate and revoke credentials regularly.
- Avoid logging secrets in any form.

## Isolated Runtime Guidance

- Use a dedicated machine image for Argus only.
- Disable unnecessary software/services in the VM.
- Restrict network egress to required domains.
- Regularly rebuild from clean snapshots.

## Session and Artifact Hygiene

- Playwright storage state files may contain authentication tokens.
- Screenshots may contain personal data.
- Apply strict filesystem permissions and short retention periods.

## Account Safety

- Prefer test/sandbox accounts for development.
- Avoid primary personal/admin accounts.
- Remove payment methods where practical.

## Future Secret-Manager Integrations

Argus is designed for extension to:

- HashiCorp Vault
- AWS Secrets Manager
- GCP Secret Manager
- Azure Key Vault

When adding integrations, require access auditing, short-lived credentials, and minimal in-memory caching.
