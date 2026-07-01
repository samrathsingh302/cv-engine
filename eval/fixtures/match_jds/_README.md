# match_jds fixtures — FICTIONAL

> **Every file in this directory is fictional and synthetic.** No real person, no
> real company, no real job. These are the P7 done-gate inputs:
> five `/match-jds` *match manifests* for an invented final-year CS student against
> five invented JDs, captured as data so `cv_builder/helpers/match_jds.py` can be
> tested deterministically — exactly as `eval/fixtures/scores/` is for the eval
> suite. They contain ZERO owner data and are never used in a real run.

The set is built so the ranker has an unambiguous correct order — an obvious easy
pairing must rank above an obvious hard one (the gate):

| id | invented company / role | designed projected band |
|----|-------------------------|-------------------------|
| `bytework_backend_placement` | Bytework — backend Python placement | top (easy: strong KB overlap) |
| `lumen_fullstack_intern` | Lumen — full-stack internship | upper-middle |
| `meridian_data_grad` | Meridian — data-engineering grad scheme | middle |
| `harborlight_frontend_intern` | Harborlight — front-end internship | lower-middle |
| `corewell_embedded_firmware` | Corewell — embedded firmware engineer | bottom (hard: no overlap) |

`test_match_jds.py` asserts `bytework_backend_placement` ranks first and
`corewell_embedded_firmware` ranks last, that the projected totals are strictly
decreasing across the five, and that the rendered report fits the one-page budget.
