# Acceptance Criteria: SPEC-UI-I18N-001

**SPEC ID:** SPEC-UI-I18N-001
**Title:** Dashboard Multi-Language Support Acceptance Criteria
**Created:** 2026-02-01

---

## Overview

This document defines the acceptance criteria for multi-language support in the Communication Server dashboard using Given-When-Then format for test scenarios.

---

## Test Scenarios

### Functional Scenarios

#### Scenario 1: Initial Dashboard Load with Korean Default

**Given** a user opens the dashboard for the first time
**And** no language preference is stored in localStorage
**When** the dashboard completes loading
**Then** all UI text **shall** display in Korean
**And** the language toggle **shall** show 한국어 as selected

---

#### Scenario 2: Initial Dashboard Load with Saved English Preference

**Given** a user has previously selected English
**And** `localStorage.dashboard_language` equals "en"
**When** the dashboard completes loading
**Then** all UI text **shall** display in English
**And** the language toggle **shall** show English as selected

---

#### Scenario 3: Language Toggle from Korean to English

**Given** the dashboard is displaying in Korean
**When** the user clicks the language toggle
**And** selects "English" from the dropdown
**Then** all UI text **shall** update to English immediately without page refresh
**And** `localStorage.dashboard_language` **shall** be set to "en"
**And** the language toggle **shall** show English as selected

---

#### Scenario 4: Language Toggle from English to Korean

**Given** the dashboard is displaying in English
**When** the user clicks the language toggle
**And** selects "한국어" from the dropdown
**Then** all UI text **shall** update to Korean immediately without page refresh
**And** `localStorage.dashboard_language` **shall** be set to "ko"
**And** the language toggle **shall** show 한국어 as selected

---

#### Scenario 5: Language Persistence Across Page Reload

**Given** a user has selected English
**And** `localStorage.dashboard_language` equals "en"
**When** the user refreshes the page
**Then** the dashboard **shall** load displaying in English
**And** the language toggle **shall** show English as selected

---

#### Scenario 6: Missing Translation Key Fallback

**Given** a translation key is missing in the current language file
**When** the UI attempts to display text for that key
**Then** the system **shall** fallback to the other language's translation
**And** if both languages lack the key, display the raw key in brackets

---

#### Scenario 7: API Returns Valid Translations

**Given** the backend i18n API is running
**When** a client sends `GET /api/v1/i18n/ko`
**Then** the response **shall** have status 200
**And** the response **shall** contain a JSON object with translation key-value pairs
**And** the response **shall** include common translations for "dashboard", "stats", "connection"

---

#### Scenario 8: API Rejects Invalid Language Code

**Given** the backend i18n API is running
**When** a client sends `GET /api/v1/i18n/invalid`
**Then** the response **shall** have status 400
**And** the response **shall** contain an error message indicating unsupported language

---

#### Scenario 9: Supported Languages List

**Given** the backend i18n API is running
**When** a client sends `GET /api/v1/i18n/languages`
**Then** the response **shall** have status 200
**And** the response **shall** contain a "languages" array with ko and en entries
**And** each language entry **shall** include code, name, and native_name fields

---

#### Scenario 10: WebSocket Messages Use Current Language

**Given** the dashboard is displaying in English
**When** a WebSocket message arrives with status information
**Then** the status labels **shall** display in English
**And** timeline event types **shall** display in English

---

### UI Component Scenarios

#### Scenario 11: Stat Cards Translate Correctly

**Given** the language is set to English
**When** the stat cards render
**Then** "전체 에이전트" **shall** display as "Total Agents"
**And** "활성화 에이전트" **shall** display as "Active Agents"
**And** "전체 메시지" **shall** display as "Total Messages"

---

#### Scenario 12: Connection Status Translates Correctly

**Given** the language is set to English
**When** the connection status is "connected"
**Then** "연결됨" **shall** display as "Connected"
**And** "연결 중..." **shall** display as "Connecting..."
**And** "연결 해제" **shall** display as "Disconnected"

---

#### Scenario 13: Agent Status Labels Translate

