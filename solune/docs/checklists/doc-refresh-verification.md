# Documentation Refresh Verification Checklist

**Refresh Date**: [DATE]
**Refresh Window**: [START] → [END]
**Performed By**: [NAME]

## Verification Items

- [ ] Change manifest accounted for all commits since last baseline
  - SHA range: `[baseline_sha]..[head_sha]`
  - Commit count: [N]
  - Notes:

- [ ] All internal doc links resolve
  - Tool: lychee
  - Broken links found: [N]
  - Notes:

- [ ] All documented features exist in the running application
  - Features smoke-tested: [list]
  - Notes:

- [ ] All config keys in docs exist in the config schema
  - Keys checked: [N]
  - Missing from code: [list or "none"]
  - Notes:

- [ ] Getting-started guide runs clean from a fresh environment
  - Environment: [container/fresh clone/CI]
  - Notes:

- [ ] No references to removed features remain in docs
  - Removed features: [list from manifest]
  - Grep results: [clean / findings]
  - Notes:

- [ ] README feature list matches current capabilities in priority order
  - Notes:

- [ ] New baseline (tag or metadata) is set for next cycle
  - Tag: docs-refresh-[DATE]
  - .last-refresh updated: yes/no
  - Notes:

- [ ] Changelog updated with documentation changes
  - Section added: yes/no
  - Notes:

## Overall Status

- [ ] **PASS** — All items verified
- [ ] **PARTIAL** — Some items require follow-up (see notes)
- [ ] **FAIL** — Critical items unresolved
