---
name: discover-collaboration
description: Automatically discover collaboration and teamwork skills when working with code review, pair programming, GitHub, pull requests, team workflows, or documentation. Activates for collaboration development tasks.
license: MIT
metadata:
  author: rand
  version: "3.1"
compatibility: Designed for Claude Code. Compatible with any agent supporting the Agent Skills format.
---

# Collaboration Skills Discovery

Provides automatic access to comprehensive collaboration skills.

## When This Skill Activates

This skill auto-activates when you're working with:
- collaboration
- code review
- documentation
- pair programming
- team workflows
- communication

## Available Skills

### Quick Reference

The Collaboration category contains 6 skills:

1. **codetour-guided-walkthroughs** - Creating CodeTour walkthroughs for codebase understanding
2. **github-pull-requests** - PR workflows, review process, merge strategies
3. **github-actions-workflows** - CI/CD with GitHub Actions
4. **github-issues-projects** - Issue tracking, project boards, milestones
5. **github-repository-management** - Repository settings, branch protection, permissions
6. **github-security-features** - Dependabot, secret scanning, code scanning

### Load Full Category Details

For complete descriptions and workflows:

Read <cc-polymath-root>/skills/collaboration/INDEX.md


This loads the full Collaboration category index with:
- Detailed skill descriptions
- Usage triggers for each skill
- Common workflow combinations
- Cross-references to related skills

### Load Specific Skills

Load individual skills as needed:

Read <cc-polymath-root>/skills/collaboration/codetour-guided-walkthroughs.md
Read <cc-polymath-root>/skills/collaboration/github/github-pull-requests.md
Read <cc-polymath-root>/skills/collaboration/github/github-actions-workflows.md
Read <cc-polymath-root>/skills/collaboration/github/github-issues-projects.md
Read <cc-polymath-root>/skills/collaboration/github/github-repository-management.md
Read <cc-polymath-root>/skills/collaboration/github/github-security-features.md

## Common Workflows

### GitHub PR Workflow
**Sequence**: Pull Requests → Actions → Issues
Read <cc-polymath-root>/skills/collaboration/github/github-pull-requests.md
Read <cc-polymath-root>/skills/collaboration/github/github-actions-workflows.md
Read <cc-polymath-root>/skills/collaboration/github/github-issues-projects.md

### Repository Setup
**Sequence**: Repository Management → Security → Actions
Read <cc-polymath-root>/skills/collaboration/github/github-repository-management.md
Read <cc-polymath-root>/skills/collaboration/github/github-security-features.md
Read <cc-polymath-root>/skills/collaboration/github/github-actions-workflows.md

## Progressive Loading

This gateway skill enables progressive loading:
- **Level 1**: Gateway loads automatically (you're here now)
- **Level 2**: Load category INDEX.md for full overview
- **Level 3**: Load specific skills as needed

## Usage Instructions

1. **Auto-activation**: This skill loads automatically when Claude Code detects collaboration work
2. **Browse skills**: Run `Read <cc-polymath-root>/skills/collaboration/INDEX.md` for full category overview
3. **Load specific skills**: Use bash commands above to load individual skills


**Next Steps**: Run `Read <cc-polymath-root>/skills/collaboration/INDEX.md` to see full category details.
