# Security and Access (Closed Test Contour)

## Access model
- Global roles:
  - `global_admin`
- Organization roles:
  - `organization_admin`
  - `editor`
  - `reader`

## Rules
- All data is scoped to `organization_id`
- `global_admin` can operate across all organizations
- `organization_admin` manages users and settings of their organization
- `editor` can add/modify/delete documents inside their organization
- `reader` can search and retrieve documents inside their organization

## Authentication (initial)
- Local auth stub (for closed contour), evolving later if needed.

## Authorization
- Enforced at API boundary (middleware + service layer checks)
