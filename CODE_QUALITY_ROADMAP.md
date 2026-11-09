# Code Quality & Linting Roadmap - Next Session

## Goal
Establish consistent code quality standards across the entire anime-portal project (Python, Go, React/Frontend) using linting, formatting, and code review automation.

**Result:** Automated code quality gates that catch issues before merge, DRY codebase, best practices enforced.

---

## Current State

### Existing Configs (Reference)
- Python linting: `/Users/germanskrylnikov/classifier/python-lint.yml`
- Go linting: `/Users/germanskrylnikov/Qortex/qortex/golangci.yml`
- Frontend: ❌ NO linting setup

### Anime Portal Current State
- ✅ Phase 1-3 code implemented
- ❌ No pre-commit hooks
- ❌ No linting in CI/CD
- ❌ No frontend linting/formatting
- ❌ Backend Python linting partially setup
- ⚠️ Go formatting not enforced
- ⚠️ React code style not standardized

---

## Phase 1: Audit Existing Code

### What to Check
1. **Python Backend**
   - Read: `/Users/germanskrylnikov/classifier/python-lint.yml`
   - Check: anime-portal backend structure
   - Tool: pylint, black, isort already configured?
   - Issues to find: Unused imports, style violations, type hints missing

2. **Go Services**
   - Read: `/Users/germanskrylnikov/Qortex/qortex/golangci.yml`
   - Check: anime-portal go-search structure
   - Tool: golangci-lint already available?
   - Issues to find: Unformatted code, missing error handling, complexity

3. **React Frontend**
   - Check: anime-portal/frontend eslint config
   - Tool: ESLint/Prettier setup?
   - Issues to find: Unused variables, React warnings, style issues

### Deliverable
- Audit report: What's missing, what exists
- List of violations found in each codebase
- Recommended tools for each language

---

## Phase 2: Setup Linting Configs

### Python Linting (Backend)
**File:** `backend/.pylintrc` + `backend/pyproject.toml`

Tools:
- **pylint** - Code style & errors
- **black** - Formatting (opinionated)
- **isort** - Import sorting
- **mypy** - Type checking
- **flake8** - Alternative linter (simpler)

**Config to create:**
```
backend/
├── .pylintrc (pylint config)
├── pyproject.toml (black, isort, mypy)
├── setup.cfg (flake8)
└── Makefile targets:
    ├── make lint
    ├── make format
    ├── make type-check
```

### Go Linting (Go Service)
**File:** `go-search/.golangci.yml`

Tools:
- **golangci-lint** - All-in-one linter
- **goimports** - Import formatting
- **gofmt** - Standard formatter
- **go vet** - Built-in checker

**Config to create:**
```
go-search/
├── .golangci.yml (golangci-lint config)
├── Makefile targets:
    ├── make lint
    ├── make fmt
    ├── make vet
```

### React/Frontend Linting
**Files:** `frontend/.eslintrc.js`, `frontend/.prettierrc`

Tools:
- **ESLint** - React best practices
- **Prettier** - Auto-formatting
- **TypeScript** - Type checking (if using TS)
- **React Hooks** - eslint-plugin-react-hooks

**Config to create:**
```
frontend/
├── .eslintrc.js (ESLint config)
├── .prettierrc (Prettier config)
├── .eslintignore
├── tsconfig.json (if TypeScript)
└── package.json scripts:
    ├── npm run lint
    ├── npm run format
    ├── npm run type-check
```

### Deliverable
- All linting configs (.pylintrc, .eslintrc, .golangci.yml, etc.)
- Consistent across all 3 languages
- Makefile targets for easy running
- README explaining how to use

---

## Phase 3: Pre-Commit Hooks

### What
Automatically run linting on every git commit - catch issues before push.

### Setup
**File:** `root/.pre-commit-config.yaml`

Hooks to add:
1. **Python formatters**
   - black
   - isort
   - pylint (optional, run separately)

2. **Go formatters**
   - gofmt
   - goimports
   - golangci-lint (optional, heavy)

3. **Frontend formatters**
   - prettier
   - eslint (with --fix)

4. **General**
   - trailing-whitespace
   - end-of-file-fixer
   - check-yaml
   - check-json

### Deliverable
- `.pre-commit-config.yaml` at project root
- Installation instructions: `pre-commit install`
- Test that it works on git commit

---

## Phase 4: CI/CD Integration

### GitHub Actions Workflow
**File:** `.github/workflows/code-quality.yml`

Runs on every push/PR:
1. Python linting (pylint, mypy)
2. Go linting (golangci-lint)
3. Frontend linting (ESLint, TypeScript)
4. Code formatting check (black, prettier)
5. Security scan (bandit for Python)

