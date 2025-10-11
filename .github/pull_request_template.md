## Description

<!-- Provide a clear and concise description of what this PR does -->

Fixes # (issue)

## Type of Change

<!-- Mark the relevant option with an 'x' -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Performance improvement
- [ ] Test addition/improvement
- [ ] CI/CD update
- [ ] Dependency update

## Changes Made

<!-- List the specific changes in this PR -->

-
-
-

## Testing

<!-- Describe the tests you ran to verify your changes -->

- [ ] Unit tests pass locally (`./scripts/run-tests.sh unit`)
- [ ] Integration tests pass (`./scripts/run-tests.sh integration`)
- [ ] Code quality checks pass (`pre-commit run --all-files`)
- [ ] Manual testing performed (describe below)

**Manual Testing Details:**
<!-- Describe any manual testing you performed -->

```bash
# Example commands run for testing
docker compose up -d
python scripts/publish-budget-alert-event.py --cost-amount 1200 --budget-amount 1000
```

## Configuration Changes

<!-- If this PR changes configuration format, provide before/after examples -->

**Before:**
```json

```

**After:**
```json

```

## Breaking Changes

<!-- If this is a breaking change, describe the impact and migration path -->

- [ ] This PR introduces breaking changes
- [ ] Migration guide added to CHANGELOG.md
- [ ] Documentation updated to reflect changes

**Migration Steps:**
<!-- If applicable, describe how users should migrate -->

1.
2.

## Documentation

<!-- Mark applicable items with an 'x' -->

- [ ] README.md updated (if applicable)
- [ ] CLAUDE.md updated (if applicable)
- [ ] CHANGELOG.md updated with changes
- [ ] Inline code comments added for complex logic
- [ ] Docstrings added/updated for new functions
- [ ] OpenTofu module documentation updated (if applicable)

## Security Considerations

<!-- Describe any security implications of this PR -->

- [ ] No new security risks introduced
- [ ] Security risks identified and mitigated (describe below)
- [ ] Credentials/secrets properly handled (Secret Manager, environment variables)
- [ ] IAM permissions reviewed and documented

**Security Notes:**
<!-- If applicable, describe security considerations -->

## Screenshots/Logs

<!-- If applicable, add screenshots or logs to demonstrate the changes -->

<details>
<summary>Click to expand</summary>

```
Paste logs here
```

</details>

## Deployment Notes

<!-- Special deployment considerations -->

- [ ] No special deployment steps required
- [ ] Special deployment steps required (describe below)
- [ ] Requires infrastructure changes (OpenTofu/Terraform update)
- [ ] Requires environment variable changes

**Deployment Steps:**
<!-- If applicable, describe deployment steps -->

1.
2.

## Checklist

<!-- Ensure all items are completed before requesting review -->

- [ ] My code follows the project's style guidelines (PEP 8, line length 100)
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
- [ ] I have checked my code and corrected any misspellings
- [ ] I have removed any debugging code or console logs
- [ ] Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)

## Additional Context

<!-- Add any other context about the pull request here -->

---

## For Reviewers

<!-- Help reviewers understand what to focus on -->

**Focus Areas:**
<!-- What should reviewers pay special attention to? -->

-
-

**Questions for Reviewers:**
<!-- Any specific questions or concerns? -->

-
-

---

<!--
Thank you for contributing to GCP FinOps Sentinel! 🎉
Your contribution helps make cloud cost management better for everyone.
-->
