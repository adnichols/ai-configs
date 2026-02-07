---
description: Create a code simplification plan with analysis and agent selection. Usage: [Target directory/files to analyze]
---

# Rule: Generating a Code Simplification Plan

## Goal

To guide an AI assistant in creating a detailed Code Simplification Plan with appropriate agent selection and careful cleanup recommendations while ensuring absolute preservation of core functionality. Think harder.

## Simplification Approach

This command uses a comprehensive approach to code simplification that:

1. **Analyze Project Structure:** Examine existing project files to understand architecture and patterns
2. **Conservative Cleanup Approach:** Use careful, evidence-based simplification with comprehensive testing
3. **Quality Review Integration:** Use appropriate quality reviewer agents for validation
4. **Apply Safety Safeguards:** Include comprehensive validation requirements to ensure functionality preservation

## Process

1. **Receive Target Scope:** The user provides a directory path, file pattern, or specific files to analyze for simplification opportunities. If not provided, review entire current directory.
2. **Analyze Project Structure:** Examine existing project files and architecture:
   - Review codebase characteristics and patterns
   - Identify key components and dependencies
   - Understand existing testing and quality measures
3. **Conservative Planning Approach:** Use careful, evidence-based simplification strategy:
   - Prioritize safety and functionality preservation
   - Require comprehensive validation for all changes
   - Focus on clear evidence-based cleanup opportunities
4. **Check Backward Compatibility:** Review for any backward compatibility requirements
5. **Ensure Working Branch:** Operate on a feature branch, create one if needed for these changes
6. **Review Recent Changes:** Leverage git history to identify recent changes to the current repository
7. **Test Coverage Assessment:** Verify existing test coverage is adequate for safe simplification
8. **Generate Simplification Plan:** Use the @simplify-planner agent to analyze the codebase and create a detailed plan
9. **Quality Review:** Use quality reviewer agent for comprehensive plan review and safety validation
10. **Save Plan:** Save the generated plan as `simplify-plan-[area-name].md` inside the `/tasks` directory

## Pre-Simplification Requirements

Before generating any simplification plan, ensure comprehensive safety requirements:

1. **Test Coverage Verification:**
   - Analyze existing test coverage for the target area (aim for comprehensive coverage)
   - Identify gaps in test coverage for core functionality
   - Document current test structure and quality
   - Favor integration tests and end-to-end scenarios where possible
   - Minimize mocks and stubs where possible, use real scenarios

2. **Recent Change Analysis:**
   - Review git history for recent modifications
   - Identify areas of frequent change or bug fixes
   - Understand evolution patterns and complexity accumulation

3. **Dependency Mapping:**
   - Identify all external dependencies on the target code
   - Map integration points and API contracts
   - Document concurrent behavior and thread safety requirements

## Simplification Plan Structure

The generated plan should include the following sections as a checklist:

### Phase 1: Preparation and Safety Verification
- [ ] **P1.1: Baseline Test Execution**
  - [ ] Run full test suite to establish baseline
  - [ ] Document current test coverage percentage
  - [ ] Identify any existing test failures

- [ ] **P1.2: Test Coverage Enhancement** (if needed)
  - [ ] Create missing unit tests for core functionality
  - [ ] Add integration tests for critical paths
  - [ ] Implement regression tests for identified edge cases

- [ ] **P1.3: Complexity Analysis**
  - [ ] Complete @simplify-planner codebase archaeology
  - [ ] Document evidence of unused/deprecated code
  - [ ] Identify consolidation opportunities
  - [ ] Map preservation requirements

### Phase 2: Plan Review and Validation
- [ ] **P2.1: Comprehensive Quality Review**
  - [ ] Submit plan to quality reviewer agent (e.g., @quality-reviewer)
  - [ ] Apply thorough review depth and comprehensive safety checks
  - [ ] Update plan to address all safety concerns or gaps identified
  - [ ] Confirm strong preservation guarantees for all functionality

- [ ] **P2.2: Risk Assessment**
  - [ ] Document all identified risks
  - [ ] Create mitigation strategies
  - [ ] Define success criteria
  - [ ] Establish monitoring approach

- [ ] **P2.3: Plan Summary and User Review**
  - [ ] Provide comprehensive summary of proposed changes
  - [ ] Highlight all areas to be modified and cleanup targets
  - [ ] Present risk assessment and mitigation strategies
  - [ ] Wait for explicit user approval before proceeding
  - [ ] Address any user concerns or modifications
  - [ ] Do NOT proceed to Phase 3 without user confirmation

### Phase 3: Implementation Steps
- [ ] **P3.1: Pre-Implementation Verification**
  - [ ] Re-run full test suite
  - [ ] Create git branch for simplification work
  - [ ] Document current system state

- [ ] **P3.2: Surgical Cleanup Execution**
  - [ ] [Specific cleanup step 1]
  - [ ] [Specific cleanup step 2]
  - [ ] [Specific cleanup step N]

- [ ] **P3.3: Post-Cleanup Validation**
  - [ ] Run full test suite after each major cleanup
  - [ ] Verify functionality preservation
  - [ ] Performance regression testing
  - [ ] Integration point validation

### Phase 4: Completion and Documentation
- [ ] **P4.1: Final Verification**
  - [ ] Complete system integration testing
  - [ ] User acceptance criteria validation
  - [ ] Performance benchmarking

- [ ] **P4.2: Documentation and Cleanup**
  - [ ] Update code documentation
  - [ ] Remove temporary files and artifacts
  - [ ] Create deployment notes
  - [ ] Archive simplification artifacts

## Agent Responsibilities

### Current Agent (Orchestrator)
- Plan creation and coordination
- Git branch management
- Progress tracking and checklist updates
- Quality gates and safety verification

### @simplify-planner Agent
- Codebase complexity analysis
- Evidence-based cleanup recommendations
- Preservation strategy design
- Risk identification and mitigation planning

### @quality-reviewer Agent
- Plan safety review
- Risk assessment validation
- Quality gate approval

## Safety Requirements

1. **Unconditional Functionality Preservation:**
   - All user-facing behavior must remain identical
   - No core functionality degradation allowed
   - All integration points must remain intact

2. **Evidence-Based Decisions:**
   - Concrete proof required for all removal decisions
   - Usage analysis with grep/git evidence
   - Deprecation timeline documentation

3. **Comprehensive Testing:**
   - Test coverage must be adequate before cleanup
   - Performance benchmarks maintained

4. **Rollback Preparedness:**
   - Git branch strategy for safe experimentation
   - Rollback involves reverting git changes, keep risky changes on their own commit

## Output

- **Format:** Markdown (`.md`)
- **Location:** `/tasks/`
- **Filename:** `simplify-plan-[area-name].md`

## Final Instructions

1. Do NOT start implementing any simplification
2. Ensure all checklist items are specific and actionable
3. Verify @simplify-planner agent provides evidence for all recommendations
4. Incorporate @quality-reviewer feedback into the plan where appropriate before proceeding
5. Remember: This creates the PLAN only - execution happens via simplify:process-plan.md
