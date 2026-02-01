# Contributing to SimpleBudget (Backend)

## Branching Strategy

```
feature-branch → PR → staging → test → PR → main (production)
```

### Branches
- **`main`** — Production. Protected. Deploys automatically to the live Lambda.
- **`staging`** — Testing. Deploys automatically to the staging Lambda.
- **Feature branches** — Your working branches. Create from `staging`.

### Workflow
1. Create a feature branch from `staging`: `git checkout staging && git checkout -b feature/my-change`
2. Make your changes, commit, push
3. Open a PR to `staging` — merge when ready
4. Test on the staging environment
5. When validated, open a PR from `staging` → `main`
6. Merge to deploy to production

### Rules
- **Never push directly to `main`** — always use PRs
- **Test on staging first** — don't skip it
- Lambda env vars are managed in AWS Console (not in CI)

### GitHub Secrets Needed for Staging
- `LAMBDA_FUNCTION_NAME_STAGING` — staging Lambda function name
- `DATABASE_URL_STAGING` — staging database connection string (managed in AWS)
- `SUPABASE_JWT_SECRET_STAGING` — staging JWT secret (managed in AWS)
