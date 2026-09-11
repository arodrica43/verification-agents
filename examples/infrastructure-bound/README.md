# Infrastructure-bound certificate demo (Demo B)

Lean seed theorem: `InfrastructureBound.demand_le_capacity_implies_within_bound`.

```bash
cd lean/examples/infrastructure-bound
lake build
```

Trust boundary: the theorem is about a formal load model (`demand ≤ capacity`).
It does not by itself prove that live telemetry matches `LoadState`.
