# Implementation Plan: SPEC-UI-I18N-001

**SPEC ID:** SPEC-UI-I18N-001
**Title:** Dashboard Multi-Language Support Implementation Plan
**Created:** 2026-02-01

---

## Overview

This plan outlines the implementation of multi-language support for the Communication Server dashboard, enabling Korean/English language toggle functionality with persistent preferences.

---

## Implementation Milestones

### Primary Goal (Priority High)

**Milestone 1: Backend Language API**

Implement backend API endpoints for serving translation resources.

**Tasks:**
- Create translation file storage structure
- Implement `GET /api/v1/i18n/{language}` endpoint
- Implement `GET /api/v1/i18n/languages` endpoint
- Add language code validation

**Success Criteria:**
- API returns valid JSON for ko and en
- Invalid language codes return 400 error
- Endpoint response time < 50ms

**Estimated Complexity:** Low

---

### Secondary Goal (Priority Medium)

**Milestone 2: Frontend Translation Infrastructure**

Create frontend JavaScript module for translation management.

**Tasks:**
- Create `i18n/` directory in static files
- Create `ko.json` and `en.json` translation files
- Implement `js/i18n.js` with I18n class
- Add translation key extraction from existing hardcoded text

**Success Criteria:**
- Translation files load without errors
- `t()` function returns correct translations
- Missing keys fallback gracefully

**Estimated Complexity:** Medium

---

### Tertiary Goal (Priority Medium)

**Milestone 3: UI Integration**

Replace hardcoded text with translation keys throughout the dashboard.

**Tasks:**
- Replace text in `index.html` with data-i18n attributes
- Update `dashboard.js` to use `t()` function
- Update `api.js` status labels
- Add language toggle component to header

**Success Criteria:**
- No hardcoded Korean text in HTML/JS
- All UI text updates when language changes
- Language toggle visible and functional

**Estimated Complexity:** High

---

### Final Goal (Priority Low)

**Milestone 4: Polish and Enhancement**

Add polish features and optimize implementation.

**Tasks:**
- Add localStorage persistence
- Implement browser language detection
- Add loading states for translation files
- Add error handling for failed translation loads
- Write tests for translation functionality

**Success Criteria:**
- Language preference persists across page reloads
- Initial language detection from browser
- Graceful handling of network errors

**Estimated Complexity:** Low

---

## Technical Approach

### Directory Structure

```
src/communication_server/
├── static/
│   ├── i18n/
│   │   ├── ko.json
│   │   ├── en.json
│   │   └── index.json (metadata)
│   └── js/
│       └── i18n.js
└── api/
    └── i18n.py (new endpoint)
```

### Translation File Format

```json
{
  "$meta": {
    "language": "ko",
    "name": "한국어",
    "version": "1.0.0"
  },
  "common": {
    "loading": "로딩 중...",
    "error": "오류",
    "refresh": "새로고침"
  },
  "dashboard": {
    "title": "AI Agent Communication",
    "subtitle": "Real-time Status Board",
    "stats": {
      "totalAgents": "전체 에이전트",
      "activeAgents": "활성화 에이전트"
    }
  }
}
```

### I18n Class Design

```javascript
class I18n {
    constructor(options = {}) {
        this.currentLanguage = options.defaultLanguage || 'ko';
        this.fallbackLanguage = options.fallbackLanguage || 'en';
        this.translations = {};
        this.storageKey = options.storageKey || 'dashboard_language';
    }

    async init() {
        // Load preference, then load translations
    }

    async loadLanguage(language) {
        // Fetch from API or load from static files
    }

    t(key, params = {}) {
        // Get translation with parameter interpolation
    }

    setLanguage(language) {
        // Switch language and update UI
    }

    getCurrentLanguage() {
        return this.currentLanguage;
    }
}
```

### HTML Attribute Pattern

Use `data-i18n` attributes for static content:

```html
<h1 data-i18n="dashboard.title">AI Agent Communication</h1>
<span data-i18n="stats.totalAgents">전체 에이전트</span>
```

JavaScript:

```javascript
document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    el.textContent = i18n.t(key);
});
```

