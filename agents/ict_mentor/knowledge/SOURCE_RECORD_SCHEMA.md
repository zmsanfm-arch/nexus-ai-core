# Knowledge Source Record Schema

This schema defines metadata for ICT Mentor's private retrieval index. It stores provenance and concise derived notes; it is not a license to copy or redistribute protected source material.

## Required source record

```json
{
  "source_id": "ict-youtube-unique-id",
  "title": "Original source title",
  "creator": "Michael J. Huddleston / ICT",
  "canonical_url": "https://www.youtube.com/watch?v=...",
  "source_type": "video",
  "publication_date": null,
  "retrieved_at": "YYYY-MM-DD",
  "language": "en",
  "playlist_or_course": null,
  "rights_and_access_note": "Public metadata; caption access/reuse basis recorded here",
  "segments": [
    {
      "segment_id": "source-id-0001",
      "start_timestamp": "00:00:00",
      "end_timestamp": "00:00:00",
      "original_terms": ["Market Structure Shift"],
      "concept_tags": ["market_structure_and_displacement"],
      "concise_summary": "Short factual summary in original wording.",
      "evidence_type": "source_statement",
      "transcript_confidence": "verified",
      "related_source_ids": []
    }
  ]
}
```

## Controlled values

- `source_type`: `video`, `official_course`, `permitted_transcript`, `user_note`, `chart_example`, `secondary_reference`.
- `evidence_type`: `source_statement`, `visual_observation`, `editorial_summary`, `user_rule`, `secondary_claim`.
- `transcript_confidence`: `verified`, `review_required`, `unavailable`.
- `source_confidence` on retrieval: a calibrated retrieval/evidence indicator, not a claim that a trading setup will succeed.

## Separation requirements

1. Official ICT source statements must never be mixed with user-specific trading rules.
2. User chart annotations and decisions are stored as user material, with user-provided date/context.
3. Secondary interpretations remain explicitly secondary.
4. Every factual claim attributed to ICT must resolve to a source record and timestamp.
5. If timestamp, wording, or source ownership is uncertain, mark it as unverified and do not state it as ICT doctrine.

## Ingestion workflow

1. Register official channel/course metadata and canonical links.
2. Record whether captions/transcripts are available through permitted access or supplied by the user.
3. Segment by coherent teaching topic while retaining exact timestamps.
4. Produce concise summaries and normalized concept tags; preserve original ICT terminology.
5. Run duplicate detection and cross-link related segments.
6. Human-review ambiguous terminology, speech recognition, and chart-dependent explanations.
7. Run retrieval tests for common concepts and adversarial questions that invite fabricated attribution.
8. Version every source record and make ingestion idempotent.

## Initial retrieval evaluation set

Create test questions for:
- definition requests (e.g. FVG, MSS, dealing range);
- distinctions between related concepts;
- exact source/timestamp lookup;
- conflicting or ambiguous explanations;
- questions with no evidence in the collection;
- user-specific rule questions where no user rule has yet been supplied.

Expected behavior for unsupported questions: state that the source collection does not establish the answer, ask for a source/chart only if necessary, and do not fill the gap with invented ICT doctrine.
