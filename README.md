# Argus

Argus is an AI-powered internet operator that can navigate websites on behalf of a user. It combines LLM planning with browser automation and strict safety controls.

Example user goal:

> "Check whether my latest Amazon order has been delivered."

## Architecture (Planner → Skills → Executor → Observation)

Argus now uses a modern operator-agent loop:

```text
User Request
   ↓
Planner (LLM)
   ↓
Skill Selection
   ↓
Executor (Playwright)
   ↓
Structured Observation
   ↓
Planner (next step)
```

### Components

- **Planner (`app/planner/`)**
  - Decides the next high-level skill.
  - Never contains browser operations.
- **Skills (`app/skills/`)**
  - High-level site operations like `login_amazon`, `open_orders_page`, `extract_order_status`.
  - Encapsulate workflow behavior while delegating low-level operations.
- **Executors (`app/executors/`)**
  - Low-level interaction layer (`BrowserExecutor`).
  - No task-specific business logic.
- **Safety (`app/safety/`)**
  - Enforces domain allowlist/blocklist, max step limits, destructive-action confirmation policy.
- **Credentials (`app/credentials/`)**
  - Composite secret retrieval from keyring/env providers.
  - No credentials in business logic.
- **Observability (`app/models/audit.py`)**
  - Per-step structured audit records:
    - timestamp
    - planner decision
    - selected skill
    - arguments
    - resulting observation
    - error (if present)

## Running Argus in an Isolated Environment

**Recommended setup for a fresh VM**

1. Create a dedicated VM (no personal sessions).
2. Use low-privilege accounts only.
3. Restrict egress network to needed domains.
4. Store credentials in keyring when possible.

### Fresh VM quickstart (Ubuntu-like)

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv git

git clone <your-repo-url> argus
cd argus

python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
playwright install chromium
```

## Configuration

```bash
cp .env.example .env
```

Required:

- `ARGUS_OPENAI_API_KEY`
- `ARGUS_ALLOWED_DOMAINS`

Important safety settings:

- `ARGUS_BLOCKED_DOMAINS`
- `ARGUS_MAX_AGENT_STEPS`
- `ARGUS_HEADLESS`

## Credential Storage

No credentials are hardcoded.

### Option A (recommended): OS keyring

```bash
python -m keyring set argus amazon.username
python -m keyring set argus amazon.password
```

### Option B: environment variables (development convenience)

- `ARGUS_AMAZON_USERNAME`
- `ARGUS_AMAZON_PASSWORD`

## CLI Usage

Show runtime config (secrets redacted):

```bash
argus show-config
```

List planner-available skills:

```bash
argus list-skills
```

Run Amazon task:

```bash
argus run-amazon-task "Check whether my latest Amazon order has been delivered"
```

Run with overrides:

```bash
argus run-amazon-task "Check latest order" --headed --max-steps 15
```


## Security Hardening

Recent hardening work adds stricter controls across planning, execution, and auditing:

- **Strict domain validation** now allows only exact allowlist domains or their subdomains (for example: `amazon.com`, `www.amazon.com`, `orders.amazon.com`). Substring matches like `evilamazon.com` are rejected.
- **Structured planner outputs** are schema-validated (`skill`, `arguments`, `reasoning`, `done`) with skill-name validation, argument-type checks, malformed-response logging, and one retry on parse/validation failure.
- **Safer execution model** wraps Playwright failures in controlled runtime errors so skills can return structured failure observations instead of crashing the loop.
- **Improved skill robustness** centralizes Amazon selectors with fallbacks and validates element presence before extraction.
- **Step-level JSON trace logs** include timestamp, planner decision, skill, arguments, result, and error for each iteration.

## Known Limitations

- Amazon UI changes can break selectors.
- CAPTCHA/MFA may require manual intervention.
- LLM output remains probabilistic.

## Security Considerations

See [SECURITY.md](SECURITY.md) for operational guidance.
