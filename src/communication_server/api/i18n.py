"""
I18n (Internationalization) API endpoints.

Provides translation resources for supported languages.
"""

from enum import Enum
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


# Supported languages
class LanguageCode(str, Enum):
    """Supported language codes."""

    KO = "ko"
    EN = "en"


# Translation file directory
I18N_DIR = Path(__file__).parent.parent / "i18n"


class TranslationResource(BaseModel):
    """Translation resource for a language."""

    language: str = Field(description="Language code (ko, en)")
    translations: dict = Field(
        description="Translation key-value pairs (nested structure supported)"
    )
    version: str = Field(default="1.0.0", description="Translation version")


class LanguageInfo(BaseModel):
    """Information about a supported language."""

    code: str = Field(description="Language code (e.g., ko, en)")
    name: str = Field(description="English name of the language")
    native_name: str = Field(description="Native name of the language")


router = APIRouter(prefix="/i18n", tags=["i18n"])

# Language definitions
SUPPORTED_LANGUAGES = [
    LanguageInfo(code="ko", name="Korean", native_name="한국어"),
    LanguageInfo(code="en", name="English", native_name="English"),
]

DEFAULT_LANGUAGE = "ko"


def load_translation_file(language: str) -> dict[str, str]:
    """
    Load translation file for a language.

    Args:
        language: Language code (ko, en)

    Returns:
        Dictionary of translation key-value pairs

    Raises:
        HTTPException: If translation file not found
    """
    translation_file = I18N_DIR / f"{language}.json"

    if not translation_file.exists():
        raise HTTPException(
            status_code=404, detail=f"Translation file not found for language: {language}"
        )

    import json

    with open(translation_file, encoding="utf-8") as f:
        return json.load(f)


@router.get("/languages")
async def get_supported_languages():
    """
    Get list of supported languages.

    Returns:
        Dictionary with languages array and default language
    """
    return {
        "languages": [lang.model_dump() for lang in SUPPORTED_LANGUAGES],
        "default": DEFAULT_LANGUAGE,
    }


@router.get("/{language}", response_model=TranslationResource)
async def get_translations(language: str) -> TranslationResource:
    """
    Get translation strings for specified language.

    Args:
        language: Language code (ko, en)

    Returns:
        TranslationResource with translations dictionary

    Raises:
        HTTPException: If language is not supported or file not found
    """
    # Validate language code
    valid_codes = {lang.code for lang in SUPPORTED_LANGUAGES}
    if language not in valid_codes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language code: {language}. Supported: {valid_codes}",
        )

    translations = load_translation_file(language)

    return TranslationResource(language=language, translations=translations, version="1.0.0")
