# Next-Gen Roadmap: Observe-Hypothesize-Verify

This plan outlines the path to transition TrashDig from a linear scanner to a next-generation autonomous vulnerability research agent as specified in `nextgen.md`.

## Current Gaps
1.  **Verification Loop**: No mechanism to generate or execute Proof-of-Concept (PoC) code to confirm findings.
2.  **Internal Loop**: Agents operate in a single-shot manner rather than a recursive hypothesis loop.
3.  **AST Precision**: Tooling is currently text-heavy (`ripgrep`) rather than fully AST-aware (missing semantic references and scope analysis).
4.  **Steerable Autonomy**: Interaction is limited to file prioritization; the agent cannot ask questions or be interrupted mid-hunt.
5.  **Persistence**: No long-term project-specific knowledge graph or finding database.

## Implementation Phases

### Phase 1: The Verification Loop (Priority: High)
- **Implement `bash_tool`**: A secure execution environment for running scripts.
- **Create `ValidatorAgent`**: A specialized agent that takes a potential finding and attempts to write a Python or `curl`-based PoC.
- **Verification Workflow**:
    1. Hunter finds a potential bug.
    2. Hunter calls Validator to "Prove it."
    3. Validator runs PoC, captures output, and updates the Finding status (Verified/False Positive).

### Phase 2: Hypothesis-Driven Orchestration
- **Refactor `Coordinator`**: Introduce a `TaskQueue` where agents can post "Hypotheses."
- **Observe-Hypothesize-Verify Loop**:
    - `StackScout` observes and posts targets.
    - `Hunter` picks up targets, generates a "Vulnerability Hypothesis," and requests specific data flow traces.
    - `Hunter` spawns sub-tasks for the `Validator` or `DefinitionResolver`.

### Phase 3: Semantic Code Intelligence (AST)
- **Implement `FindReferences(symbol)`**: Use `tree-sitter` or specialized grep to find all call-sites of a function.
- **Implement `GetScope(file, line)`**: Provide the LLM with the local variable names and types at a specific line.
- **AST-Aware Taint Analysis**: Replace `ripgrep`-based `trace_variable` with a true AST walker that understands assignments and function calls.

### Phase 4: Collaborative Steering & Persistence
- **"Agent Asks User"**: Add a mechanism for the agent to pause and request clarification via the TUI REPL.
- **Project Database**: Use SQLite to store the "Project Profile," symbol maps, and all attempted hypotheses (including failed ones).
- **Context Compaction**: Implement a strategy to summarize old tool outputs to keep the context window clean during deep dives.

## Next Steps
1. Implement the `bash_tool` and `ValidatorAgent` infrastructure.
2. Update `TODO.md` with these milestones.
TODO.md` with these milestones.
