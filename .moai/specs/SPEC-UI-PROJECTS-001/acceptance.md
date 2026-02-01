# Acceptance Criteria: SPEC-UI-PROJECTS-001

**SPEC ID:** SPEC-UI-PROJECTS-001
**Title:** Project-Based Agent Filtering UI Acceptance Criteria
**Created:** 2026-02-01

---

## Overview

This document defines the acceptance criteria for project-based agent filtering UI using Given-When-Then format for test scenarios.

---

## Test Scenarios

### Functional Scenarios

#### Scenario 1: Display Project Sidebar

**Given** a user opens the dashboard
**When** the dashboard completes loading
**Then** a project sidebar **shall** be visible on the left side
**And** the sidebar **shall** have a "Projects" header
**And** the sidebar **shall** display an "All Agents" channel

---

#### Scenario 2: List All Projects

**Given** the system has 3 registered projects (Project A, Project B, Project C)
**When** the dashboard loads
**Then** the sidebar **shall** display 3 project channels
**And** each channel **shall** show the project name
**And** each channel **shall** show the agent count

---

#### Scenario 3: Select Project to Filter Agents

**Given** the dashboard is displaying all agents
**And** Project A has 2 agents
**When** the user clicks on "Project A" channel
**Then** the agent grid **shall** display only the 2 agents from Project A
**And** Project A channel **shall** be visually marked as active
**And** stats cards **shall** update to show Project A counts

---

#### Scenario 4: Select All Agents Channel

**Given** the user has selected "Project A" channel
**And** the system has 5 total agents across all projects
**When** the user clicks on "All Agents" channel
**Then** the agent grid **shall** display all 5 agents
**And** "All Agents" channel **shall** be visually marked as active
**And** stats cards **shall** update to show total counts

---

#### Scenario 5: Project Online Status Indicator

**Given** Project A has 2 agents with 1 online
**And** Project B has 3 agents with 0 online
**When** the sidebar renders
**Then** Project A channel **shall** display an online (green) status indicator
**And** Project B channel **shall** display an offline (gray) status indicator

---

#### Scenario 6: Agent Count Updates

**Given** the sidebar is displaying Project A with 2 agents
**When** a new agent registers for Project A
**Then** Project A's agent count **shall** update to 3
**And** the update **shall** occur via WebSocket or polling

---

#### Scenario 7: Collapse Sidebar

**Given** the sidebar is visible
**When** the user clicks the collapse button in the sidebar header
**Then** the sidebar **shall** collapse to 60px width
**And** project names **shall** be hidden
**And** project icons **shall** remain visible

---

#### Scenario 8: Expand Sidebar

**Given** the sidebar is collapsed
**When** the user clicks the expand button
**Then** the sidebar **shall** expand to full width (240px)
**And** project names **shall** become visible

---

#### Scenario 9: Project Selection Persists

**Given** the user has selected "Project A"
**And** `localStorage.selectedProject` equals "project-a"
**When** the user refreshes the page
**Then** the dashboard **shall** load with "Project A" pre-selected
**And** the agent grid **shall** show only Project A agents

---

#### Scenario 10: Empty Project Handling

**Given** Project X exists but has 0 agents
**When** the sidebar renders
**Then** Project X channel **shall** be displayed
**And** the agent count **shall** show "0"
**And** the status indicator **shall** be gray (offline)

---

### API Scenarios

#### Scenario 11: Projects API Returns List

**Given** the backend has 2 registered projects
**When** a client sends `GET /api/v1/projects`
**Then** the response **shall** have status 200
**And** the response **shall** contain a "projects" array with 2 entries
**And** each project **shall** include project_id, name, agent_count, active_count

---

#### Scenario 12: Filter Agents by Project

**Given** the system has agents from multiple projects
**When** a client sends `GET /api/v1/status/agents?project_id=project-a`
**Then** the response **shall** have status 200
**And** the response agents **shall** only include agents with project_id="project-a"

---

#### Scenario 13: Get All Agents Without Filter

**Given** the system has agents from multiple projects
**When** a client sends `GET /api/v1/status/agents` (no project_id)
**Then** the response **shall** have status 200
**And** the response agents **shall** include all agents regardless of project

