# Arc

*Working name, swappable.*

**Track:** Vultr (Statement Two, Enterprise Agent grounded in documents)
**Parallel target:** NVIDIA partner prize (RTX 5080), physical-AI / critical-energy fit

---

## One-liner

The reflexes of your most experienced electrical engineer, running on every fault in your critical power infrastructure. An operator knows where to go, what to test, and exactly how to fix it, with every step grounded in your own documents.

## The hook

In a factory, a data center, or a nuclear plant, when the electrical infrastructure faults, the clock starts and it is expensive. A fuse blows in compartment B5 and hundreds of things could have caused it: a voltage sag, an overvoltage spike, a thermal overload. Today an operator loses critical minutes hunting the cause across schematics, manuals, and years of past incidents, often alone, at 3am, under stress, near live equipment. The person who can read that fault instantly is a veteran with decades of experience, and there are fewer of them every year. When they retire, that instinct is gone. Arc captures it and runs it on every fault.

## The problem

Downtime on critical power is measured in thousands of euros per minute, and on the highest-criticality sites it is a safety problem, not just a cost one. The diagnosis is manual, expertise-bound, and does not scale. This is exactly the high-stakes enterprise operations workflow that grounds every decision in documentation, which makes it a Vultr-track fit, and it sits squarely in the physical-AI and critical-energy space.

## How it works: a multi-agent workflow with a real-world validation loop

Arc is not one model answering once. It is a team of specialized agents, and the operator sits in the loop at the center.

**Phase 1, Diagnosis**
- A correlation agent takes the alarm ("fuses blown, B5"), reads the incoming sensor values (voltage trace, thermal readings), and pinpoints the location using the plant's ingested floor plans and schematics.
- A root-cause agent cross-references those readings against schematics, equipment manuals, and past incidents, then returns ranked probable causes with a confidence score (overvoltage 78%, thermal 15%, and so on). If confidence is too low it refuses to guess and triggers another retrieval pass (matching-signature incidents, manufacturer bulletins). If it is missing a document it needs, it asks the operator for that specific document and acts on the answer.

Output of Phase 1 is a diagnostic card, pushed to the operator: "Go to B5. Probable cause: overvoltage. Test the input terminal. Bring this equipment." Every claim cited to its source.

**Phase 2, Physical validation and prescription (the differentiator)**
This is the core of the project and the thing no retrieve-then-answer system can do.
- The operator goes to the site, tests in the real world, and comes back with an actual field measurement or observation, for example "415V at the B5 input terminal" or "voltage normal but casing at 80C." This is not a confirm/correct button. The operator reports a real value.
- The agent takes that measurement as new evidence and matches it against its prediction. If it matches, the cause is validated. If it contradicts, the agent pivots, re-diagnoses, and issues a new test, live. Every such round feeds the agent's picture of this fault.
- Once the cause is validated, a remediation agent produces the full step-by-step procedure, with the relevant safety protocols cited inline, and a cost-and-inventory agent predicts the cost of the fault, the cost avoided, and matches the required replacement parts against the company's real stock (a live tool call over the parts catalog). "Fuse X in stock, location Y. If not, reorder, lead time Z."

Because the agent's output depends on what the operator reports back, the loop is genuinely closed between the digital and the physical, and it is falsifiable rather than scripted.

## Why we do not need a real environment

"Does it work" for an agent does not mean "wired to a real substation." It means the agent's decisions are genuinely driven by its inputs and change when those inputs change. We prove that with a faithful scenario: real documents grounding the reasoning, realistic seeded telemetry, and a real operator observation fed back in. The realness comes from the reasoning being input-driven and the human in the loop changing the outcome, not from physical hardware.

## Document grounding (why it fits the track)

Two layers. At setup, Arc ingests the company's strategic documents (floor plans, work plans, control points, schematics, equipment manuals, safety protocols, parts catalog) and builds a clean spatial and technical knowledge base, which is what lets it say "go straight to B5" and cite a real procedure. Then, during a diagnosis, if it realizes it is missing something, it requests that specific document from the operator and adapts. An agent that knows what it does not know and goes to get it is the opposite of basic retrieval.

## Why it fits the Vultr statement

The statement asks for a web-based enterprise agent that grounds decisions in documents, plans, retrieves more than once, calls tools, makes decisions, and produces a usable outcome. Arc maps to every clause, and to the canonical telecom example, with the domain shifted from a telecom network to an electrical network:
- ingests logs and vendor docs, Arc ingests schematics, manuals, incidents, safety protocols
- plans repair sequences, Arc plans diagnosis and intervention
- retrieves historical data to predict root causes, Arc re-retrieves matching-signature incidents, confidence-gated
- calls scheduling tools, Arc calls cost and inventory tools
- generates a prioritized action report with cited docs, Arc produces a cited procedure and prescription

On top of the example, Arc adds two agentic behaviors the example does not have: the physical validation loop and the dynamic document request. It sits at the strong end of what the statement asks for.

## The human layer

