import re
import unicodedata
from functools import lru_cache

from app.models import TranslateLineRequest, TranslateLineResponse

WORD_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+")


def translate_line(request: TranslateLineRequest) -> TranslateLineResponse:
    translated_text = translate_text(
        request.text,
        request.source_language,
        request.target_language,
    )
    token_translations = translate_tokens(
        request.text,
        request.source_language,
        request.target_language,
    )

    return TranslateLineResponse(
        sourceText=request.text,
        translatedText=translated_text,
        sourceLanguage=request.source_language,
        targetLanguage=request.target_language,
        provider="argos",
        isMock=False,
        tokenTranslations=token_translations,
    )


def translate_tokens(text: str, source_language: str, target_language: str) -> dict[str, str]:
    translations: dict[str, str] = {}

    for token in WORD_PATTERN.findall(text):
        key = normalize_token(token)

        if len(key) < 2 or key in translations:
            continue

        translations[key] = translate_text(token, source_language, target_language)

    return translations


@lru_cache(maxsize=2048)
def translate_text(text: str, source_language: str, target_language: str) -> str:
    # Keep the legacy endpoint import-light. Argos is loaded only when the
    # deprecated endpoint receives an actual translation request.
    from argostranslate import translate

    return translate.translate(text, source_language, target_language)


def normalize_token(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    without_accents = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_accents.replace("’", "'").replace("'", "").strip()
