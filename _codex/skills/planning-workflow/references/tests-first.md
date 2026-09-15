## TDD + BDD rules

For every acceptance area:

- define acceptance in observable user or system outcomes,
- define what the system should do automatically before asking the user or agent to intervene,
- add `Given/When/Then` scenarios for happy path, failure path, and relevant edge cases,
- add counterexample or ambiguity scenarios when matching, routing, identity, parsing, refs, or policies could yield misleading passes,
- add boundary or scale scenarios when volume, fan-out, or aggregation could change correctness,
- add cross-surface parity scenarios when behavior must match across HTTP/CLI/MCP/UI or similar interfaces.

For workflow and product-surface planning, include scenarios that distinguish:

- routine recoverable faults that should self-heal,
- ambiguous or high-risk faults that should fail closed,
- and the exact agent-legible error or inline guidance expected when automation must stop.

For every phase:

- start with failing tests first when practical,
- map tests to acceptance criteria and BDD scenario IDs,
- make the RED-phase contract strong enough to catch partial or misleading implementations,
- if strict TDD is not practical, state why and define compensating verification.
