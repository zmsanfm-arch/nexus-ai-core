# ICT Knowledge Collection

## Collection layout

Organize material by concept, not merely by playlist order:

- foundations_and_market_delivery
- dealing_ranges_and_bias
- liquidity_and_sweeps
- market_structure_and_displacement
- pd_arrays
- time_and_sessions
- entry_models
- trade_management
- mentorship_lessons
- user_strategy_profile

## Required metadata per source

Each source record should contain:

- `source_id`: stable internal identifier
- `title`
- `creator`: Michael J. Huddleston / ICT, or another clearly identified author
- `canonical_url`
- `source_type`: video, course, transcript, user_note, chart_example
- `publication_date`, if known
- `retrieved_at`
- `language`
- `playlist_or_course`, if applicable
- `segments[]`: segment id, start/end timestamps, concise content, concepts, and provenance
- `rights_and_access_note`

## Ingestion rules

1. Prefer the official ICT channel and official course materials.
2. Use captions/transcripts only where access and reuse are permitted, or where supplied by the user.
3. Keep timestamps attached to every extracted segment.
4. Normalize terminology without erasing the original term.
5. Deduplicate repeated lessons and cross-link concepts.
6. Mark uncertain speech recognition, unclear charts, and conflicting definitions.
7. Never treat third-party interpretations as direct ICT statements.
8. Do not publish or redistribute full copyrighted transcripts. Keep only the material needed for private retrieval where lawful; otherwise store links, metadata, short notes, and embeddings.
9. Re-ingestion must be idempotent and preserve source history.

## Retrieval output contract

Every retrieved passage should return:
`source_id`, `title`, `canonical_url`, `start_timestamp`, `end_timestamp`, `concept_tags`, `excerpt_or_summary`, and `source_confidence`.

A response must be able to show the source title and timestamp. If a source cannot be resolved, it must not be presented as a verified ICT teaching.
