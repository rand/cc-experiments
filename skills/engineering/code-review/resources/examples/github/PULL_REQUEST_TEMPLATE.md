# Pull Request Template

## Description

<!-- Provide a brief description of the changes in this PR -->

### What does this PR do?
<!-- Explain the purpose and functionality of these changes -->

### Why is this change needed?
<!-- Explain the motivation or problem being solved -->

### How does this work?
<!-- Brief technical explanation of the approach -->

## Type of Change

<!-- Mark with an 'x' all that apply -->

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature that breaks existing functionality)
- [ ] Refactoring (no functional changes, just code restructuring)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Security fix
- [ ] Dependency update

## Testing

### How was this tested?

<!-- Describe the tests you ran and their results -->

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] End-to-end tests added/updated
- [ ] Manual testing performed

### Test Coverage

<!-- Paste coverage report or percentage -->

```
Coverage: XX%
Critical paths: XX%
```

### Manual Testing Steps

<!-- If manual testing was performed, list the steps -->

1.
2.
3.

## Checklist

<!-- Mark with an 'x' all that have been completed -->

### Code Quality
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Code is self-documenting or has comments for complex logic
- [ ] No debug statements (console.log, print, etc.)
- [ ] No commented-out code
- [ ] Error handling is appropriate

### Testing
- [ ] All new and existing tests pass locally
- [ ] Test coverage meets requirements (>70%)
- [ ] Edge cases are tested
- [ ] Error cases are tested

### Documentation
- [ ] Public APIs have documentation/comments
- [ ] README updated if needed
- [ ] CHANGELOG updated
- [ ] Breaking changes documented
- [ ] Migration guide provided (if breaking changes)

### Dependencies
- [ ] Dependencies are up-to-date
- [ ] No new security vulnerabilities introduced
- [ ] License compatibility checked
- [ ] Dependency versions pinned appropriately

### Security
- [ ] No secrets or credentials in code
- [ ] Input validation added where needed
- [ ] Authentication/authorization checked
- [ ] Security best practices followed

### Performance
- [ ] No performance regressions
- [ ] Database queries optimized (no N+1 queries)
- [ ] Appropriate caching implemented
- [ ] Large datasets handled efficiently

## Related Issues

<!-- Link to related issues or tickets -->

- Fixes #<!-- issue number -->
- Related to #<!-- issue number -->
- Closes #<!-- issue number -->

## Breaking Changes

<!-- If this PR includes breaking changes, list them here -->

### What breaks?
<!-- Describe what existing functionality is affected -->

### Migration Path
<!-- Describe how users should update their code -->

```
# Before
old_code_example()

# After
new_code_example()
```

## Screenshots/Videos

<!-- If applicable, add screenshots or videos demonstrating the changes -->

### Before
<!-- Screenshot or description of behavior before changes -->

### After
<!-- Screenshot or description of behavior after changes -->

## Deployment Notes

<!-- Any special considerations for deployment? -->

- [ ] Database migrations required
- [ ] Environment variables need updating
- [ ] Feature flags required
- [ ] Cache needs clearing
- [ ] CDN needs invalidation
- [ ] Background jobs need restarting
- [ ] Configuration changes needed

### Rollback Plan

<!-- How to rollback if issues arise in production -->

1.
2.

## Performance Impact

<!-- Describe any performance implications -->

### Before
<!-- Metrics before changes (if applicable) -->

### After
<!-- Metrics after changes (if applicable) -->

## Additional Context

<!-- Any additional information that reviewers should know -->

### Design Decisions

<!-- Explain key design decisions and alternatives considered -->

### Trade-offs

<!-- What trade-offs were made and why? -->

### Future Work

<!-- What should be done in follow-up PRs? -->

- [ ] <!-- Future task 1 -->
- [ ] <!-- Future task 2 -->

## Reviewer Notes

<!-- Specific areas you'd like reviewers to focus on -->

### Focus Areas

- <!-- Area 1 -->
- <!-- Area 2 -->

### Questions for Reviewers

- <!-- Question 1 -->
- <!-- Question 2 -->

---

**Ready for Review:** <!-- Yes/No - change to Yes when ready -->

**Merge Strategy:** <!-- Merge commit / Squash / Rebase -->

**Target Milestone:** <!-- Version/milestone this should be included in -->
