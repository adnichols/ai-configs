---
name: product-evals
description: Evaluate an AI product or agent workflow using complete task traces, human-reviewed failure modes, and matched improvement runs. Use when designing evals, auditing a score, or trying to improve agent task success.
---

# Product evals

Start from the user outcome the product is meant to deliver. Inspect the current eval, its task corpus, and several complete runs before changing a score or writing a grader. A command syntax score, model benchmark, or plausible final answer does not establish task success.

## Find failures

1. Gather authorized real task traces when available. A trace needs the request, relevant instructions, actions and tool arguments, returned data and errors, and final answer or persisted result. Record model, tool and skill versions, and cost or timing when available. Keep credentials and protected content within their access boundary.
2. Select examples across task types and outcomes, including random examples. If needed, make a small review view that shows the output as its user saw it and lets the reviewer inspect intermediate evidence. Ask the product owner to describe failures in free text before showing agent-suggested labels. When a failure appears, inspect more instances and a few apparent successes. Record changes to the definition of success.
3. Group reviewed failures by the first meaningful step that went wrong and the user-visible effect. Count prevalence only in a representative sample; mark deliberately selected hard cases separately. If real traces leave a gap, generate realistic tasks by varying task, data shape, and ambiguity, label them synthetic, and execute the full workflow against known ground truth.

## Turn findings into checks

For each priority failure, name a reviewed failing example, a passing example, the source of truth, and the most likely false pass. Prefer a direct check of tool results or final state for objective behavior. Use a model judge only for criteria that require judgment; compare it with human labels on separate development and held-out cases, report how often it recognizes both passes and failures, and inspect disagreements before using it as a gate.

Keep different outcomes visible: task completion, evidence quality, authorization and safety, and efficiency. A safety or authority violation fails the task. Measure calls, time, and tokens among successful runs so a fast wrong answer cannot improve the result. Show counts and denominators by task family alongside any overall score.

## Test an improvement

Run the same tasks against baseline and candidate with the same data, model, effort, permissions, and tool access. Check the final answer or persisted state against independent ground truth. Repeat close results when run variance could change the decision. Report gains, regressions, uncertainty, and the next smallest fix supported by the traces.

For graph agents such as Ava, inspect scope and query choice, pagination and freshness, relationship direction and type, conflicting claims, revision and authorization controls, and readback after writes. The project spec determines the exact pass rule.

Method informed by [Hamel Husain and Shreya Shankar's error discovery article](https://www.lennysnewsletter.com/p/advanced-evals-how-to-find-and-fix). Their [upstream eval skills](https://github.com/ai-evals-course/evals-skills) are a separate package; this skill contains original guidance and does not vendor that package.
