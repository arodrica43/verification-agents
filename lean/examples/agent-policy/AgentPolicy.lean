/-!
# Agent Policy — privileged action authorization

Demo theorem for the Formal Platform Phase 1 trust anchor.

We model a minimal system state where a privileged action may execute only when
authorization holds. The theorem states: if the policy is satisfied and a
privileged action executed, then the principal was authorized.

No `sorry` / `admit`.
-/

namespace AgentPolicy

/-- Principal identity (opaque for the demo). -/
structure Principal where
  id : String
  deriving DecidableEq, Repr

/-- Minimal system state for authorization reasoning. -/
structure SystemState where
  actor : Principal
  authorized : Bool
  privilegedActionExecuted : Bool
  deriving Repr

/-- Policy is satisfied when authorization flag matches execution requirements. -/
def policySatisfied (s : SystemState) : Prop :=
  s.privilegedActionExecuted → s.authorized = true

/-- Convenience: actor is authorized. -/
def authorized (s : SystemState) : Prop :=
  s.authorized = true

/--
If the policy is satisfied and a privileged action was executed,
then the actor was authorized.
-/
theorem privileged_action_requires_authorization
    (s : SystemState)
    (hpolicy : policySatisfied s)
    (hexec : s.privilegedActionExecuted = true) :
    authorized s := by
  unfold authorized policySatisfied at *
  exact hpolicy hexec

/-- Corollary: executing a privileged action under a satisfied policy implies authorization. -/
theorem exec_implies_authorized_under_policy
    (s : SystemState)
    (h : policySatisfied s ∧ s.privilegedActionExecuted = true) :
    authorized s := by
  exact privileged_action_requires_authorization s h.left h.right

end AgentPolicy
