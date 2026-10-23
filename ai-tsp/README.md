# AI TSP Backend

Connected-vehicle AI backend service for the Stephen FDE platform.

## Commands

Run from the repository root:

```bash
npm run tsp:install
npm run dev:tsp
npm run tsp:test
```

The service listens on port `8002` and exposes APIs under
`/api/agent-data`. RDS configuration is loaded from the repository root
`.env` file.
