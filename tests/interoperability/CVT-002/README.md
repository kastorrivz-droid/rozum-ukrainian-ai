# PRE-CVT-002 interoperability fixtures

These fixtures are additive and non-normative. `jcs_vectors.json` is evaluated by
both the Python RFC 8785 dependency and an independent, dependency-free Node.js
implementation. Passing this subset proves byte agreement for the recorded JCS
cases and the immutable CVT-001 signing input; it is not a full CVT-002 PASS.
