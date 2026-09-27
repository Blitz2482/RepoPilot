# IBM Bob API Adapter

> **Important:** The HTTP contract below is the starter contract printed in the supplied v2.0 bundle. It is not independently verified against the current IBM Bob service. The live hackathon/API specification remains the deployment-time source of truth.

The source onboarding bundle explicitly instructs the team to paste the real Bob API specification into this file, but the supplied bundle does not contain that external API specification. The starter code in the same bundle shows the intended contract as:

- Base URL: `https://api.bob.ibm.com/v2`
- Request endpoint: `/agent/run`
- Headers: `Authorization: Bearer <BOB_API_KEY>`
- JSON request: `{prompt, repo_path, mode:"agent", output_format:"json"}`

RepoPilot therefore preserves that starter contract behind `BOB_BASE_URL` and `BOB_ENDPOINT`. Before a live hackathon deployment, replace the adapter settings with the actual current Bob API documentation supplied by the event portal.

For local development and deterministic testing, `MOCK_BOB=true` bypasses external calls while keeping the same AgentFinding/Q&A interfaces.
