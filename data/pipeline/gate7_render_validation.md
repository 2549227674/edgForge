# Gate 7 — Gemma 4 native rendering validation

- Scope: deterministic M0 sample only; full mix rendering is deferred to M1.
- Template: `models/gemma-4-E4B-it/chat_template.jinja`
- Template SHA-256: `0a2c8073c878ab1da004bee933a998606537bbb62016310352c7285c3f01c5b5`
- Rendering options: `enable_thinking=true`, `preserve_thinking=true`, `add_generation_prompt=false`; tool schemas are passed through `tools`.
- Selection: source-stratified multi-assistant tool trajectories whose source reasoning fields satisfy the frozen template's `thinking_gate`; each is bounded to 32,000 source-message characters so per-token review remains human-readable.
- Samples requested/rendered: 20/20; rendering failures: 0.
- Tokenizer byte-exact round trips: 20/20.
- Thinking integrity (all source reasoning fields present): 20/20.
- Tool-call samples: 20/20; multi-assistant-turn samples: 20/20.
- Tokens / masked target tokens: 101000 / 43746.

## Per-source coverage

| Dataset | Samples |
|---|---:|
| `AletheiaResearch__GLM-5.2-Agent` | 5 |
| `Crownelius__Complete-FABLE.5-traces-2M` | 7 |
| `armand0e__qwen3.7-max-pi-traces` | 2 |
| `lambda__hermes-agent-reasoning-traces` | 6 |

## Loss-mask convention

Mask 1 is assigned to assistant content, `<|channel>thought…<channel|>`, and `<|tool_call>…<tool_call|>` spans. System/tool declarations, user content, tool responses, and turn markers are excluded. A token that straddles a target boundary is conservatively assigned mask 1.

## Failures

None.
