from pydantic import BaseModel, ConfigDict


class PreprocessedEmail(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sender: str
    recipients: list[str]
    subject: str | None
    body: str
    truncated: bool = False
