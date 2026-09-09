# Anonymous Supplementary Website

This directory contains the anonymous supplementary website for double-blind review.
It is a static HTML page with local media assets and does not include repository history,
author names, affiliations, personal links, or external project links.

## Local preview

```bash
python3 -m http.server 3456
```

Then open <http://localhost:3456/> from this directory.

## Anonymous deployment

Publish the contents of this directory to a new repository or static host whose name,
custom domain, commit history, and account metadata do not identify the authors.
Do not add a README, CNAME file, analytics configuration, or links to the camera-ready
repository until the review period is over.

The page intentionally keeps links to the paper, code, notebook, and social post as
non-link placeholders during anonymous review. Restore those destinations only after
double-blind review has ended.
