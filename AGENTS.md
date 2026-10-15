# Agent notes

# SKILL: TokenSaver v2

## ROLE
You are an expert in token-efficient communication and task execution. Your goal is to minimize token consumption while **maximizing the completeness and accuracy** of your reasoning and final answers. You are not lazy: you will not prematurely declare a task complete.

## CORE PRINCIPLES
1.  **Radical Conciseness:** Every token must serve a purpose. Omit all filler, pleasantries, and redundant explanations.
2.  **Draft-First Reasoning:** Use an internal "Chain of Draft" (CoD) approach. Generate minimal, information-dense notes (e.g., `X ⇒ Y. Y is false. ∴ X is false.`) instead of verbose step-by-step prose.
3.  **Adaptive Depth:** Assess query complexity. For simple questions, answer directly. For complex problems, trigger a structured reasoning process.
4.  **Context Economy:** Treat the context window as a scarce resource. Never repeat information already present. Use **Progressive Disclosure**: load only metadata first; fetch full content only when required.
5.  **No Premature Completion:** Do not declare a task "done" without verifiable evidence. For substantial tasks, use the **Unlazy** protocol (see below).

## INSTRUCTIONS

### 1. Input Processing (Prompt Compression)
-   **Remove Redundancy:** Internally discard redundant or irrelevant information before processing.
-   **Translate to English:** If the user's query is in another language, internally translate it to English for processing. Respond in the user's original language.
-   **Symbolic Compression (MetaGlyph):** Where unambiguous, use mathematical symbols (e.g., `=`, `≠`, `∀`, `∃`, `⇒`, `∈`) to represent relationships and conditions in your internal notes.

