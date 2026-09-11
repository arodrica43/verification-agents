# Agent Policy Certificate (Demo A seed)

This example packages a **manually authored** Lean theorem about privileged-action
authorization into a Formal Platform certificate bundle.

## Theorem

`AgentPolicy.privileged_action_requires_authorization` — if `policySatisfied` and a
privileged action executed, then `authorized`.

Proof contains **no** `sorry`.

## Bundle

```bash
python scripts/build_demo_certificate.py
uv run formal-cert verify examples/agent-policy-certificate/certificate-demo
# With Lean:
uv run formal-cert verify examples/agent-policy-certificate/certificate-demo --lean
```

## Trust boundary reminder

The certificate proves a property of the **formal model**. It does not by itself prove
that a live agent deployment satisfies `policySatisfied`.
