from pydantic import BaseModel, Field


class OllamaSettings(BaseModel):
    api_base: str = Field(
        "http://localhost:11434",
        description="Base URL of Ollama API. Example: 'https://localhost:11434'.",
    )
    llm_model: str = Field(
        None,
        description="Model to use. Example: 'llama2-uncensored'.",
    )
    embedding_model: str = Field(
        None,
        description="Model to use. Example: 'nomic-embed-text'.",
    )
    tfs_z: float = Field(
        1.0,
        description="Tail free sampling is used to reduce the impact of less probable tokens from the output. A higher value (e.g., 2.0) will reduce the impact more, while a value of 1.0 disables this setting.",
    )
    num_predict: int = Field(
        None,
        description="Maximum number of tokens to predict when generating text. (Default: 128, -1 = infinite generation, -2 = fill context)",
    )
    top_k: int = Field(
        40,
        description="Reduces the probability of generating nonsense. A higher value (e.g. 100) will give more diverse answers, while a lower value (e.g. 10) will be more conservative. (Default: 40)",
    )
    top_p: float = Field(
        0.9,
        description="Works together with top-k. A higher value (e.g., 0.95) will lead to more diverse text, while a lower value (e.g., 0.5) will generate more focused and conservative text. (Default: 0.9)",
    )
    repeat_last_n: int = Field(
        64,
        description="Sets how far back for the model to look back to prevent repetition. (Default: 64, 0 = disabled, -1 = num_ctx)",
    )
    repeat_penalty: float = Field(
        1.1,
        description="Sets how strongly to penalize repetitions. A higher value (e.g., 1.5) will penalize repetitions more strongly, while a lower value (e.g., 0.9) will be more lenient. (Default: 1.1)",
    )
    request_timeout: float = Field(
        120.0,
        description="Time elapsed until ollama times out the request. Default is 120s. Format is float. ",
    )