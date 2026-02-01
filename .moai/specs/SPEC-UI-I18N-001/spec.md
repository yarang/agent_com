# SPEC-UI-I18N-001: Dashboard Multi-Language Support

**SPEC ID:** SPEC-UI-I18N-001
**Title:** Dashboard Multi-Language Support (Korean/English)
**Created:** 2026-02-01
**Status:** Planned
**Priority:** Medium

---

## Environment

### Context

The Communication Server dashboard currently has hardcoded Korean text throughout the UI (`index.html`, `dashboard.js`, `api.js`). The user requests multi-language support with Korean/English toggle functionality.

### Current State

- Dashboard HTML contains hardcoded Korean text (e.g., "전체 에이전트", "활성화 에이전트", "연결 중...")
- JavaScript files have Korean UI strings embedded
- No language selection mechanism exists
- No language API endpoint for translations

### Target State

- Dashboard supports Korean and English languages
- User can toggle between languages via UI selector
- Language preference persists in browser localStorage
- Backend API provides translation resources
- WebSocket updates respect language preference

---

## Assumptions

### Technical Assumptions

- **Confidence: High** - Modern browsers support localStorage API
- **Evidence Basis**: Standard web API with >95% browser support
- **Risk if Wrong**: Fallback to cookies or session storage needed
- **Validation Method**: Test on target browsers (Chrome, Firefox, Safari, Edge)

### User Behavior Assumptions

- **Confidence: Medium** - Users primarily prefer Korean or English
- **Evidence Basis**: Project is Korean-developed with English documentation
- **Risk if Wrong**: May need additional language support later
- **Validation Method**: User feedback after initial implementation

### Integration Assumptions

- **Confidence: High** - Existing announcement_translator can be adapted
- **Evidence Basis**: Similar pattern exists in MoAI-ADK
- **Risk if Wrong**: Custom translation system required
- **Validation Method**: Proof of concept with announcement_translator pattern

---

## Requirements (EARS Format)

### Ubiquitous Requirements

**REQ-I18N-001:** The system **shall** provide language toggle functionality accessible from the dashboard header.

**REQ-I18N-002:** The system **shall** persist user language preference in browser localStorage.

**REQ-I18N-003:** The system **shall** default to Korean language when no preference is set.

**REQ-I18N-004:** The system **shall** support Korean (ko) and English (en) language codes.

### Event-Driven Requirements

**WHEN** user selects a language from the language toggle dropdown, **THEN** the system **shall** update all UI text to the selected language immediately.

**WHEN** user selects a language, **THEN** the system **shall** save the preference to localStorage with key `dashboard_language`.

**WHEN** dashboard initializes, **THEN** the system **shall** load language preference from localStorage or default to Korean.

**WHEN** API responses include translatable content, **THEN** the system **shall** apply translations based on current language.

### State-Driven Requirements

**IF** localStorage contains a valid language preference, **THEN** the system **shall** use that language on dashboard load.

**IF** localStorage language preference is invalid or missing, **THEN** the system **shall** default to Korean (ko).

**IF** translation key is missing for current language, **THEN** the system **shall** fallback to the other language before displaying raw key.

### Unwanted Requirements

The system **shall not** require page refresh when switching languages.

The system **shall not** break existing functionality when adding language support.

### Optional Requirements

**Where possible**, the system **should** support language detection from browser `navigator.language` API for initial default.

**Where possible**, the system **should** provide language file structure that allows easy addition of new languages (ja, zh) in future.

---

## Specifications

### Frontend Specifications

**SPEC-I18N-FE-001:** Language JSON Files

Create translation files in `src/communication_server/static/i18n/`:

```json
// i18n/ko.json
{
  "dashboard": {
    "title": "AI Agent Communication",
    "subtitle": "Real-time Status Board"
  },
  "stats": {
    "totalAgents": "전체 에이전트",
    "activeAgents": "활성화 에이전트",
    "totalMessages": "전체 메시지",
    "totalMeetings": "진행 중 회의",
    "decisionsMade": "결정 사항"
  },
  "connection": {
    "connected": "연결됨",
    "connecting": "연결 중...",
    "disconnected": "연결 해제",
    "error": "연결 오류"
  }
}
```

**SPEC-I18N-FE-002:** Language Toggle Component

Add language selector in header:
- Dropdown with 한국어/English options
- Icon: globe or language icon
- Position: Right side of header, next to time display

**SPEC-I18N-FE-003:** Translation Function

Create `src/communication_server/static/js/i18n.js`:

```javascript
class I18n {
    constructor() {
        this.currentLanguage = this.loadLanguage();
        this.translations = {};
    }

    async loadTranslations() {
        // Load JSON files based on currentLanguage
    }

    t(key) {
        // Get translation for key
    }

    setLanguage(lang) {
        this.currentLanguage = lang;
        localStorage.setItem('dashboard_language', lang);
    }
}
```

### Backend Specifications

**SPEC-I18N-BE-001:** Language API Endpoint

Create `GET /api/v1/i18n/{language}` endpoint:

```python
@router.get("/i18n/{language}")
async def get_translations(language: str) -> dict:
    """
    Get translation strings for specified language.

    Args:
        language: Language code (ko, en)

    Returns:
        Dictionary of translation key-value pairs
    """
```

**SPEC-I18N-BE-002:** Supported Languages List

Create `GET /api/v1/i18n/languages` endpoint:

```python
@router.get("/i18n/languages")
async def get_supported_languages() -> dict:
    """
    Get list of supported languages.

    Returns:
        Dictionary with language codes and native names
    """
    return {
        "languages": [
            {"code": "ko", "name": "한국어", "native_name": "한국어"},
            {"code": "en", "name": "English", "native_name": "English"}
        ],
        "default": "ko"
    }
```

### Data Models

**SPEC-I18N-DM-001:** Translation Resource Model

```python
class TranslationResource(BaseModel):
    """Translation resource for a language."""

    language: str = Field(description="Language code (ko, en)")
    translations: dict[str, str] = Field(description="Translation key-value pairs")
    version: str = Field(default="1.0.0", description="Translation version")
```

---

## Dependencies

### Internal Dependencies

- **SPEC-MCP-BROKER-001**: Base MCP Broker Server functionality
- **SPEC-UI-PROJECTS-001**: Project filtering UI (language support needed for project names)

### External Dependencies

None required for initial implementation

---

## Quality Gates

### TRUST 5 Framework

**Tested:**
- Unit tests for translation loading and key lookup
- Integration tests for language switching
- E2E tests for complete language toggle flow

**Readable:**
- Clear naming: `I18n`, `t()`, `setLanguage()`
- Documentation comments for translation file structure

**Unified:**
- Consistent translation key naming (dot notation)
- Consistent JSON structure across language files

**Secured:**
- Input validation for language codes
- No XSS from user-generated translations (static files only)

**Trackable:**
- Conventional commits for translation changes
- Component: `i18n`, `feat`: for new features

---

## Related Documents

- **PLAN:** `.moai/specs/SPEC-UI-I18N-001/plan.md` - Implementation milestones
- **ACCEPTANCE:** `.moai/specs/SPEC-UI-I18N-001/acceptance.md` - Test scenarios

---

**END OF SPEC-UI-I18N-001**