### Deliverable
- GitHub Actions workflow file
- Fail PR if linting fails
- Show violations as PR comments

---

## Phase 5: Codebase Refactoring

### What to Fix
After linting setup, fix violations:

**Python (Backend)**
- Add missing type hints
- Remove unused imports
- Format with black
- Sort imports with isort
- Fix mypy errors

**Go (Services)**
- Run gofmt on all files
- Fix golangci-lint warnings
- Add error handling
- Simplify complex functions

**React (Frontend)**
- Fix ESLint warnings
- Format with Prettier
- Remove unused imports
- Fix React warnings
- Add prop-types/TypeScript

### Deliverable
- Clean codebase with zero lint violations
- All tests still passing
- Git commits showing refactoring

---

## Phase 6: Documentation

### What to Document
1. **Linting Guide** - How to run linters locally
2. **Pre-commit Setup** - How to install hooks
3. **Code Style Guide** - Standards for each language
4. **CI/CD Status** - How to check if PR passes checks
5. **Troubleshooting** - Common issues and fixes

### Files to Create
```
root/
├── LINTING.md (how to lint)
├── CODE_STYLE.md (standards)
├── .github/
│   └── workflows/code-quality.yml (CI/CD)
└── docs/
    └── code-quality.md (overview)
```

### Deliverable
- Complete documentation
- Easy for new contributors to follow

---

## Tools Comparison Table

| Language | Tool | Why | Alternative |
|----------|------|-----|-------------|
| **Python** | black | Opinionated, zero-config | autopep8 |
| | pylint | Comprehensive | flake8 |
| | isort | Import sorting | reorder-python-imports |
| | mypy | Type checking | pyright |
| **Go** | golangci-lint | All-in-one | gofmt + goimports |
| | gofmt | Standard format | - |
| **React** | ESLint | Best practices | TSLint (deprecated) |
| | Prettier | Auto-format | - |
| | TypeScript | Type safety | PropTypes |

---

## Implementation Order (Priority)

### Session 1: Foundation (2-3 hours)
1. ✅ Audit existing code (30 min)
2. ✅ Create Python linting config (30 min)
3. ✅ Create Go linting config (30 min)
4. ✅ Create React/ESLint config (30 min)
5. ✅ Test all linters work (30 min)

### Session 2: Integration (2-3 hours)
1. ✅ Setup pre-commit hooks (30 min)
2. ✅ Setup GitHub Actions CI/CD (30 min)
3. ✅ Fix backend Python violations (30 min)
4. ✅ Fix Go service violations (30 min)
5. ✅ Fix React/frontend violations (30 min)

### Session 3: Polish (1-2 hours)
1. ✅ Fix remaining violations (30 min)
2. ✅ Document everything (30 min)
3. ✅ Test end-to-end (30 min)
4. ✅ Commit and push (15 min)

**Total: 5-8 hours over 3 sessions**

---

## Success Criteria

✅ All linting configs created  
✅ Zero lint violations in codebase  
✅ Pre-commit hooks working  
✅ GitHub Actions CI/CD passing  
✅ All tests still passing  
✅ Documentation complete  
✅ New team members can follow standards  

---

## Files to Reference

### Existing Configs (Learn From)
- `/Users/germanskrylnikov/classifier/python-lint.yml`
- `/Users/germanskrylnikov/Qortex/qortex/golangci.yml`
- Check if there are frontend configs in other projects

### Will Create
```
anime-portal/
├── backend/
│   ├── .pylintrc
│   ├── pyproject.toml
│   └── setup.cfg
├── go-search/
│   ├── .golangci.yml
│   └── Makefile (add lint targets)
├── frontend/
│   ├── .eslintrc.js
│   ├── .prettierrc
│   └── .eslintignore
├── .pre-commit-config.yaml
├── .github/workflows/code-quality.yml
└── docs/
    └── LINTING.md
```

---

## Benefits After Completion

✅ **Consistency** - Same standards across all code  
✅ **Quality** - Catch bugs before merge  
✅ **Automation** - Linting runs automatically  
✅ **Learning** - Best practices enforced  
✅ **Portfolio** - Shows professional setup  
✅ **Scalability** - Easy to onboard new developers  

---

## Notes for Next Session

1. **Start with audit** - Understand current state
2. **Copy configs** - Reference existing projects
3. **Iterate configs** - Get team consensus on rules
4. **Fix violations** - Clean up codebase
5. **Automate** - Pre-commit + CI/CD
6. **Document** - Make it easy to follow

---

## Resources to Have Ready

- Existing lint configs from other projects
- GitHub Actions examples
- ESLint best practices guide
- Prettier documentation
- golangci-lint documentation
- Anime portal source code review ready

---

**Ready to establish code quality standards!** 🎯
