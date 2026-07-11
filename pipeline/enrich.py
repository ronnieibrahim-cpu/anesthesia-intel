"""Lawful open-access enrichment: Unpaywall (by DOI) + PubMed Central ELink (by PMID).

STUB — implemented in M1 Step 4.

Design decided now:
- For every item with a DOI, query Unpaywall (requires the UNPAYWALL_EMAIL env var —
  their API asks for a contact email, no key). For items with a PMID, query NCBI ELink
  for a PMC version.
- If a legal OA copy exists, store its link in `items.oa_url` and the provenance in
  `items.oa_source` ('unpaywall' | 'pmc'); the digest shows it as "Free full text".
- This is the ONLY full-text mechanism in the project. No paywall circumvention of
  any kind, ever (CLAUDE.md rule 2).
"""


def enrich(items):
    """Attach oa_url/oa_source to item rows where a lawful open-access copy exists."""
    raise NotImplementedError("Implemented in M1 Step 4 (Unpaywall/PMC enrichment).")