**Given** the language is set to English
**When** agent cards render with status "online"
**Then** "온라인" **shall** display as "Online"
**And** "활성" **shall** display as "Active"
**And** "오프라인" **shall** display as "Offline"

---

#### Scenario 14: Form Labels Translate

**Given** the language is set to English
**When** the agent registration form displays
**Then** "새 에이전트 등록" **shall** display as "Register New Agent"
**And** "닉네임" **shall** display as "Nickname"
**And** "API 키 생성" **shall** display as "Generate API Key"

---

#### Scenario 15: Error Messages Translate

**Given** the language is set to English
**When** an error occurs during API communication
**Then** error messages **shall** display in English
**And** error dialogs **shall** have English titles and buttons

---

### Performance Scenarios

#### Scenario 16: Translation Load Performance

**Given** a user with empty cache
**When** the dashboard loads for the first time
**Then** translation files **shall** load within 100ms
**And** UI text **shall** not display raw keys during loading

---

#### Scenario 17: Language Switch Performance

**Given** the dashboard is fully loaded
**When** the user switches languages
**Then** all UI text **shall** update within 100ms
**And** no flickering **shall** occur during transition

---

### Edge Cases

#### Scenario 18: Corrupted localStorage Value

**Given** `localStorage.dashboard_language` contains an invalid value like "xyz"
**When** the dashboard loads
**Then** the system **shall** fallback to Korean
**And** **shall** clear the invalid value from localStorage

---

#### Scenario 19: Network Error Loading Translations

**Given** the i18n API is unreachable
**When** the dashboard attempts to load translations
**Then** the system **shall** display cached translations if available
**Or** fallback to embedded English translations
**And** **shall** show a notification about translation loading error

---

#### Scenario 20: Browser Language Detection

**Given** a user with browser set to English (`navigator.language = "en-US"`)
**And** no localStorage preference exists
**When** the dashboard loads for the first time
**Then** the system **shall** detect browser language
**And** **shall** default to English if supported
**Or** fallback to Korean if browser language is not supported

---

## Quality Gate Criteria

### Code Quality

- [ ] All translation keys follow dot notation (e.g., `dashboard.title`)
- [ ] No hardcoded Korean or English text in HTML/JS after migration
- [ ] Translation files have consistent structure across languages
- [ ] Missing keys are logged in development mode

### Test Coverage

- [ ] Unit tests for I18n class methods (>80% coverage)
- [ ] Integration tests for API endpoints
- [ ] E2E tests for complete language toggle flow
- [ ] Visual regression tests for each language

### Documentation

- [ ] Translation key naming convention documented
- [ ] Guide for adding new languages documented
- [ ] API documentation for i18n endpoints

### User Experience

- [ ] Language switch requires <= 2 clicks
- [ ] Language preference persists indefinitely
- [ ] No page refresh required for language switch
- [ ] Smooth transition animation (optional enhancement)

---

## Definition of Done

**SPEC-UI-I18N-001 is complete when:**

1. Backend `/api/v1/i18n/*` endpoints are implemented and tested
2. Frontend I18n class is implemented with localStorage persistence
3. Translation files exist for Korean and English with full coverage
4. All hardcoded text in dashboard is replaced with translation keys
5. Language toggle component is visible and functional in header
6. All acceptance criteria scenarios pass
7. Test coverage exceeds 80% for i18n-related code
8. No regression in existing dashboard functionality

---

## Test Execution Plan

### Unit Tests

```bash
# Run i18n unit tests
pytest tests/unit/test_i18n.py -v
pytest tests/unit/test_i18n_api.py -v
```

### Integration Tests

```bash
# Run i18n integration tests
pytest tests/integration/test_language_switching.py -v
```

### E2E Tests

```bash
# Run E2E tests with Playwright
pytest tests/e2e/test_dashboard_language.py -v
```

### Manual Testing Checklist

- [ ] Open dashboard in new incognito window - verify Korean default
- [ ] Switch to English - verify all text updates
- [ ] Refresh page - verify English persists
- [ ] Switch back to Korean - verify all text updates
- [ ] Test all major user flows in both languages

---

**END OF ACCEPTANCE CRITERIA - SPEC-UI-I18N-001**
