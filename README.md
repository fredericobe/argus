# Argus

Argus is an AI-powered internet operator that can navigate websites on behalf of a user. It combines LLM planning with browser automation and strict safety controls.

Example user goal:

> "Check whether my latest Amazon order has been delivered."

## Architecture

Argus now supports a capability-oriented execution loop:

```text
User Request
   ↓
Planner (LLM)
   ↓
Capability Resolver
   ↓
Capability Type Decision
   ├─ Stable skill-backed capability
   ├─ Learned capability
   ├─ Generated temporary capability (sandboxed)
   └─ Human confirmation / safe fail
   ↓
Executor / Sandbox
   ↓
Observation + Audit
   ↓
Evaluator / Critic
   ↓
Capability Memory + Promotion lifecycle
```

### Core Components

- **Planner (`app/planner/`)**
  - Produces structured next actions.
- **Capabilities (`app/capabilities/`)**
  - First-class model for stable, learned, and generated capabilities.
  - Includes registry, resolver, lifecycle, and memory.
- **Skills (`app/skills/`)**
  - Existing stable skills remain unchanged and are wrapped as stable capabilities.
- **Builder (`app/builder/`)**
  - Builds temporary capabilities via spec → code provider → sandbox → evaluator.
- **Executors (`app/executors/`)**
  - Low-level browser actions and interaction primitives.
- **Safety (`app/safety/`)**
  - Domain allow/block rules, max steps, destructive-action confirmation.
- **Credentials (`app/credentials/`)**
  - Composite provider; generated capabilities do not bypass this path.
- **Observability (`app/models/audit.py`)**
  - Per-step, auditable records across stable and generated paths.

## Capability Model

Each capability tracks:

- id, name, description, version
- status, risk_level, capability_type
- allowed_domains, required_inputs, expected_outputs
- implementation_kind, tags, author/source
- created_at, updated_at

Supported types:

- `stable`
- `learned`
- `generated_temporary`
- `generated_candidate`

Supported implementation kinds:

- `skill`
- `browser_workflow`
- `api_adapter`
- `generated_code`

## Capability Resolver

Resolution order is explicit and auditable:

1. Stable capability match
2. Learned capability match
3. Generated capability path
4. Human confirmation or safe failure

High-risk capabilities return a confirmation path instead of direct execution.

## Generated Capability Lifecycle

Generated capabilities move through:

1. `generated_temporary`
2. sandbox validation + execution
3. evaluator acceptance/rejection
4. accepted → `generated_candidate`
5. later promotion path → `approved_stable`

Rejected capabilities are marked `rejected` and not reused.

## Sandboxed Generation Path

Generated capability flow:

1. create `CapabilitySpec`
2. call abstract code generation provider
3. validate package structure in sandbox
4. run sandbox evaluation
5. evaluator verifies evidence + safety compliance
6. register resulting capability and audit artifacts

> ⚠️ Generated capabilities are powerful. Run only in isolated environments and keep `ARGUS_ALLOW_GENERATED_CODE_EXECUTION=false` unless you have strong containment controls.

## Memory of Learned Capabilities

Argus stores capability usage records (JSON-backed path by default):

- capability id
- task
- success/failure
- reason
- timestamp

This enables deterministic reuse and future persistence upgrades.

## Configuration

Copy example config:

```bash
cp .env.example .env
```

Required:

- `ARGUS_OPENAI_API_KEY`
- `ARGUS_ALLOWED_DOMAINS`

Capability-learning settings:

- `ARGUS_ENABLE_GENERATED_CAPABILITIES`
- `ARGUS_SANDBOX_ENABLED`
- `ARGUS_CAPABILITY_STORAGE_PATH`
- `ARGUS_MAX_GENERATED_CAPABILITY_ATTEMPTS`
- `ARGUS_EVALUATOR_STRICT_MODE`
- `ARGUS_ALLOW_GENERATED_CODE_EXECUTION`
- `ARGUS_GENERATED_CAPABILITY_TIMEOUT_SECONDS`

## CLI Usage

```bash
argus show-config
argus list-skills
argus list-capabilities --kind all
argus show-capability-memory
argus run-amazon-task "Check whether my latest Amazon order has been delivered"
```

## Security Considerations

- Generated capabilities must declare domains.
- Allowlist/blocklist checks are still enforced.
- High-risk actions still require confirmation.
- Audit records remain mandatory for traceability.
- Credentials remain provider-mediated.
- Do not run generated capabilities outside isolated sandboxes.

See [SECURITY.md](SECURITY.md) for operational guidance.
