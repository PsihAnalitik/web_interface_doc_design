# workflow_ai runtime snapshot

Only the Python `workshop/` runtime is included, so deployment does not require a
second checkout on the server. `SNAPSHOT.json` records the upstream base commit
and SHA-256 of every copied source file. The snapshot includes local working-tree
changes to that runtime; it is not represented as a pristine upstream commit.

Do not edit these files as part of Copilot feature work. Update the runtime in
workflow_ai, copy the reviewed Python files and refresh `SNAPSHOT.json` together.
Runtime dependencies and the web service are locked in
`agent_factory_baseline/service/uv.lock`.

No upstream documents, wiki, credentials, logs or generated runs are bundled.
Copilot supplies its own versioned wiki and prompts.
