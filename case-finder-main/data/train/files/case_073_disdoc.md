**Company**: Spotify
**Title**: Background Coding Agents: Predictable Results Through Strong Feedback Loops (Part 3)
**Technology area**: AI agents
**Source URL**: https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3
**Content type**: article

### 1. Problem definition

#### 1.1. Origin

The system, internally codenamed "Honk," is a background coding agent designed to address the challenges of large-scale software maintenance at Spotify. The goal is to automate code changes across thousands of different software components without direct human supervision. This system is part of a broader initiative for Fleet Management, enabling agents to rewrite software automatically.

#### 1.2. Relevance & reasons

Manually performing code changes across thousands of components is not scalable. Automation is necessary, but unreliable automation can create more work for engineers and erode trust. The primary challenge is ensuring that an unsupervised agent can produce correct and reliable results as often as possible. Failures in this process can lead to engineers having to fix half-broken code or, in the worst case, merging functionally incorrect code that breaks production.

#### 1.3. Expectations

The system is expected to produce pull requests (PRs) that are:
*   **Correct**: The code should be syntactically correct, build successfully, and pass all tests.
*   **Reliable**: The generated PRs should not introduce functional regressions.
*   **Scoped**: The changes should strictly adhere to the instructions provided in the initial prompt and not include extraneous refactoring or creative additions.

#### 1.4. Previous work

This document describes the third iteration of the "Honk" system. Previous work (Parts 1 and 2 of the blog series) focused on enabling the Fleet Management system to use agents and on writing effective prompts to guide the agent. The system described here introduces a verification loop to improve upon the reliability of earlier versions.

#### 1.5. Usage volumes and patterns

The system operates across "thousands of different software components." Internal metrics are gathered from "thousands of agent sessions."

### 2. Goals and anti-goals

#### 2.1. Goals

*   **High Reliability**: The primary goal is to produce correct and reliable code changes with a high degree of predictability.
*   **Automation at Scale**: Successfully automate code modifications across thousands of software components.
*   **Engineer Trust**: Build trust in the automation by minimizing the number of incorrect or broken PRs that require human intervention.
*   **Complexity Handling**: Enable agents to solve increasingly complex tasks reliably.

#### 2.2. Anti-goals

*   **Agent Creativity**: The agent should not "get creative" and change things outside the scope of its prompt, such as refactoring unrelated code or disabling flaky tests.
*   **CI Failures**: The system should avoid producing PRs that fail in continuous integration (CI), as this is frustrating for engineers and requires manual fixes.
*   **Hidden Functional Errors**: The system must not produce PRs that pass CI but are functionally incorrect, as these are the most serious errors and can break production.
*   **Agent Flexibility**: The agent's flexibility is intentionally reduced to make it more predictable. It should only perform its core task of taking a prompt and applying a code change. Complex tasks like user interaction or Git operations are handled by surrounding infrastructure.

### 3. Risks and constraints

#### 3.1. Risks

The primary risks are categorized into three failure modes:
1.  **Agent fails to produce a PR**: Considered a minor annoyance. The worst-case scenario is that the change must be performed manually.
2.  **Agent produces a PR that fails in CI**: This is a frustrating error for engineers who must decide whether to fix the half-broken code. This is a significant time sink.
3.  **Agent produces a PR that passes CI but is functionally incorrect**: This is the most serious error. Such changes are hard to spot in reviews and can break production functionality if merged, eroding trust in the automation.

These failures can be caused by:
*   The target component having little to no test coverage.
*   The agent changing code outside the scope of the prompt.
*   The agent being unable to properly run builds and tests for the target component.

#### 3.2. Constraints

*   **Security**: The agent runs in a highly sandboxed container with limited permissions, few binaries, and virtually no access to surrounding systems.
*   **Context Window**: The agent's context window is a precious resource. The system is designed to abstract away noise (e.g., complex build system outputs) to avoid consuming the context window unnecessarily.
*   **Hardware/OS**: The initial version of the verifiers only runs on Linux x86, which serves backend and web infrastructure but is a constraint for broader adoption (e.g., iOS apps requiring macOS, or backend systems on ARM64).

### 4. Metrics and loss functions

#### 4.1. Offline metrics

