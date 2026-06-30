# Plan-reviewer review modes product direction

Session-derived product direction from Aaron while planning Hermes collaboration on top of `plan-reviewer`.

## Core reframing

Do not frame the next evolution as merely “generic artifact reviewer” or “plan reviewer plus exceptions.” Reframe it as **review modes** over a shared HTML review substrate.

The shared substrate should include:

- HTML document hosting/rendering
- safe no-script rendered document surface unless a later security plan changes it
- DOM/text/image selection and markers
- durable comments
- threaded conversations
- pub/sub / queue-backed comment delivery
- source sync and safe rendered-version refresh
- agent delivery infrastructure

## Initial modes

### Planning mode

Planning mode is the existing reviewed-plan workflow expressed as a mode:

- each comment iterates on the plan
- threaded conversations support clarification and follow-up
- plan-specific buttons/actions remain at the top of the screen
- plan-specific document format is enforced
- execution-readiness metadata and planning index semantics remain intact

### Collaboration mode

Collaboration mode is for conversing with an agent through a document:

- each comment is a conversation with an agent about the selected document context
- agent responses appear as inline thread replies
- the agent may update the document in response to the conversation
- no planning-specific buttons appear at the top of the screen
- no planning-specific document format is enforced
- collaboration-specific buttons may be added later, after the basic comment-thread/update loop works

## Planning implication

When creating or revising plans for `plan-reviewer` features around Hermes, HTML artifacts, comments, or document collaboration:

1. Prefer an explicit `Review modes` section near the top.
2. Name shared infrastructure separately from mode-specific policy.
3. Preserve backwards compatibility by treating existing reviewed plans as planning-mode documents.
4. Test both mode-specific behavior and shared-substrate behavior.
5. Do not duplicate selection/comment/queue/thread infrastructure per mode; mode policy should configure common substrate behavior.