### Backend API Implementation

```python
# src/communication_server/api/i18n.py

from fastapi import APIRouter, HTTPException
from pathlib import Path

router = APIRouter(prefix="/i18n", tags=["i18n"])

STATIC_DIR = Path(__file__).parent.parent / "static"
I18N_DIR = STATIC_DIR / "i18n"

SUPPORTED_LANGUAGES = {
    "ko": {"name": "한국어", "native_name": "한국어"},
    "en": {"name": "English", "native_name": "English"},
}

@router.get("/{language}")
async def get_translations(language: str):
    """Get translation strings for specified language."""
    if language not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {language}")

    translation_file = I18N_DIR / f"{language}.json"
    if not translation_file.exists():
        raise HTTPException(status_code=404, detail=f"Translation file not found for {language}")

    import json
    with open(translation_file, encoding="utf-8") as f:
        return json.load(f)

@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages."""
    return {
        "languages": [
            {"code": code, **info}
            for code, info in SUPPORTED_LANGUAGES.items()
        ],
        "default": "ko"
    }
```

---

## Migration Strategy

### Phase 1: Parallel Implementation

Keep existing Korean text while adding i18n infrastructure.

1. Create translation files alongside existing HTML
2. Implement I18n class
3. Test translations in isolation
4. No user-visible changes yet

### Phase 2: Gradual Migration

Replace hardcoded text incrementally.

1. Start with header and navigation
2. Move to stat cards
3. Update status labels and buttons
4. Handle error messages and confirmations

### Phase 3: Default Language Change

After English translations are verified:

1. Change default to browser detection
2. Add language toggle to UI
3. Remove old hardcoded text completely

---

## Risks and Response Plans

### Risk 1: Missing Translation Keys

**Description:** UI shows raw keys instead of translated text

**Mitigation:**
- Implement fallback to other language
- Add warning in development mode
- Create translation coverage report

**Response Plan:**
- Log missing keys to console
- Display key in brackets: `[missing.key]`
- Add missing key to translation files

### Risk 2: Performance Impact

**Description:** Loading translation files adds to page load time

**Mitigation:**
- Cache translations in memory after first load
- Consider bundling translations with main JS
- Use CDN for static assets in production

**Response Plan:**
- Measure load time before/after
- Optimize if increase > 100ms
- Consider async loading for less critical content

### Risk 3: Context-Specific Translations

**Description:** Some translations depend on context (e.g., "active" as status vs. action)

**Mitigation:**
- Use specific keys: `status.online` vs `button.activate`
- Document key naming conventions
- Review translations for context accuracy

**Response Plan:**
- Refactor ambiguous keys
- Add namespace prefixes where needed

---

## Testing Strategy

### Unit Tests

- `I18n.t()` returns correct translation for valid key
- `I18n.t()` returns fallback for missing key
- `I18n.setLanguage()` updates and persists preference
- `I18n.loadLanguage()` handles network errors

### Integration Tests

- API returns valid translations for ko and en
- API rejects invalid language codes
- Frontend successfully loads translations from API
- Language toggle updates all UI elements

### E2E Tests

- User can switch from Korean to English
- User can switch from English to Korean
- Language preference persists across page reload
- Dashboard loads in correct language based on preference

---

## Dependencies and Coordination

### Prerequisites

None - this is independent functionality

### Blocks

- **SPEC-UI-PROJECTS-001**: Project filtering UI should use translatable project names
- **SPEC-UI-MESSAGES-001**: Message history UI should use translatable labels

### Coordination Notes

Implement translation infrastructure first, then coordinate with other SPECs to ensure new UI components use i18n system.

---

## Success Metrics

### Completion Criteria

- All hardcoded Korean text replaced with translation keys
- Language toggle functional in UI
- Language preference persists across sessions
- Zero missing translation keys in common user flows
- Test coverage > 80% for i18n module

### Performance Targets

- Translation load time < 50ms (cached)
- Language switch latency < 100ms
- No measurable impact on dashboard load time

---

**END OF IMPLEMENTATION PLAN - SPEC-UI-I18N-001**
