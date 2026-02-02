# Implementation Plan: SPEC-DASHBOARD-001

## TAG BLOCK

```
SPEC_ID: SPEC-DASHBOARD-001
VERSION: 1.0
LAST_UPDATED: 2026-02-01
STATUS: Planned
ASSIGNED: TBD
```

## Milestones

### Primary Goal (P0) - Fix Agent List Display

**Objective**: Resolve field name mismatch causing agent list to not display properly.

**Tasks**:
1. Update `createAgentCard()` function to use `agent_id` instead of `display_id`
2. Update `renderAgents()` function to properly pass agent data
3. Test agent card rendering with various agent statuses

**Success Criteria**:
- Agent list displays all registered agents
- Each agent card shows correct display ID, nickname, status, and capabilities
- No "undefined" values in agent cards

**Dependencies**: None

---

### Secondary Goal (P1) - Fix Agent Management Table

**Objective**: Resolve field name mismatch causing agent management table to not display properly.

**Tasks**:
1. Update `createAgentManagementRow()` function to use `agent_id` instead of `id` and `display_id`
2. Update `handleDeleteAgent()` function to use correct agent ID
3. Test agent deletion functionality

**Success Criteria**:
- Agent management table displays all registered agents
- Each row shows correct status, nickname, and display ID
- Delete buttons work correctly with proper agent ID

**Dependencies**: Primary Goal

---

### Final Goal (P2) - Verify Message Timeline Display

**Objective**: Ensure message timeline displays correctly with proper agent references.

**Tasks**:
1. Verify `createTimelineItem()` function handles agent IDs correctly
2. Test timeline rendering with various message types
3. Verify agent display in timeline events

**Success Criteria**:
- Message timeline displays correctly
- Each timeline event shows proper sender and recipient information
- Agent IDs are correctly formatted and displayed

**Dependencies**: Primary Goal

---

## Technical Approach

### Strategy Overview

**Approach**: Frontend-only fixes with API field name alignment

**Rationale**:
- The backend API structure is correct and well-defined
- The frontend code has inconsistent field name usage
- Fixing frontend is less disruptive than changing API contracts
- Maintains backward compatibility with any other API consumers

### Architecture Changes

**Component: dashboard.js**

**Files to Modify**:
- `src/communication_server/static/js/dashboard.js`

**Changes Required**:

1. **Function: `createAgentCard(agent)`** (Line ~381)
   - Change: `const { display_id, ... } = agent;`
   - To: `const { agent_id, full_id, ... } = agent;`
   - Update all references to `display_id` → `agent_id`

2. **Function: `createAgentManagementRow(agent)`** (Line ~978)
   - Change: `const { id, nickname, display_id, status } = agent;`
   - To: `const { agent_id, full_id, nickname, status } = agent;`
   - Update all references to `id` → `agent_id`
   - Update all references to `display_id` → `agent_id`

3. **Function: `createTopAgentsChart(ctx, data)`** (Line ~532)
   - Update fallback logic to use `agent_id` consistently
   - Change: `display_id || agent_id` → `agent_id`

4. **Function: WebSocket message handler** (Line ~724)
   - Update agent finding logic to use `agent_id` consistently
   - Change: `a.agent_id === agent_id || a.display_id === agent_id`
   - To: `a.agent_id === agent_id`

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Dashboard                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐         ┌─────────────┐      ┌──────────────┐  │
│  │  Frontend   │         │    API      │      │   Backend    │  │
│  │  JavaScript │────────▶│   Client    │─────▶│  FastAPI     │  │
│  │             │         │             │      │              │  │
│  └─────────────┘         └─────────────┘      └──────────────┘  │
│       │                         │                      │         │
│       │ 1. Request agents       │                      │         │
│       │                         │                      │         │
│       │                         │ 2. Query agents      │         │
│       │                         │                      │         │
│       │                         │                      │         │
│       │                         │ 3. Return JSON       │         │
│       │◀─────────────────────────│◀─────────────────────│         │
│       │    {                     │                      │         │
│       │      "agents": [{        │                      │         │
│       │        "agent_id": "...", │                      │         │
│       │        "full_id": "...", │                      │         │
│       │        "nickname": "...",│                      │         │
│       │        ...              │                      │         │
│       │      }]                 │                      │         │
│       │    }                    │                      │         │
│       │                         │                      │         │
│       │ 4. Render with          │                      │         │
│       │    agent_id             │                      │         │
│       │                         │                      │         │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Phases

**Phase 1: Analysis and Setup**
- Create backup of current dashboard.js
- Identify all locations using `display_id`, `id` for agent references
- Document expected behavior changes

**Phase 2: Frontend Fixes**
- Update `createAgentCard()` function
- Update `createAgentManagementRow()` function
- Update chart and timeline functions
- Update WebSocket handlers

**Phase 3: Testing**
- Manual testing of agent list display
- Manual testing of agent management table
- Manual testing of delete operations
- Manual testing of message timeline

**Phase 4: Quality Gates**
- Run ESLint to ensure no syntax errors
- Verify all displays work correctly
- Verify delete operations work
- Verify timeline displays correctly

## Risk Analysis

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing functionality | Medium | High | Comprehensive testing before and after changes |
| Missing field references | Low | Medium | Grep search for all occurrences |
| WebSocket handler issues | Low | Medium | Test real-time updates |
| Timeline display issues | Low | Low | Verify with sample data |

### Implementation Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Incomplete field replacement | Medium | High | Systematic grep and replace |
| Missed edge cases | Low | Medium | Manual code review |
| Testing gaps | Medium | Medium | Test coverage checklist |

## Quality Assurance

### Test Coverage

**Unit Testing**:
- Manual verification of each function change
- Visual inspection of rendered output

**Integration Testing**:
- End-to-end dashboard load test
- Agent registration flow test
- Agent deletion flow test
- Message timeline rendering test

### Acceptance Testing

**Pre-Deployment Checklist**:
- [ ] Agent list displays all agents correctly
- [ ] Agent cards show proper IDs and status
- [ ] Agent management table displays correctly
- [ ] Delete buttons work with proper IDs
- [ ] Message timeline displays correctly
- [ ] No console errors on page load
- [ ] WebSocket updates work correctly
- [ ] All agent statuses display properly

## Deployment Strategy

**Deployment Type**: Hotfix

**Steps**:
1. Create feature branch from main
2. Implement changes
3. Test locally
4. Create pull request
5. Code review
6. Merge to main
7. Deploy to development environment
8. Verify in development
9. Deploy to production

**Rollback Plan**:
- Revert commit if critical issues found
- Restore previous version of dashboard.js

## Dependencies

**Internal Dependencies**:
- `src/communication_server/static/js/api.js` - API client (no changes needed)
- `src/communication_server/static/js/i18n.js` - Internationalization (no changes needed)

**External Dependencies**:
- None - purely frontend JavaScript changes

## Success Metrics

**Functional Metrics**:
- Agent list displays 100% of registered agents
- Agent management table displays 100% of registered agents
- Delete operations succeed with correct agent IDs
- Message timeline displays 100% of events correctly

**Quality Metrics**:
- Zero JavaScript console errors
- Zero undefined values in displays
- All TRUST 5 principles maintained

## References

- Project Structure: `.moai/project/structure.md`
- Technical Stack: `.moai/project/tech.md`
- Related SPEC: `SPEC-UI-MESSAGES-001` (Message list functionality)
