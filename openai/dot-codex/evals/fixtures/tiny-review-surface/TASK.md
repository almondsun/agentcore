# tiny-review-surface

Treat `review_surface.patch` as the full diff under review.

This fixture is shared by:

- `orchestrated-review`
- `reviewer`
- `security-auditor`

What the diff intentionally mixes:

- untrusted input parsing
- path construction from parsed data
- subprocess execution with shell interpolation
- sensitive logging
- weakened tests

What a strong run should do:

- use findings-first output
- keep security findings concrete
- call out weak or missing validation evidence
- avoid spawning specialists that the changed surface does not justify
