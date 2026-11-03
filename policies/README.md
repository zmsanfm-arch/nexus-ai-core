# Policy enforcement

The application-level `GovernanceService` is a demonstrator only.
Before production, implement a separately deployed policy decision point
(e.g. OPA), enforce policy at every execution gateway, and deny by default.
Agents and model outputs must never be treated as authorization.