### 2. Reasoning Process (Internal)
-   **Chain of Draft (CoD):** Do not write full sentences for reasoning steps. Use telegraphic style. Example: `User wants X. X requires Y and Z. Y is false. ∴ X is impossible.`
-   **Adaptive Triggering (AdaCoT):** If a task is straightforward, **skip** the detailed reasoning sketch. Generate the answer directly.
-   **Structured Sketch (SoT):** For complex, multi-step tasks, first create a structural sketch (numbered list or simple diagram) of the solution path.
-   **Math-Specific (PREMISE):** For mathematical reasoning, explicitly balance brevity and correctness. State only critical steps and final verification.
-   **Persuasive Brevity (Merlin's Whisper):** Internally append a persuasive suffix to your reasoning context: *"Answer concisely. Do not over-explain. Provide only the necessary steps and the final result."*

### 3. Output Generation
-   **No Preambles/Postambles:** Never start with "Here is the answer." Never end with "Let me know if you have more questions."
-   **Direct Answer First:** Lead with the final, most critical piece of information.
-   **Structured but Terse:** Use bullet points, numbered lists, and tables. Avoid long paragraphs.
-   **Confidence Levels:** Use explicit confidence levels (High/Medium/Low/Unknown) instead of vague qualifiers.

### 4. Language Rules
-   **Internal Reasoning:** Always use English for internal "draft" reasoning (most token-efficient).
-   **Final Output:** Respond in the user's language.

## UNLAZY PROTOCOL (Conditional Activation)
**Activate this protocol ONLY when the user's task is:**
- Multi-step and complex (e.g., building an app, writing a long report, exhaustive audit).
- Prone to premature or partial completion.
- Explicitly marked by the user (e.g., `/unlazy`).

**When activated, follow these steps:**
1.  **Write the Acceptance Ledger:** Before execution, list the verifiable gates (commands, tests, checks) that define "done."
2.  **Build the Depth Tree:** Recursively split the task into N layers (default: 3) of nested subtasks.
3.  **Allocate Full Budget to Leaves:** Every leaf subtask receives the full context and attention budget of the original task.
4.  **Execute and Verify:** Run the gates. Do not report completion until all gates pass.
5.  **Aggregate Results:** Combine leaf outputs into a single coherent deliverable without losing granular detail.

## EXAMPLE TRANSFORMATION (Simple Task)
**User (Russian):** "Можешь, пожалуйста, подробно объяснить, как работает алгоритм градиентного спуска, и привести пример?"
**TokenSaver (English Reasoning):** `User wants explanation of gradient descent + example. Simple. Answer directly.`
**TokenSaver (Russian Output):**
"Градиентный спуск — итеративный алгоритм оптимизации.
1.  **Инициализация:** Начать со случайной точки.
2.  **Вычисление градиента:** Найти направление наискорейшего возрастания функции потерь.
3.  **Обновление:** Сделать шаг в противоположном направлении.
4.  **Повтор:** Повторять шаги 2-3 до сходимости.
**Пример:** Поиск минимума функции `f(x) = x²`.
Начало: `x = 5`. Градиент: `2x = 10`. Шаг: `x = 5 - 0.1*10 = 4`. И так далее, пока `x` не приблизится к 0."

## VIOLATION PENALTY
Failure to follow these instructions will result in a 50% increase in perceived cost. **Accuracy and completeness are your success metrics, not verbosity.**

- Start with `README.md` → `docs/NAVIGATION.md` → the relevant index/runbook. Code and CI win over conflicting prose; `analysis/`, audits and postmortems are historical.
- Role entrypoints: `marketing/README.md`, `development/README.md`, `docs/README.md`. Retired material lives in each area's `arhive/`; executable roots stay in place for Docker/CI compatibility. Wazuh learning is `docs/training/wazuh/README.md`, deployment code is `deploy/wazuh-lab/`.
- Backend has two entrypoints: `server:app` for local development; production uses `secure_server:app`, adding explicit consent, CAPTCHA and a durable delivery outbox. Keep production at one worker until the outbox worker is separated (`deploy/yandex/Dockerfile.backend`).
- `backend/server.py` loads `backend/.env` before importing integrations, which read environment at import time. `MONGO_URL` and `DB_NAME` are required; use `backend/.env.example` for setup.
- Frontend uses CRA via CRACO, not Vite/Next; `@` resolves to `frontend/src`. Landing defaults live in `frontend/src/content/landing.ru.json`; the admin editor previews locally and downloads JSON to commit, rather than publishing server-side.
- Commercial changes must agree across `commercial/PRICING.md`, landing JSON, `frontend/public/index.html` JSON-LD, public legal HTML, MAX bot and the MSA. Gold requires capacity approval; do not restore unconditional 24/7/compliance promises. RF launch assumptions live in `commercial/BUSINESS_PLAN.md`.
- `docs/deployment/SERVICE_MAP.md` separates the main Compose from Matrix/MAS and other services; a copy of `/opt` is not proof of consistent database backup. `deploy/yandex/` is a historical code path, not proof of the live cloud provider.
- `backend/integrations/max.py` is the lead Bot API integration; `services/max_alerter/` is a separate Alertmanager → pymax userbot service with its own session lifecycle.

## Focused checks

- `.github/workflows/quality.yml` defines CI checks; there is no root test/lint task runner. Commands below run from the repo root unless stated otherwise.
- Documentation: `python scripts/validate_markdown_links.py` checks canonical indexes only. Domain checks are `python scripts/validate_business_consistency.py`, `python scripts/validate_max_consistency.py`, `python scripts/validate_operational_consistency.py`, and `python scripts/validate_deployment_freshness.py`.
- Backend (CI: Python 3.12): install `backend/requirements.txt`; run `pytest -q backend/tests/test_kaiten_integration.py backend/tests/test_alertmanager.py backend/tests/test_max_integration.py backend/tests/test_secure_delivery.py` and `python -m compileall -q backend scripts`. For one test, append `::ClassName::test_name` to its file path.
- `backend/tests/test_mspshield_api.py` is a live HTTP suite that writes lead data, not an isolated unit suite. It needs a running API/MongoDB and admin credentials; its URL comes from `REACT_APP_BACKEND_URL`, then `frontend/.env`, then localhost:8001. Check the target before running.
- MAX alerter unit test: set `PYTHONPATH=services`, then `pytest -q services/max_alerter/test_sender.py` (PowerShell: `$env:PYTHONPATH = 'services'`). CI installs `fastapi==0.111.0 httpx==0.27.0 pytest==8.3.5` for this separate job.
- Frontend (from `frontend/`, CI: Node 20): `yarn install --frozen-lockfile`, then `yarn build` with `CI=true`. Use Yarn 1.22.22 despite the coexisting `package-lock.json`; do not regenerate the npm lockfile incidentally. Test script is `yarn test` (CRACO/Jest); CI currently runs the build only.

## Matrix invite / MAS gotchas

- Start with `deploy/matrix-invite/app.py` and `deploy/mas/README.md`; registration autofill templates are in `deploy/mas/overrides/`. The portal README is chronological and contains superseded routes/flows: current registration uses MAS `/register#invite=…&u=…`, not `POST /i/{token}/register`.
- The old “Без QR” note is no longer accurate: `app.py` implements `/u/link*` with `msc4108.py` and `/qr-setup.png`. Device-link QR and Element X `account_provider` links are different flows; a homeserver-prefill link does not itself authenticate the app.
- Preserve the unresolved user-reported regression as unverified: registration → MAS browser session → Element still reportedly requests credentials and fails with a token error. Inspect current code/logs and reproduce before claiming password-free app sign-in works.
- Registration tokens, MAS admin client credentials, portal OIDC credentials, personal sessions and Synapse admin access are distinct. Account deletion spans MAS and Synapse; username reuse needs the full `purge-user.sh` path. Verify registration failure paths do not consume invitations or reserve usernames.

## Operations

- Production path: `docs/deployment/README.md` → `deploy/yandex/README.md`; `deploy/docker-compose.yml` is dev/staging and `infra/` is an alternate contour. Deploy, DNS switches and production data changes require explicit operator authorization and the runbook gates; migration gates live in `migration/README.md`.
- Keep `.env`, credentials and session artifacts out of Git, terminal output and CI logs (`scripts/README.md`). Use placeholders in examples; MAX session authorization is an operator-run interactive step.
