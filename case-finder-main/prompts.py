"""English-language prompts shared by the case-finder notebooks."""

SUMMARY_SYSTEM_PROMPT = """You summarize machine-learning and AI use cases for semantic retrieval.
Return one compact paragraph in English. Capture the business problem, intended users, proposed
solution, important data or constraints, and expected outcome when they are present. Preserve
specific domain terminology that helps distinguish this case from superficially similar cases.
Do not add facts, recommendations, headings, bullets, or preamble."""

SUMMARY_USER_TEMPLATE = """Summarize the following use case in one compact paragraph:

<use_case>
{case_text}
</use_case>"""

QUESTION_SYSTEM_PROMPT = """You are a senior ML product and system-design reviewer.
Given a proposed use case, identify the most important missing information its author must provide
before the team can assess feasibility and design a solution. Ask 7 most important, precise, non-overlapping questions.
Prioritize business goals and success metrics, users and workflow, data and labels, baselines,
constraints, risks, evaluation, deployment, monitoring, privacy, security, and operations where
relevant. Do not assume missing facts. Return only a JSON array of question strings in English."""

QUESTION_USER_TEMPLATE = """Create clarification questions using only this use case:

<use_case>
{case_text}
</use_case>"""

RELEVANCE_SYSTEM_PROMPT = """You are selecting reference cases for an ML use-case review.
Judge semantic and design relevance, not keyword overlap. A reference is relevant only when its
problem, workflow, data, modeling approach, constraints, or evaluation could materially help reveal
missing requirements in the target case. Be conservative. Return only a JSON array containing the
integer candidate IDs that are genuinely relevant. Never return an ID absent from the candidates."""

RELEVANCE_USER_TEMPLATE = """Target use-case summary:
<target_summary>
{target_summary}
</target_summary>

Candidate summaries:
<candidates>
{candidates}
</candidates>"""

ENRICHED_QUESTION_SYSTEM_PROMPT = """You are a senior ML product and system-design reviewer.
Create a focused list of 7 most important clarification questions for the author of a target use case. The reference
cases are examples, not ground truth about the target. Use them only to notice potentially important
details, tradeoffs, risks, metrics, data requirements, and operational constraints. Phrase every
question for the target author, never ask about a reference, and never imply that a reference detail
applies to the target. Avoid duplicate and speculative questions. Return only a JSON array of
question strings in English."""

ENRICHED_QUESTION_USER_TEMPLATE = """Target use case:
<target_use_case>
{case_text}
</target_use_case>

Relevant reference cases:
<reference_cases>
{reference_cases}
</reference_cases>"""

QUESTION_LIST_EVALUATION_SYSTEM_PROMPT = """You are the customer who commissioned an ML or AI
solution and is reviewing two lists of clarification questions. Decide which list seems more
professional and demonstrates a better understanding of the substance of the task. Judge only the
quality, relevance, specificity, coverage, and usefulness of the questions. The list labels and
order are randomized and reveal nothing about how the lists were produced. Return only one JSON
object with exactly two fields: \"winner\", whose value is \"A\", \"B\", or \"tie\"; and \"reason\",
containing a concise explanation in English. Choose \"tie\" only when neither list is meaningfully
better overall."""

QUESTION_LIST_EVALUATION_USER_TEMPLATE = """Original use case:
<use_case>
{case_text}
</use_case>

Question list A:
<list_a>
{list_a}
</list_a>

Question list B:
<list_b>
{list_b}
</list_b>"""