*   **Judge Veto Rate**: The percentage of proposed changes that are vetoed by the "LLM as a Judge" verifier. Out of thousands of agent sessions, the judge vetoes about 25% of them.
*   **Course-Correction Rate**: The percentage of times the agent successfully corrects its changes after being vetoed by the judge. This happens in about 50% of veto cases.
*   **Judge Score**: The judge LLM provides a verdict score from 0 to 1 on whether the proposed change strictly follows the instructions. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_073/img_004.png`)

The system currently lacks a structured evaluation framework, but implementing one is planned for future work to systematically assess changes to prompts, agent architectures, and LLM providers.

#### 4.2. Online/business metrics

[NO INFO]

#### 4.3. Loss functions

[NO INFO]

### 5. Data (Dataset)

#### 5.1. Data sources

*   **Source Code**: The agent has read access to the codebase of the target software component.
*   **Prompts**: The primary input is a natural language prompt describing the code change to be performed. These are authored by surrounding infrastructure, not the agent itself.
*   **Code Diffs**: The "LLM as a Judge" component uses the `git diff` of the proposed change as input for its evaluation.

#### 5.2. Labeling strategy

[NO INFO]

#### 5.3. Data quality and cleaning

The system uses verifiers to provide feedback on the quality of the generated code. Part of the verifier's job is to parse complex, noisy output from build and test tools and extract only the most relevant error messages. This is done using techniques like regular expressions.

#### 5.4. ETL

[NO INFO]

### 6. Validation schema

The system is designed around a strong "verification loop" that provides incremental feedback to the agent. This loop is the primary validation mechanism.

*   **Inner Loop (Fast Feedback)**: This loop can be triggered as a tool call by the agent at any time and is always run before a PR is opened. It consists of one or more independent verifiers.
    *   **Deterministic Verifiers**: These activate automatically based on the content of the software component (e.g., a `MavenVerifier` activates if a `pom.xml` is found). They perform tasks like:
        *   **Formatting**: e.g., `mvn com.spotify.fmt:fmt-maven-plugin:format`
        *   **Building**: e.g., `mvn compile`
        *   **Testing**: e.g., `mvn test`
        These verifiers ensure the agent produces syntactically correct code that builds and passes tests. They parse tool output to provide short, relevant feedback. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_073/img_002.png`)
    *   **LLM as a Judge**: This is another verifier that runs after all other verifiers have completed. It uses an LLM to evaluate if the proposed code change (the diff) strictly adheres to the original prompt. It is designed to catch instances where the agent goes out of scope. The judge is given a system prompt to act as a strict senior engineer. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_073/img_004.png`)

*   **Outer Loop (Future Work)**: A planned future enhancement is to integrate the agent more deeply with existing CI/CD pipelines. This would involve the agent acting on CI checks in GitHub pull requests, adding another layer of validation.

The verifiers are abstracted from the agent via a tool definition using a "Model Context Protocol (MCP)". The agent only knows it can call a `verify_tool`, not the specifics of each underlying verifier. (see image: `ml-design-doc-reviewer/data/raw_documents/images/case_073/img_003.png`)

### 7. Baseline solution

The implicit baseline is the manual process where engineers perform large-scale code changes themselves. An alternative baseline is a simpler agentic system without the strong verification loops, which is noted to often produce code that "simply doesn't work."

### 8. Errors and their analysis

The system is designed to mitigate three primary failure modes:

1.  **Agent fails to produce a PR**: This is accepted as a low-severity failure.
2.  **Agent produces a PR that fails in CI**: This is addressed by the deterministic verifiers (format, build, test) which are run before the PR is created. If any of these fail, the PR is blocked.
3.  **Agent produces a PR that passes CI but is functionally incorrect**: This is the most critical error. It is mitigated by two main components:
    *   **High Test Coverage**: The success of the system relies on the target component having good test coverage, which the verifiers can execute.
    *   **LLM as a Judge**: This component specifically targets errors where the agent goes "outside the instructions outlined in the prompt." It acts as a semantic check on the agent's work. From empirical observation, this is the most common trigger for a judge veto.

If a verifier fails during the pre-PR check, the PR is not opened, and the user receives an error message.

### 9. Training pipelines

The article does not describe the training of the underlying LLM (e.g., Claude Code). It focuses on the application framework built around the pre-trained model.

*   **Tooling**:
    *   LLM: Claude Code
    *   Build/Test Tools: Maven (`mvn`)
    *   Agent Framework: Custom-built, using a "Model Context Protocol (MCP)" to define tools.
    *   Containerization: The agent runs in a sandboxed container.
*   **Automation**: The verification loop is automated. For the Claude Code model, the system uses the `stop hook` to run all relevant verifiers before the agent attempts to open a PR.
*   **Experiment Tracking**: Currently informal. The team plans to implement robust evaluations to systematically assess changes to system prompts, agent architectures, and LLM providers.

### 10. Features

The "features" are the inputs provided to the various components of the system.

*   **Agent Inputs**:
    *   **Prompt**: A natural language description of the task.
    *   **Source Code**: The full codebase of the target component.
*   **Verifier Inputs**:
    *   **File System State**: Verifiers are triggered by the presence of specific files (e.g., `pom.xml`).
    *   **Generated Code**: The verifiers operate on the code modified by the agent.
*   **Judge LLM Inputs**:
    *   **Original Prompt**: The instructions given to the agent.
    *   **Code Diff**: The `git diff` of the changes proposed by the agent.

The system is designed to abstract away noisy, low-value information (like verbose build logs) from the agent's context window, effectively performing feature selection to help the agent focus.

### 11. Measuring results

#### 11.1. Offline evaluation

There is no formal, structured evaluation ("evals") framework in place yet for the judge or the overall system. However, the team relies on empirical observations and internal metrics from production usage.

*   **Judge Performance**: The judge vetoes ~25% of agent sessions.
*   **Agent Self-Correction**: The agent successfully course-corrects in 50% of the cases where the judge vetoes the change.
*   **Qualitative Analysis**: The most common reason for a judge veto is the agent going outside the scope of the prompt.

Future work includes building a robust evaluation framework to benchmark different LLMs, prompts, and agent architectures.

#### 11.2. A/B testing

[NO INFO]

### 12. Integration and Serving

#### 12.1. API and serving architecture

*   **Architecture**: The system is an agentic framework where the core agent has a very limited scope.
    *   **Agent**: Runs in a sandboxed container. It can read the codebase, use tools to edit files, and execute verifiers. It uses an LLM like Claude Code.
    *   **Surrounding Infrastructure**: Handles more complex tasks like pushing code to version control, interacting with users on Slack, and authoring prompts. This separation makes the agent more predictable and secure.
*   **Serving Pattern**: The agent runs as a background process to generate a code change, culminating in a pull request. It is not a real-time serving system.
*   **Tool Integration**: Verifiers are exposed to the agent as tools via a "Model Context Protocol (MCP)". The agent is instructed to always call the `verify` tool before completing its task.

#### 12.2. SLAs and fallback

*   **SLA**: [NO INFO]
*   **Fallback**: If the agent fails to produce a PR, or if the verification loop fails and the agent cannot correct the issue, the PR is not opened. The fallback is for a human engineer to perform the change manually.

### 13. Monitoring

*   **Model Quality**: The "LLM as a Judge" acts as a real-time monitor for the quality and relevance of the agent's output. The veto rate is a key metric.
*   **Data Quality / Engineering**: The deterministic verifiers (format, build, test) monitor the syntactic and functional correctness of the generated code before it becomes a PR. Failure of any verifier is an alert that blocks the PR creation and notifies the user.
*   **Future Monitoring**: Planned integration with CI/CD pipelines will provide an additional "outer loop" of monitoring and validation on the created pull requests.

### 14. Operations

#### 14.1. Retraining and maintenance

The system is not retrained in a traditional sense. Maintenance and improvement involve:
*   **Expanding Verifier Infrastructure**: A key area for future work is to add support for more hardware (macOS, ARM64) and operating systems to broaden the agent's applicability.
*   **Prompt Engineering**: Future evaluations will systematically assess changes to system prompts.
*   **Agent Architecture**: The team plans to experiment with new agent architectures.

#### 14.2. Incident response

*   **Rollback**: If a verifier fails, the PR is not opened, preventing a bad change from entering the review process.
*   **Manual Override**: The ultimate fallback is for an engineer to take over the task manually.
*   **User Notification**: If a PR cannot be opened due to a verification failure, the user is presented with an error message. Surrounding infrastructure handles user communication (e.g., via Slack).