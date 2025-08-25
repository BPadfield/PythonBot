import os
import openai
import ollama

class LLM:
    def generate(self, system: str, prompt: str, **kwargs) -> str:
        raise NotImplementedError

class OllamaLLM(LLM):
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct")

    def generate(self, system: str, prompt: str, **kwargs) -> str:
        response = ollama.chat(
            model=kwargs.get("model", self.model),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": kwargs.get("temperature", 0.7)},
        )
        return response["message"]["content"]
    

class OpenAILLM(LLM):
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def generate(self, system: str, prompt: str, **kwargs) -> str:
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=kwargs.get("max_tokens", 256),
            temperature=kwargs.get("temperature", 0.7),
        )
        return response.choices[0].message["content"]

def make_llm() -> LLM:
    backend = os.getenv("LLM_BACKEND", "ollama").lower()
    if backend == "openai":
        return OpenAILLM()
    return OllamaLLM()
