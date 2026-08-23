## Summary

Describe the user-visible or maintainer-facing change.

## Motivation

Explain the problem this pull request solves and link any related issue.

## Testing

- [ ] `python3 -m compileall -q src tests`
- [ ] `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- [ ] Additional checks described below, if applicable.

## Documentation

- [ ] README, API specification, or relevant docs updated.
- [ ] No documentation change is needed.

## Compatibility and security

- [ ] This change does not break the documented API.
- [ ] Any breaking change is described below.
- [ ] I considered secrets, network access, untrusted page content, and data persistence.

## Notes

Add migration notes, limitations, or follow-up work that is explicitly outside this pull request.
