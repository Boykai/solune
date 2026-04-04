# Plan CRUD Skill

Enables step-level CRUD operations on implementation plans with DAG validation.

## Operations

### Add Step
Adds a new step to an existing plan with automatic position assignment and dependency validation.

### Edit Step
Updates step title, description, or dependencies with DAG re-validation.

### Delete Step
Removes a step and cascades dependency removal to other steps.

### Reorder Steps
Reorders all steps with DAG validation to ensure dependency integrity.

### Approve Step
Sets per-step approval status (pending/approved/rejected).

## Validation

All mutations validate the dependency graph using Kahn's algorithm to detect circular dependencies before committing changes.