Arc is built to augment the operator, never to replace them.
- Safety first. On critical, potentially live electrical systems, the operator no longer walks in blind. Arc hands them the safety procedure and the right equipment before they move.
- Knowledge transfer. The veteran's expertise is encoded, so a junior operates closer to a senior's level, and when the veteran leaves the knowledge stays.
- Wellbeing. The operator stops firefighting alarm storms under pressure. Less stress, less alarm fatigue.
- The compounding effect. Fewer outages, shorter mean-time-to-repair, and safer operations let the site run closer to full capacity, which is what funds growth, and because Arc lowers the expertise barrier, growing the team no longer means finding twenty-year veterans who do not exist.

## The demo (what is on screen)

A web app with two synced views, shown side by side so the whole flow reads as one continuous story:
- Control Room (desktop): the agents' reasoning stream. A live, sequential feed where each step is its own element: which agent is acting, what it found, its confidence, the re-retrieval moment when confidence is too low, the tool calls, and the moment it asks for a missing document. Clickable citations back to the source docs run through the whole stream.
- Operator (mobile/field view): the diagnostic card received, the input where the operator enters the real field measurement, then the prescription card with cited safety steps, cost avoided, and the replacement part matched to stock.

The scenario: a plant electrical schematic with sensitive points marked. A fault is injected on one point (overvoltage, sag, or thermal). An external notification reaches the operator (mobile push or email, for example) with the location and the probable cause. The operator reports back a measurement, the agent validates or pivots, then issues the procedure report. The schematic is passive support: a point lights up only when the agent references it, as a living citation, never a continuously animated flow. The agent's reasoning is the largest element on screen, the schematic is secondary.

The money shot: prepare two runs, one where the field measurement confirms the diagnosis and one where it contradicts it and the agent visibly re-diagnoses. If we are bold, we let a judge pick which fault to inject. A judge cannot call that scripted, because the outcome is set by the input.

## UX direction

A reasoning cockpit, not a monitoring dashboard. A dashboard shows states you contemplate (gauges, curves). Arc shows a process unfolding over time (agents reasoning and acting). That difference in nature is what keeps it out of the banned "dashboard as main feature" category. Principles: the reasoning streams step by step rather than appearing all at once, citations are visible inside the flow, sensor values appear only as cited evidence, and the whole thing stays legible to a non-technical viewer rather than a wall of raw logs.

## Tech

Vultr Serverless Inference for the reasoning across all agents. VultronRetriever (via Serverless Inference) for retrieval over the ingested document corpus. The cost and inventory tools are real functions doing real math over seeded enterprise data. A custom web app frontend surfaces the agents' reasoning and the operator flow. The two views are driven by a stream of typed agent events, so the frontend can be built against a mocked event stream and later swapped to the live agent with no rebuild.

## Compliance: clear of every banned category

- Not a basic RAG app. Multi-agent, confidence-gated re-retrieval, dynamic document requests, real tool calls, and a physical human-validation loop. Multiple retrieval passes and real decisions, never retrieve-then-answer.
- Not a dashboard. The main feature is the agent's reasoning and the operator workflow, not a screen of gauges. The visual is a process visualization (the opposite of a dashboard), it appears only during the agent portion of the pitch, and the schematic reacts to the agent rather than running on its own.
- Not an image analyzer. No computer vision. Sensor and thermal data are numeric inputs the agents reason over, and any photo is displayed as evidence, never analyzed.
- Not a Streamlit app. Custom web application.
- New work only. Built entirely during the event, fresh codebase, distinct from any prior project.
- None of the remaining banned categories apply (no medical, mental-health, nutrition, sports, personality, or job-screening content).

## Pitch scenography and 3-minute flow

The app appears on screen only during the agent portion. During the opening (problem, hook, the retiring expert), the screen shows a simple context visual, not the app, so the only thing a judge ever sees on screen is an agent reasoning, never a dashboard running in the background.

Offer two levels of reading the same system: the operator view by default (what the real user sees, clear and actionable), and an engineer view on request (the full reasoning under the hood). Present it as depth, not as simple versus complex. Only offer the engineer view if it is polished, and keep it to 20 to 30 seconds so it does not blow the timing.

1. Hook: the veteran who reads the fault instantly, and there are fewer every year (context visual, not the app) (15s).
2. Stakes: thousands per minute, and a safety problem on critical sites (15s).
3. App appears. Live demo Phase 1: alarm fires, agents locate and diagnose, low confidence triggers re-retrieval, cited diagnostic card sent to the operator (60s).
4. The pivot: operator reports a real field measurement, agent validates or re-diagnoses live (25s).
5. Phase 2: prescription with cited safety steps, cost avoided, part matched to stock (35s). Optionally offer the engineer view here.
6. Human close: augmentation not replacement, safety, knowledge transfer, scale (30s).

## Why it wins, by the judging weights

- Impact (25%). Critical-infrastructure downtime and safety, a real multi-billion problem, plus the retiring-expert story. Useful to operators, plant managers, and safety teams.
- Demo (50%). Agents reasoning live, confidence-gated re-retrieval visible on screen, real tool calls, clickable citations, a falsifiable validation loop, and a stable inference endpoint that will not break on stage.
- Creativity (15%). The real-world validation loop and the dynamic document request are genuinely past retrieve-then-answer.
- Pitch (10%). The human hook, safety, and knowledge transfer carry the story.
