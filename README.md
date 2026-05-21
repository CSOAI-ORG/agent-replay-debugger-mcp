# Agent Replay Debugger MCP

> ## 🧱 Part of the MEOK A2A Substrate (£499/mo)
> See [meok.ai/a2a](https://meok.ai/a2a).

# Step-debug an agent run — deterministic replay + signed audit evidence

<!-- mcp-name: io.github.CSOAI-ORG/agent-replay-debugger-mcp -->

[![PyPI](https://img.shields.io/pypi/v/agent-replay-debugger-mcp)](https://pypi.org/project/agent-replay-debugger-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What this does

Record every action an agent takes (inputs, outputs, timestamps, costs) so you can REPLAY the run deterministically afterward. Step through each action like a debugger. Filter, search, branch from any step. Sign the recording for audit evidence.

Pairs with `bft-progress-council-mcp` (real-time loop halting) and `agent-audit-logger-mcp` (audit-chain submission).

## Tools

| Tool | Purpose |
|---|---|
| `start_recording(goal, session_id?, agent_id?)` | Open new recording |
| `record_step(session_id, action, input?, output?, model?, tokens?, ms?)` | Log one step |
| `replay_step(session_id, step_idx)` | Re-fetch a step |
| `timeline(session_id, model_filter?, tag_filter?)` | Full ordered timeline |
| `branch_from(session_id, step_idx, new_action)` | Alternative branch |
| `search_steps(session_id, query)` | Free-text step search |
| `export_recording(session_id, format)` | JSON or markdown export |
| `sign_recording(session_id)` | HMAC-sign for audit submission |

## Use cases

- Debug why an agent burned £20 on a £0.50 task
- Reproduce a customer-reported wrong-answer bug
- Audit evidence: prove what an agent did, to whom, when
- Train next-gen agents on senior-agent traces
- Forensic post-mortems after prompt-injection incidents

## Sister MCPs

- `bft-progress-council-mcp` — real-time loop halt
- `agent-token-budget-mcp` — spend cap
- `agent-audit-logger-mcp` — audit-chain submission
- `agent-cost-allocator-mcp` — multi-tenant chargeback

Full catalogue: [meok.ai/anthropic-registry](https://meok.ai/anthropic-registry)

## Pricing

| Option | Price |
|---|---|
| Self-host MIT | £0 |
| Universal PAYG | £29/mo + £0.0002/call |
| A2A Substrate | £499/mo |
| Universe | £1,499/mo |
| Defence | £4,990/mo |

Buy: https://meok.ai/a2a

## Licence

MIT. By [MEOK AI Labs](https://meok.ai) (CSOAI LTD, UK Companies House 16939677).
