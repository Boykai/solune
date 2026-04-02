# Contracts: Linting Clean Up

This feature is a tooling and configuration change. It does not introduce or modify any API endpoints, data schemas, or service contracts.

No OpenAPI, GraphQL, or other contract files are needed for this feature.

**Rationale**: The linting cleanup modifies type-check configurations, removes inline suppression comments, and tightens ESLint rules. All changes are to developer tooling and CI/CD pipelines. No runtime API behaviour changes.

If suppression removal in `solune/frontend/src/services/api.ts` changes the TypeScript types used for API calls, run `bash solune/scripts/validate-contracts.sh` to verify that frontend types still align with the backend OpenAPI schema.
