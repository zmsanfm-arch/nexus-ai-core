# Web Studio runtime integration

## Implemented components

- `OfflineDockerBuild` validates website build contexts, rejects symlinks and sensitive paths, requires digest-pinned allowlisted base images, and runs `docker build` with `--network=none`, `--pull=false`, `--no-cache`, and CPU/memory/time/context limits. It never starts, pushes, or deploys the resulting image.
- Twenty-one Web Studio roles have distinct advisory system policies and a strict `SpecialistResult` contract. The handlers have no tools and cannot execute code, browse, modify files, publish, or deploy. The browser tester role is wired to the real browser adapter only when its runner and artifact store are configured.
- `BrowserTesterHandler` validates browser reports and screenshots and stores them under the mission principal in the immutable, hash-verified Artifact Store.
- `PlaywrightDockerRunner` starts a fresh, disposable browser container for each invocation. The browser runs read-only, non-root, with all Linux capabilities dropped, no-new-privileges, PID/memory/CPU limits, and a temporary filesystem.
- Each browser invocation creates a unique Docker-internal network, attaches only the approved egress proxy, starts the browser container, then disconnects and removes the network. Concurrent browser runs do not share an internal network.
- `browser_egress_proxy.py` supports HTTPS CONNECT only on port 443, checks an exact domain/subdomain allowlist, resolves DNS once, rejects non-public IP answers, and connects to the validated numeric IP to prevent DNS rebinding between validation and connection. The proxy is intended to be the only container on its dedicated external bridge network and on each ephemeral internal browser network.
- The mission worker registers the role-specific advisory handlers and the optional Playwright-backed browser tester. It still checks manifest status, capability, central permission, and handler availability before execution. All 21 manifests remain disabled and have no grants.
- The mission worker stores per-node outputs, browser report/screenshots, and the final mission report with principal-scoped artifact ownership.
- CI includes Python 3.11/3.12 tests, container/security checks, real Docker offline-build verification, and a real Playwright-in-container smoke/E2E test through the egress proxy.

## Browser runtime deployment contract

The dedicated `mission-worker` Compose service runs `app.mission_worker_entrypoint` and stores mission artifacts on the persistent `mission_artifacts` volume. It is separate from the generic advisory `worker` service. Start it with the `mission-worker` Compose profile after the operator has prepared the application environment.

The browser runtime is deliberately not enabled unless the operator configures all required values. Production worker containers do **not** mount the host Docker socket. The mission worker uses a dedicated browser Docker daemon over mutually authenticated TLS on TCP 2376; that daemon should run on a separate, disposable browser-execution host/VM with no production application workloads.

Required worker environment:

- `NEXUS_PLAYWRIGHT_IMAGE`: locally available browser image by immutable digest or image ID, built from `Dockerfile.playwright-runner`.
- `NEXUS_BROWSER_INTERNAL_NETWORK`: short prefix for per-run ephemeral internal Docker networks.
- `NEXUS_BROWSER_EGRESS_PROXY_URL`: `http://<proxy-container-name>:3128`.
- `NEXUS_BROWSER_EGRESS_PROXY_CONTAINER`: exact proxy container name.
- `NEXUS_BROWSER_ALLOWED_DOMAINS`: comma-separated DNS names approved by the operator.
- `NEXUS_BROWSER_DOCKER_HOST`: dedicated remote Docker endpoint, e.g. `tcp://browser-host.internal:2376`.
- `NEXUS_BROWSER_DOCKER_TLS_VERIFY=1` and `NEXUS_BROWSER_DOCKER_CERT_PATH`: directory containing `ca.pem`, `cert.pem`, and `key.pem`; mount it read-only at `/run/browser-docker-certs`. Compose exposes `NEXUS_BROWSER_DOCKER_CERTS_PATH` for the host-side mount source. The files must be readable by the non-root `nexus` container user through a dedicated group; do not make private keys world-readable.

On the dedicated browser Docker host:

1. Build `Dockerfile.browser-egress` and `Dockerfile.playwright-runner` with a digest-pinned Python base image. Make both images available locally on that host.
2. Create one dedicated external bridge network for the egress proxy. Run the egress proxy container only on that network with `NEXUS_EGRESS_PROXY_MODE=allowlist-v1` and `NEXUS_EGRESS_ALLOWED_DOMAINS` configured. Do not publish port 3128 to the host or public Internet.
3. Do not attach other containers to the proxy's external bridge network. At runtime, the runner verifies that the proxy is the only member of that network and that it is the only container on each ephemeral internal browser network.
4. The egress proxy must be the only route from the internal browser network to public destinations. It permits only allowlisted HTTPS CONNECT destinations and rejects private, loopback, link-local, multicast, reserved, and IP-literal destinations. The browser network itself is Docker-internal.
5. Use a dedicated TLS-protected Docker daemon and client certificates. Never mount `/var/run/docker.sock` into the application worker.

The runner refuses to activate if the image, remote TLS Docker endpoint/certificates, internal network prefix, proxy identity, or domain allowlist is missing. Browser runs fail closed if the Docker network topology or proxy image labels/environment do not match the expected policy.

## Activation and acceptance boundaries

- The 21 role manifests remain disabled with empty permissions. Installing a handler is not an authorization grant. Each role must receive a separate review and explicit manifest grant before it can execute through the central worker.
- The current worker is sequential. The DAG compiler validates dependencies; this increment does not claim parallel execution.
- The browser E2E test proves the browser -> screenshot/report artifacts -> mission worker -> final report path in CI. It is not a substitute for production-host network validation.
- CI security scanners and internal tests are not an independent security assessment. A reviewer who did not implement this code must assess the threat model, proxy, Docker daemon boundary, artifact isolation, and failure/recovery paths.
- PostgreSQL concurrency tests and the encrypted backup/restore drill run in CI. Mission artifacts now have separate encrypted backup and verified restore scripts; they reject symlinks, unsafe archive paths, non-regular files, ownership mismatches, and content-hash mismatches. Production load thresholds, real alert delivery, and a production recovery exercise still require the operator's isolated environment and monitoring endpoints.

## Mission artifact backup and restore

- Run `scripts/backup_mission_artifacts_encrypted.sh` with `NEXUS_ARTIFACT_ROOT`, `AGE_RECIPIENT`, and `BACKUP_DIR`. The encrypted archive and SHA-256 sidecar are written outside the artifact volume.
- Run `scripts/restore_mission_artifacts_drill.sh` with `BACKUP_FILE`, `AGE_IDENTITY_FILE`, an empty `NEXUS_RESTORE_ARTIFACT_ROOT`, and `NEXUS_RESTORE_CONFIRM=YES`. The script validates archive paths and artifact ownership/integrity before copying data into the empty target.
- CI generates a temporary age identity, creates a real Artifact Store entry, encrypts a backup, removes the source, restores into an empty directory, and reads the artifact back through `LocalArtifactStore`.
- Store the age identity separately from encrypted backups. The repository operator owns the recipient/identity lifecycle and off-host backup retention.
- Production secrets/key management, server provisioning, DNS, TLS certificates, and deployment are owned by the repository operator and are not acceptance gates for this code change.
- Live trading, external execution, image push, and automatic deployment remain disabled.
