# Code Style and Quality Standards

## Overview

ProRyx enforces consistent code style across Python (backend) and TypeScript (frontend) codebases. All code must pass formatting and linting checks before commits.

---

## Quick Commands

```bash
# Auto-fix formatting issues
./scripts/format.sh

# Check for errors (must achieve 0 errors, 0 warnings)
./scripts/check.sh
```

---

## Python (Backend)

### Tools Used

| Tool | Purpose |
|------|---------|
| **Black** | Code formatter (line length: 88) |
| **Ruff** | Linter (replaces flake8, isort) |
| **pyupgrade** | Modernize Python syntax |

### Style Rules

#### Strings
- Use **double quotes** `"` for all strings
```python
# Good
message = "Hello, world"

# Bad
message = 'Hello, world'
```

#### Imports
- Sorted automatically by Ruff
- First-party imports (`proryx_backend`) separated from third-party
```python
# Good
from fastapi import FastAPI
from sqlalchemy import Column

from proryx_backend.config import settings
from proryx_backend.database import Base
```

#### Line Length
- Maximum **88 characters** (Black default)

#### Type Hints
- Use type hints for function parameters and return values
```python
# Good
async def get_user(user_id: int) -> User | None:
    ...

# Bad
async def get_user(user_id):
    ...
```

#### Docstrings
- Use triple double quotes
- First line is summary
```python
def calculate_total(items: list[Item]) -> Decimal:
    """Calculate the total price of all items.

    Args:
        items: List of items to sum.

    Returns:
        Total price as Decimal.
    """
    ...
```

### Configuration

Settings in `pyproject.toml`:

```toml
[tool.black]
line-length = 88
target-version = ['py312']

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["proryx_backend"]
```

---

## TypeScript (Frontend)

### Style Rules

#### Strings
- Use **double quotes** `"` for all strings
```typescript
// Good
const message = "Hello, world";

// Bad
const message = 'Hello, world';
```

#### Semicolons
- Required at end of statements

#### Components
- Use functional components with TypeScript
- Props interfaces should be explicitly defined
```typescript
// Good
interface ButtonProps {
  label: string;
  onClick: () => void;
}

const Button = ({ label, onClick }: ButtonProps) => {
  return <button onClick={onClick}>{label}</button>;
};
```

#### Imports
- React imports first
- Third-party imports second
- Local imports last
```typescript
import { useState } from "react";

import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
```

---

## General Guidelines

### No Trailing Whitespace
- Remove trailing spaces from all lines

### No Unused Imports
- Remove imports that aren't used

### Consistent Naming

| Type | Convention | Example |
|------|------------|---------|
| Python variables | snake_case | `user_name` |
| Python classes | PascalCase | `UserService` |
| Python constants | UPPER_SNAKE | `MAX_RETRIES` |
| TypeScript variables | camelCase | `userName` |
| TypeScript components | PascalCase | `UserCard` |
| TypeScript constants | UPPER_SNAKE | `MAX_RETRIES` |
| Files (Python) | snake_case | `user_service.py` |
| Files (TypeScript) | PascalCase for components | `UserCard.tsx` |

### File Organization

#### Backend Module Structure
```
modules/feature_name/
├── __init__.py      # Exports
├── models.py        # SQLAlchemy models
├── schemas.py       # Pydantic schemas
├── crud.py          # Database operations
├── services.py      # Business logic
└── routers.py       # API endpoints
```

#### Frontend Structure
```
src/
├── api/             # API hooks (TanStack Query)
├── components/      # Reusable UI components
├── pages/           # Page components
├── stores/          # Zustand stores
├── lib/             # Utilities
└── types/           # TypeScript types
```

---

## Pre-Commit Checklist

Before every commit, ensure:

1. **Format code:**
   ```bash
   ./scripts/format.sh
   ```

2. **Run checks:**
   ```bash
   ./scripts/check.sh
   ```

3. **Verify output:**
   - 0 errors
   - 0 warnings

4. **Test changes:**
   - Start the app and verify functionality
   - Check browser console for errors

---

## Common Issues and Fixes

### "Line too long"
```bash
# Auto-fixed by Black
./scripts/format.sh
```

### "Import not sorted"
```bash
# Auto-fixed by Ruff
./scripts/format.sh
```

### "Unused import"
- Manually remove the unused import

### "Missing type annotation"
- Add type hints to function parameters and return values

### "Single quotes used"
```bash
# Auto-fixed by formatters
./scripts/format.sh
```

---

## Quality Gates

All PRs must pass:
- `./scripts/check.sh` with 0 errors
- Manual review for logic and security
- Tests (when available)

---

## Resources

- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [TypeScript Best Practices](https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html)
