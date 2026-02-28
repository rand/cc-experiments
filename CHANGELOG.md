# Changelog

All notable changes to cc-polymath are documented in this file.

## [4.0.0] - 2026-02-28

### Changed
- **Breaking**: Replaced all `<cc-polymath-root>` path references with relative paths across 111 files (1,271 replacements)
- Consolidated gateway skills from 40 to ~22 for reduced context budget
- Updated cross-reference validation to work with relative paths

### Added
- CHANGELOG.md
- MCP server for skill discovery (`mcp-server/`)
- Enhanced plugin hooks (compact, SubagentStart)
- `context: fork` on `/skills` command

### Removed
- Large JSON report files from repository tracking (moved to CI artifacts)
- Internal planning documents from repository

## [3.1.0] - 2026-02-02

### Added
- New skills across multiple domains
- End-to-end validation test script
- Gateway keyword enrichment for better auto-discovery

### Fixed
- Hook schema validation errors
- Invalid `agents` field in plugin.json

## [3.0.0] - 2026-02-02

### Changed
- Modernized plugin structure for Claude Code plugin system
- Fixed path resolution throughout the plugin
- Cleaned up command definitions

### Fixed
- Plugin installation instructions across all documentation
- Commands and skills path prefixes in plugin.json

## [2.0.0] - 2025-10-27

### Added
- Three-tier progressive discovery architecture (gateways, indexes, leaf skills)
- 40 gateway skills for automatic discovery
- Category INDEX.md files for each domain
- Property-based test suite
- Security audit infrastructure
- Getting started documentation and setup scripts

### Changed
- Reorganized from flat skill listing to hierarchical discovery system
- Optimized context budget (60-84% reduction vs monolithic index)

## [1.0.0] - 2025-10-18

### Added
- Initial standalone repository
- 132 atomic skills across multiple domains
- YAML frontmatter metadata on all skills
- CI workflows and quality assurance
- MIT license
