from typing import Dict

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str


class TranslateLineRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_language: str = Field(alias="sourceLanguage", min_length=2)
    target_language: str = Field(alias="targetLanguage", min_length=2)
    text: str = Field(min_length=1)


class TranslateLineResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_text: str = Field(alias="sourceText")
    translated_text: str = Field(alias="translatedText")
    source_language: str = Field(alias="sourceLanguage")
    target_language: str = Field(alias="targetLanguage")
    provider: str
    is_mock: bool = Field(alias="isMock")
    token_translations: Dict[str, str] = Field(alias="tokenTranslations")
