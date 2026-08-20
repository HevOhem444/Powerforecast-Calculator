# Versioning, Logging, and Release Rules

## 1. Version Format Syntax
Follow the exact format: `[Main].[Major].[Deployments/Fixes]v` (e.g., `1.6.43v`)

- **Main (`X`..):** Main application version. Do NOT change unless explicitly instructed.
- **Major Fixes (`.X.`):** Major updates/fixes. **STRICT RULE:** Do NOT change or increment unless explicitly instructed by the user.
- **Deployments / Minor Fixes (`..X`):** Auto-increment on every deployment, push, or minor bug fix under the current major version.
- **Reset Rule:** When **Major Fixes** changes, reset the **Deployments/Minor Fixes** counter back to `0` (e.g., `1.6.43v` -> `1.7.0v`).

---

## 2. GitHub Commit & Tagging Standard
All GitHub commit messages, pull requests, and git tags must follow this exact template:

`[Version] - [Clear description of changes]`

**Example:**
`1.6.43v - Remove api/main.py and remove rewrites in vercel.json so Vercel zero-config serves index.html at root, docs.html at /docs, and api/*.py at /api/*`

---

## 3. UI Display Update
- Update the version string in the codebase so the visible tag on the **bottom-right corner** of the webpage displays the exact new version.
- Never deploy without syncing the UI version tag.

---

## 4. Database Changelog & Logging
On every deployment:
- Record and compile the version number, description, and timestamp into the database to serve as audit logs.
- Ensure 100% parity across all three targets:
  1. GitHub Commit Message
  2. Webpage UI (Bottom-Right)
  3. Database Changelog Logs
