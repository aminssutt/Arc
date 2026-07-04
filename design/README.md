# /design

- **Owner:** designspear-epic
- **Goes here:** design direction (reasoning-cockpit, anti-dashboard), tokens (web + iOS), component specs, schematic asset, iOS screen specs.
- **Does NOT go here:** implementation code (`/frontend`, `/ios`), Apple credentials (local `.env`/keychain only).

## Design handoff status

**Status:** Design system, main desktop screen, and mobile case-detail screen are complete for implementation handoff.

**Figma source:** [Arc Figma workspace](https://www.figma.com/design/8AFA0Or97IrnY7QSLJwKHQ/%ED%95%B4%EC%BB%A4%ED%86%A4?m=auto)

**Owner:** `designspear-epic`

**Related issues:** `#41`, `#42`, `#43`, `#44`, `#45`, `#46`, `#58`

## Completed design scope

### Design system

The Arc design system is now defined in Figma with Light and Dark modes.

Completed foundation work:

- Color variables with semantic Light/Dark mode mapping.
- Typography styles for display, headings, body, label, caption, and button text.
- Button variants for primary, secondary, ghost, warning, and warning-subtle states.
- Badge variants for agent state, evidence status, warning state, and neutral state.
- Card, media-card, media-viewport, spacing, radius, and surface treatment rules.
- Brand color variables for the Arc logo and directional arrows, including Light/Dark mode values.

Implementation note:

- Please use semantic variables from the Figma design system rather than hard-coded colors.
- The screen copy is intentionally English-only.
- Internal Figma variables and styles are bilingual where needed for team clarity.

### Desktop main screen

The desktop screen is designed as a reasoning cockpit rather than a traditional monitoring dashboard.

Primary areas:

- **Building Situation:** BIM-style building context with the B5 fault location highlighted.
- **Agent Orchestration:** Main Agent, dormant sub-agents, active Electrical Sub-Agent, and downstream reasoning nodes.
- **Investigation Flow:** Step-by-step card flow showing Detect, Delegate, Retrieve, and Ask Human.

The layout is intended to make the agentic process visible:

1. The Main Agent detects an abnormal voltage pattern.
2. The Main Agent activates the Electrical Sub-Agent.
3. The system retrieves schematics, SOPs, and incident context.
4. The operator receives a field-test request through the mobile flow.

Screenshot:

![Arc desktop investigation screen](screenshots/arc-desktop-investigation.png)

### Mobile case-detail screen

The mobile screen is designed for the field operator after receiving a push notification.

Primary areas:

- **Building Situation:** Shows the fault context and BIM snapshot.
- **Agent Activity:** Summarizes what the agents have already done.
- **Requested Action:** Shows the human field-test task.
- **Evidence:** Lists the supporting schematic and safety documents.

The mobile UX focuses on one action:

> Measure the B5 input terminal voltage and submit the field-test result back into the agent workflow.

Screenshot:

![Arc mobile case detail screen](screenshots/arc-mobile-case-detail.png)

## Implementation guidance

For the frontend and iOS lanes:

- Treat the Figma file as the visual source of truth.
- Preserve the distinction between agent reasoning, evidence retrieval, and human handoff.
- Keep the mobile screen task-oriented. The operator should immediately understand what happened, what Arc is doing, and what action is required.
- The desktop experience should avoid becoming a generic dashboard. The main story is agent activation and evidence-backed reasoning.

## Current handoff summary

The design lane is ready for implementation alignment.

Recommended next steps:

1. Frontend: map the desktop screen to the live SSE event stream.
2. iOS: map the mobile case-detail screen to the push payload and validation flow.
3. Demo: use the desktop and mobile screenshots as deck visuals if live rendering is not ready in time.
