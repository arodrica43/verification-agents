# Agent Policy Certificate (Demo A seed)

This example packages a **manually authored** Lean theorem about privileged-action
authorization into a Formal Platform certificate bundle.

## Theorem

`AgentPolicy.privileged_action_requires_authorization` — if `policySatisfied` and a
privileged action executed, then `authorized`.

Proof contains **no** `sorry`.

## Bundle

Issuance **requires** an independent `lake build` by default:

```bash
python scripts/build_demo_certificate.py
uv run formal-cert verify examples/agent-policy-certificate/certificate-demo --lean
```

Offline scaffolding (records `verification.success=false`):

```bash
python scripts/build_demo_certificate.py --allow-unverified --skip-lean
```

## Trust boundary reminder

The certificate proves a property of the **formal model**. It does not by itself prove
that a live agent deployment satisfies `policySatisfied`.
