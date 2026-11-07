# Session isolation policy

`SessionAccessPolicy` is an authorization primitive for future session and memory APIs.
It is not yet wired into persistence or request routes; do not treat it as an active
runtime boundary until every read/write path invokes it.

Rules:
- Principal ownership is mandatory for every access.
- The owning agent can read and write its own session.
- Other agents are denied by default.
- Cross-agent read requires an exact `(owner_agent_id, reader_agent_id)` grant.
- Cross-agent writes remain denied, even when cross-agent reads are granted.
- Invalid or missing identifiers fail closed.

Before runtime use, persist immutable session ownership, enforce the policy in every
repository method (not only API routes), add tenant-scoped artifact references, and
test concurrent access and revocation. Never put credentials or raw secret values in
session memory.