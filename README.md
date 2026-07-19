# HomeRepairAgent

An AI-powered home repair assistant. A LangGraph agent (running on Amazon Bedrock / Nova) walks a
user through picking which home-repair project they're working on and then helps diagnose and fix
the issue, backed by a Postgres-based user/project store, a Bedrock Knowledge Base for reference
material (falling back to Tavily web search), and Amazon Bedrock Guardrails for content safety and
answer-quality checks.

## Architecture

Deployed as a set of AWS CDK stacks (see [bin/app.ts](bin/app.ts)):

- **VpcStack** — shared VPC for the Lambdas and databases.
- **RagDatabaseStack** — Aurora Postgres cluster (pgvector) backing the Bedrock Knowledge Base.
- **PdfBucketStack** / **KnowledgeBaseStack** — S3 bucket of reference PDFs and the Bedrock
  Knowledge Base built from them. Dropping a `.pdf` into the bucket auto-triggers a KB sync
  ([lambdas/trigger-kb-sync](lambdas/trigger-kb-sync)).
- **UserInfoDatabaseStack** — Postgres schema for users, projects, and saved conversations.
- **McpServerStack** — `homerepair-mcp-server` Lambda, a tool server (get/add/update user & project
  data) invoked over the Lambda `tools/call` protocol.
- **GuardrailStack** — an Amazon Bedrock Guardrail ([lib/guardrail-stack.ts](lib/guardrail-stack.ts))
  enforcing profanity filtering, PII protection, and a contextual grounding check on home_repair
  answers. See [Guardrails](#guardrails) below.
- **LangGraphAgentStack** — `langgraph-agent` Lambda, the conversational agent described below.
- **ApiStack** — API Gateway in front of the LangGraph agent Lambda, authenticated via JWT
  (Sign in with Apple).

## LangGraph agent conversation flow

Each API request is one turn: the graph runs exactly one node per invocation, returns a response,
and persists state (DynamoDB, 24h TTL) keyed by `sessionId` for the next turn.

```
START
  │
  ▼
initial_verification   (only on a brand-new session)
  │  looks up the user by Apple ID via the MCP tool `get_user_profile`,
  │  greets them and shows their default project
  ▼
orchestrator
  │  1st turn: asks "switch project, or home repair question?"
  │  2nd turn: classifies the reply — QUESTION / PROJECT / IRRELEVANT
  ├── QUESTION ──────────────► home_repair
  ├── PROJECT ───────────────► project_update
  └── IRRELEVANT ─────────────► re-asks (stays on orchestrator)
                                                │
project_update ◄────────────────────────────────┘
  │  lists the user's other projects (current default excluded), lets them
  │  switch or create a new one (`add_project` / `set_project_as_default`
  │  MCP tools), then hands off to home_repair
  ▼
home_repair
  │  gathers the specific issue (using any uploaded photo (S3) as context), and on the first
  │  turn for a new issue, opens with the project's last saved resolution (if any).
  │  When ready to answer: queries the Bedrock Knowledge Base first; if nothing scores above
  │  KB_RETRIEVAL_MIN_SCORE, falls back to a Tavily web search. The answer is then checked
  │  against that search context via the guardrail's contextual grounding check.
  ├── answer grounded in search results ─────► check_result
  └── no search needed, or search context failed the grounding check ─► stays on home_repair
                                                │
check_result ◄───────────────────────────────────┘
  │  asks "did that resolve it?" and classifies the reply, saving the resolution via the
  │  MCP tool `update_resolution`
  ├── YES ───────────────────────────► orchestrator (asks intent again)
  └── NO / UNCLEAR ──────────────────► home_repair (keep troubleshooting) / re-asks
  ▼
 END (response returned to the client; graph state saved for the next turn)
```

Node implementations live in [lambdas/langgraph-agent/nodes/](lambdas/langgraph-agent/nodes/):
`initial_verification.py`, `orchestrator.py`, `project_update.py`, `home_repair.py`,
`check_result.py`. The graph itself is wired up in [graph.py](lambdas/langgraph-agent/graph.py).

## Guardrails

The `GuardrailStack` ([lib/guardrail-stack.ts](lib/guardrail-stack.ts)) configures a single Bedrock
Guardrail with three policies:

- **Word filter** — the managed `PROFANITY` list.
- **Sensitive information** — `EMAIL`/`PHONE` are masked (`ANONYMIZE`); Social Security numbers,
  credit/debit card numbers, bank account numbers, passwords, and AWS access/secret keys are
  blocked outright. `NAME`/`ADDRESS` are intentionally *not* filtered — the app legitimately
  discusses project addresses and user names as part of normal conversation.
- **Contextual grounding check** — flags `home_repair` answers that aren't backed by the search
  context they were generated from (`GROUNDING`) or that don't address the user's question
  (`RELEVANCE`). Thresholds are `GUARDRAIL_GROUNDING_THRESHOLD` / `GUARDRAIL_RELEVANCE_THRESHOLD`
  in [lib/constants.ts](lib/constants.ts) (default `0.5`, range `0`–`0.99`).

Wiring differs by policy, since they attach to the model call differently:

- Word filter and sensitive-information checks run automatically on every LLM call — the guardrail
  ID/version are passed straight into `ChatBedrock` in
  [llm.py](lambdas/langgraph-agent/llm.py).
- The grounding check can't run that way (Bedrock needs the search context and user query tagged
  separately from the model's response). `home_repair.py`'s `_grounding_check` calls the
  standalone `ApplyGuardrail` API directly, after generating the answer, passing the search
  context as `grounding_source` and the user's question as `query`. If it fails, the response is
  replaced with the guardrail's blocked-output message and the turn skips `check_result` (no
  "did that resolve it?" — the agent isn't confident the answer is valid).

## Logging

Both Lambdas log to CloudWatch via the standard Python `logging` module, controlled by a
`LOG_LEVEL` environment variable (default `INFO`, set in the CDK stacks).

- **langgraph-agent**: logs each request/response, MCP tool calls, state transitions between
  nodes, and every Bedrock LLM call — including the exact prompt sent and the model's reply
  (image data is redacted, long content is truncated) — via a callback handler in
  [llm.py](lambdas/langgraph-agent/llm.py).
- **homerepair-mcp-server**: logs each `tools/call` request/result and every SQL statement sent to
  Postgres (fully interpolated, via a logging cursor in
  [db.py](lambdas/homerepair-mcp-server/db.py)).

## Development

```
npm install
npm run build   # compile TypeScript (CDK)
npm run synth   # cdk synth
npm run deploy  # cdk deploy
```

The `homerepair-mcp-server` Lambda has a unit test suite:

```
cd lambdas/homerepair-mcp-server
pip install -r requirements.txt -r requirements-test.txt
pytest
```
