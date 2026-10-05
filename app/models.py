from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ToolRequest(StrictModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_.]+$")
    arguments: dict[str, object] = Field(default_factory=dict)


class EmptyArgs(StrictModel):
    pass


class PathArgs(StrictModel):
    path: str = Field(min_length=1, max_length=512)


class FileReadArgs(PathArgs):
    max_bytes: int = Field(default=8192, ge=1, le=32768)


class FileWriteArgs(PathArgs):
    content: str = Field(max_length=32768)


class FileCopyArgs(StrictModel):
    source: str = Field(min_length=1, max_length=512)
    destination: str = Field(min_length=1, max_length=512)


class SecretSetArgs(StrictModel):
    name: Literal["GEMINI_API_KEY", "OPENROUTER_API_KEY", "GROQ_API_KEY", "OMNIROUTE_API_KEY"]
    value: str = Field(min_length=8, max_length=4096)


class ProviderConfigArgs(StrictModel):
    provider: Literal["openrouter", "gemini", "groq", "local"]
    model: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:/-]+$")
    host: str = Field(default="127.0.0.1", pattern=r"^(127\.0\.0\.1|localhost|::1)$")
    port: int = Field(default=20128, ge=1, le=65535)


class ExtensionInstallArgs(StrictModel):
    extension_id: Literal["Google.geminicodeassist", "diegosouzapw.omnicopilot"]


class GitCloneArgs(StrictModel):
    repository: Literal["https://github.com/diegosouzapw/OmniRoute.git"]
    path: str = Field(default="source", max_length=128)


class Result(StrictModel):
    success: bool
    result: dict[str, object] = Field(default_factory=dict)
