# RepoPilot Security Notes

This document records the non-credential security controls included in the deployment package.

## Repository ingestion

- Only GitHub repository URLs are accepted.
- Clone operations disable interactive credential prompts.
- Optional GitHub credentials are injected through Git configuration rather than the clone command line.
- Repository size, source-file size, and clone time are bounded.
- Symlinks are excluded from source display and repository metadata traversal.
- Source paths are normalized and resolved before file access, with traversal and symlink checks.
- The analysis pipeline parses source as data; it does not execute repository application code.

## API and browser boundaries

- Production CORS requires explicit origins and disables credentialed CORS.
- Production frontend API URLs must use HTTPS.
- Browser WebSocket connections are checked against the same explicit origin allow-list.
- Public job responses do not expose the backend's internal clone filesystem path.
- Production provider-exchange logging is disabled by configuration validation.
- Request IDs are attached to successful responses for troubleshooting.

## Deployment boundaries

- The backend container runs as a dedicated non-root user.
- Secrets are provided through deployment environment variables, not source files.
- Docker/CI release checks reject common committed-secret patterns and local environment files.
- `/health` is a liveness probe; `/ready` is the production dependency/configuration gate.

## Remaining deployment-time controls

Authentication/authorization, if enabled through the bundle's Clerk stack, must be connected before exposing private repository analysis to untrusted users. The current hackathon MVP routes are intentionally account-light and should be treated as a controlled deployment until the team's authentication layer is configured.
