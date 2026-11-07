# NEXUS Visual Intelligence & Personal Knowledge

## Status
Approved architecture; implementation is staged behind the core platform governance and tenancy foundations tracked in Issue #39. This document does not claim that Instagram connectivity or media processing is implemented.

## Objective
Let a user capture, organize, search, compare, and analyze visual references from Instagram and other sources inside NEXUS, using the user's own labels and collections as first-class knowledge metadata.

## Product behavior
- Capture an Instagram post or reel through the native Share flow into a NEXUS-owned inbox.
- Accept a user-provided post URL, image, video, or archive import where the source permits it.
- Preserve source URL, capture time, user/tenant ownership, collection labels, user tags, and provenance.
- Extract available caption/text, OCR, video keyframes, and media metadata.
- Generate embeddings for text and visual representations; support hybrid lexical and semantic retrieval.
- Classify content into user-defined collections and NEXUS workspaces, with user confirmation for uncertain classifications.
- Find visually or semantically similar references and compare them against saved design constraints.
- Produce traceable reports with references to the original captured items.
- Support deletion, reprocessing, export, and tenant-scoped retention controls.

## Instagram integration strategy

### Primary path: explicit share-to-NEXUS capture
Use Instagram's native Share action to send a post/reel link to a NEXUS capture endpoint or mobile share target. The user explicitly selects the content. The capture service stores the submitted URL and any media/metadata actually supplied by the client, then enriches it only through permitted and available mechanisms.

### Backfill path: user-provided export
Allow users to upload an Instagram account export. Treat it as an index/backfill source, not as proof that media bytes or full captions are present. Resolve each item only when the user supplies the media or an authorized retrieval path is available.

### Official API path
Use Meta's official APIs only for supported professional-account and public-content use cases, with the required account type, scopes, review, and user authorization. Do not represent these APIs as exposing personal Saved posts or private Saved Collections.

### Optional browser-assisted capture
A browser companion may be evaluated as a user-visible, consent-based capture mechanism for content already rendered in the user's authenticated browser session. It must not collect passwords, bypass access controls, silently scrape private endpoints, or transmit session cookies to NEXUS. This path is optional and must pass policy, security, and compatibility review before release.

### Explicit non-dependency
Do not make the platform depend on reverse-engineered Instagram private endpoints or unofficial login automation. Such integrations are brittle, can break without notice, and can expose the user's account to restrictions.

## Logical architecture
1. Capture adapters — share target, manual URL/file upload, export importer, and approved API adapters.
2. Ingestion service — validates inputs, assigns tenant/principal ownership, records provenance, deduplicates by source identity and content hash, and queues processing.
3. Media processing — safe file validation, malware scanning where available, image normalization, video keyframe extraction, OCR, caption/text extraction, and metadata parsing.
4. Enrichment pipeline — multimodal embeddings, user-label-aware classification, entity/tag extraction, and similarity indexing.
5. Knowledge store — durable source records, media references, collection membership, annotations, embedding model/version metadata, and provenance.
6. Retrieval service — tenant/ACL-filtered hybrid lexical, metadata, and vector retrieval; lexical fallback when vector infrastructure is unavailable.
7. Mission tools — bounded read-only tools for collection inspection, similarity search, comparison, and report generation.
8. Governance and audit — policy checks at every tool boundary, explicit approval for external side effects, and immutable audit events.

## Data model (initial)
- visual_sources: tenant_id, owner_principal_id, source_type, canonical_url, source_platform, source_item_id, captured_at, provenance, status.
- visual_assets: source_id, asset_type, storage_key, mime_type, byte_size, checksum, duration, dimensions, processing_status.
- visual_collections: tenant_id, owner_principal_id, name, description, created_at.
- visual_collection_items: collection_id, source_id, user_label, sort_order, added_at.
- visual_annotations: source_id, author_principal_id, annotation_type, value, confidence, created_at.
- visual_embeddings: source_id or asset_id, modality, model_id, model_version, vector_ref, created_at.

All records and retrieval operations must enforce tenant and principal authorization. Do not expose storage keys or private source data across tenants.

## Safety, privacy, and operational requirements
- Treat captions, OCR text, image text, and imported metadata as untrusted input, never as system instructions.
- Do not execute links, scripts, QR destinations, or embedded instructions found in media.
- Enforce file size, MIME/type, duration, and decompression limits before processing.
- Keep credentials and browser session material out of the ingestion pipeline.
- Store only media and metadata the user is authorized to provide or that an approved API supplies.
- Apply retention, deletion, export, and reprocessing consistently to source records, derived assets, and embeddings.
- Redact secrets and private media URLs from logs.
- Use idempotent jobs, bounded concurrency, retry limits, and dead-letter handling.
- Keep all collection search and mission tools read-only by default.

## Suggested user-facing commands
- "Inspect my NEXUS chain collection."
- "Find saved references for stainless-steel necklaces."
- "Show designs that could be made with 2 mm wire."
- "Compare this reference with the previous six-fold designs."
- "Find visually similar items and explain the differences."
- "Sort these captured references into my NEXUS collections."

## Delivery sequence
1. Define contracts and tenant-scoped persistence after governance and identity foundations.
2. Implement capture inbox and manual media/URL ingestion with provenance.
3. Implement safe image/video processing and OCR.
4. Add embedding abstraction and hybrid retrieval with lexical fallback.
5. Add collection management and user-confirmed classification.
6. Add read-only mission tools and traceable reports.
7. Add Instagram export importer and validate real export formats.
8. Evaluate official Meta API use cases and optional browser-assisted capture separately.
9. Run tenant-isolation, authorization, file-safety, deletion, retry/replay, and end-to-end tests.

## Acceptance criteria
- A user can share a supported post/reel link or upload media into a tenant-scoped NEXUS inbox.
- Each captured item retains provenance and user-defined labels.
- Image, video, OCR, and text processing produce inspectable status and errors.
- Search combines semantic and lexical results without crossing tenant boundaries.
- Similarity results include source references and explainable matching signals.
- Uncertain classification is presented for user confirmation rather than silently moving content.
- Deletion removes or invalidates derived searchable representations according to retention policy.
- Processing is idempotent and bounded under retries and parallel workloads.
- No unsupported claim is made that Meta's official API exposes personal Saved Collections.
- All external actions remain blocked unless a centralized governance policy explicitly authorizes them.
