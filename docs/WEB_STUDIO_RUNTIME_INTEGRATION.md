# Web Studio runtime integration — implementation notes

This increment adds two concrete adapters and the mission evidence path:

- `OfflineDockerBuild` packages a validated local website context and sends it to Docker as a tar stream. Builds use `--network=none`, `--pull=false`, `--no-cache`, bounded memory/CPU and a digest-pinned local base-image allowlist. It never starts, pushes or deploys the resulting image.
- `BrowserTesterHandler` accepts a trusted browser-runner adapter, validates its report and screenshot payloads, and stores each screenshot plus the machine-readable report in the principal-scoped Artifact Store with mission metadata.
- The mission worker now passes the owning principal to specialist context and stores a bounded final mission report artifact after node execution. Existing per-node artifact persistence remains in place.
- Central permission policy now declares a distinct permission for each of the 21 Web Studio capabilities. A policy entry is not a grant: manifests remain disabled with empty permission lists, and the worker still requires registered status, a matching capability, a granted permission, and an installed handler.

## Activation boundary

This increment does not enable the 21 agents or claim that a production browser runtime is installed. A deployment must inject a reviewed Playwright runner that executes in a disposable browser container with explicit egress restrictions, configure the pinned Docker build image allowlist, and register handlers only after CI and security review. The existing mission worker is sequential; the DAG's dependency order is enforced, but parallel execution is not claimed.

Production deployment, DNS/TLS, production secrets and external network access remain outside this adapter. Browser evidence is immutable and principal/mission-scoped; the Artifact Store root must be mounted on persistent storage and included in encrypted backup/restore drills.
