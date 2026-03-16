# Argus

Argus is an AI-powered internet operator that can navigate websites on behalf of a user. It combines LLM planning with browser automation and strict safety controls.

## Argus Capability Learning Architecture

### Capability model
Argus uses first-class capability records for `stable`, `generated_temporary`, `generated_candidate`, `approved_stable`, and `rejected` states. Each capability stores id/version, declared domains, implementation kind, and metadata required for deterministic execution and auditing.

### Generation pipeline
Generated capability flow is now operational:
1. `spec_created`
2. `generation_completed`
3. `package_validated`
4. `sandbox_executed`
5. `evaluation_completed`
6. `capability_registered` or `capability_rejected`

Generated packages include capability id, version, declared domains, entrypoint, metadata, and source code.

### Sandbox validation
Sandbox validation enforces:
- entrypoint presence (`run(arguments[, context])`)
- import allowlist checks
- blocked dangerous calls (`open`, `exec`, `eval`, etc.)
- execution timeout
- controlled context that blocks undeclared domain access

### Evaluator
Evaluator verifies sandbox result success, evidence quality, and safety-policy compatibility (including domain governance). It emits structured score/evidence metrics for lifecycle and memory.

### Lifecycle and promotion
Lifecycle states:
- `generated_temporary`
- `generated_candidate`
- `approved_stable`
- `rejected`

Promotion policy is configurable (minimum successful runs, evaluator score threshold, safety violations, evidence completeness).

### Artifact storage
Generated capability artifacts are persisted to filesystem storage:

```text
capabilities/
  generated/
    capability_id/
      metadata.json
      source.py
      sandbox_result.json
      evaluation.json
      usage_log.json
```

This storage model is intentionally simple and DB-migration friendly.

### Safety constraints
- Generated capabilities never bypass `SafetyPolicy`.
- Domain access is least-privilege and explicit.
- Rejected capabilities are never reused.
- Stable capabilities are preferred over generated ones.

> ⚠️ **Warning**: generated capability learning/execution must run in isolated environments. Do not enable it in shared production hosts without process/container isolation and strict runtime controls.

## Configuration
Generated capability controls:
- `ARGUS_ENABLE_GENERATED_CAPABILITIES`
- `ARGUS_SANDBOX_ENABLED`
- `ARGUS_GENERATED_CAPABILITY_STORAGE_PATH`
- `ARGUS_GENERATED_CAPABILITY_TIMEOUT`
- `ARGUS_GENERATED_CAPABILITY_PROMOTION_THRESHOLD`
- `ARGUS_GENERATED_CAPABILITY_MAX_ATTEMPTS`
- `ARGUS_CAPABILITY_MEMORY_ENABLED`

## CLI usage
```bash
argus show-config
argus list-skills
argus list-capabilities --kind all
argus show-capability-memory
argus run-amazon-task "Check whether my latest Amazon order has been delivered"
```