---

### UI/UX Scenarios

#### Scenario 14: Active Channel Styling

**Given** "Project A" channel is selected
**When** the sidebar renders
**Then** "Project A" channel **shall** have a distinct background color
**And** "Project A" channel **shall** have a left border indicator
**And** other channels **shall** not have active styling

---

#### Scenario 15: Hover Effect on Channels

**Given** the user is viewing the sidebar
**When** the user hovers over any project channel
**Then** the channel **shall** display a hover background color
**And** the cursor **shall** change to pointer

---

#### Scenario 16: Project Tooltip

**Given** a project has a description "Frontend Services Team"
**When** the user hovers over the project channel
**Then** a tooltip **shall** appear showing the description
**And** the tooltip **shall** display project tags if available

---

#### Scenario 17: Keyboard Navigation

**Given** the user is viewing the dashboard
**When** the user presses Cmd/Ctrl+1
**Then** "All Agents" channel **shall** be selected
**When** the user presses Cmd/Ctrl+2
**Then** the first project channel **shall** be selected

---

#### Scenario 18: Mobile Responsive Layout

**Given** the user is on a mobile device (< 1024px width)
**When** the dashboard loads
**Then** the sidebar **shall** be hidden by default
**And** a hamburger menu **shall** be visible
**When** the user taps the hamburger menu
**Then** the sidebar **shall** slide in from the left

---

### Data Integrity Scenarios

#### Scenario 19: Agent Belongs to One Project

**Given** an agent is registered with project_id="project-a"
**When** querying agents for project-a
**Then** the agent **shall** appear in the results
**When** querying agents for project-b
**Then** the agent **shall not** appear in the results

---

#### Scenario 20: Project Deletion Handling

**Given** an agent is associated with a deleted project
**When** the dashboard loads
**Then** the agent **shall** appear in "All Agents" channel
**And** the agent **shall** display its project_id as "unknown"

---

## Quality Gate Criteria

### Code Quality

- [ ] Sidebar component follows existing dashboard patterns
- [ ] Project channel HTML uses semantic structure
- [ ] CSS follows BEM or utility-class convention
- [ ] No inline styles in JavaScript

### Test Coverage

- [ ] Unit tests for ProjectSidebar class (>80% coverage)
- [ ] Integration tests for project API endpoints
- [ ] E2E tests for sidebar interaction
- [ ] Visual regression tests for sidebar states

### Accessibility

- [ ] Sidebar is keyboard navigable
- [ ] Project channels have proper ARIA labels
- [ ] Active state is announced to screen readers
- [ ] Sidebar has proper heading hierarchy

### Performance

- [ ] Sidebar render time < 50ms
- [ ] Project switch latency < 100ms
- [ ] No memory leaks from channel updates

---

## Definition of Done

**SPEC-UI-PROJECTS-001 is complete when:**

1. Backend `/api/v1/projects` endpoint is implemented
2. Agent filtering by project_id is functional
3. Project sidebar is visible and styled
4. All project channels are selectable
5. Agent list updates based on selection
6. Selected project persists in localStorage
7. Sidebar collapse/expand works
8. All acceptance criteria scenarios pass
9. Test coverage exceeds 80% for sidebar code
10. No regression in existing dashboard functionality

---

## Test Execution Plan

### Unit Tests

```bash
# Run sidebar unit tests
pytest tests/unit/test_sidebar.py -v
pytest tests/unit/test_project_api.py -v
```

### Integration Tests

```bash
# Run project filtering integration tests
pytest tests/integration/test_project_filtering.py -v
```

### E2E Tests

```bash
# Run E2E tests with Playwright
pytest tests/e2e/test_project_sidebar.py -v
```

### Manual Testing Checklist

- [ ] Verify sidebar displays on load
- [ ] Click each project channel and verify filter
- [ ] Click "All Agents" and verify all agents shown
- [ ] Test sidebar collapse/expand
- [ ] Test localStorage persistence (refresh page)
- [ ] Verify online/offline status indicators
- [ ] Test mobile responsiveness
- [ ] Verify keyboard shortcuts (if implemented)

---

**END OF ACCEPTANCE CRITERIA - SPEC-UI-PROJECTS-001**
