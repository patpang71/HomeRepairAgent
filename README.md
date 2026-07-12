# HomeRepairAgent

An AI-powered home repair assistant. A LangGraph agent (running on Amazon Bedrock / Nova) walks a
user through picking which home-repair project they're working on and then helps diagnose and fix
the issue, backed by a Postgres-based user/project store and a Bedrock Knowledge Base for reference
material.

## Architecture

Deployed as a set of AWS CDK stacks (see [bin/app.ts](bin/app.ts)):

- **VpcStack** — shared VPC for the Lambdas and databases.
- **RagDatabaseStack** — Aurora Postgres cluster (pgvector) backing the Bedrock Knowledge Base.
- **PdfBucketStack** / **KnowledgeBaseStack** — S3 bucket of reference PDFs and the Bedrock
  Knowledge Base built from them.
- **UserInfoDatabaseStack** — Postgres schema for users, projects, and saved conversations.
- **McpServerStack** — `homerepair-mcp-server` Lambda, a tool server (get/add/update user & project
  data) invoked over the Lambda `tools/call` protocol.
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
  │  gathers the specific issue, optionally searches the web (Tavily) for
  │  diagnostic help, and answers — using any uploaded photo (S3) as context
  ▼
 END (response returned to the client; graph state saved for the next turn)
```

Node implementations live in [lambdas/langgraph-agent/nodes/](lambdas/langgraph-agent/nodes/):
`initial_verification.py`, `orchestrator.py`, `project_update.py`, `home_repair.py`. The graph
itself is wired up in [graph.py](lambdas/langgraph-agent/graph.py).

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
