import abc
import json
import requests
from typing import Iterator
from app.core.config import settings

class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate(self, prompt: str, model_name: str, **kwargs) -> str:
        """Send a non-streaming generation request to the LLM."""
        pass

    @abc.abstractmethod
    def stream(self, prompt: str, model_name: str, **kwargs) -> Iterator[str]:
        """Send a streaming generation request to the LLM."""
        pass

class OllamaProvider(LLMProvider):
    def generate(self, prompt: str, model_name: str, **kwargs) -> str:
        url = f"{settings.LLM_URL}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.2),
                "num_predict": kwargs.get("num_predict", 120),
            }
        }
        response = requests.post(url, json=payload, timeout=(10, 180))
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()

    def stream(self, prompt: str, model_name: str, **kwargs) -> Iterator[str]:
        url = f"{settings.LLM_URL}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.2),
                "num_predict": kwargs.get("num_predict", 120),
            }
        }
        response = requests.post(url, json=payload, timeout=(10, 180), stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            data = json.loads(line)
            token = data.get("response", "")
            done = data.get("done", False)
            if token:
                yield token
            if done:
                break

class OpenRouterProvider(LLMProvider):
    def generate(self, prompt: str, model_name: str, **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/DataTrust",
            "X-Title": "DataTrust",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "temperature": kwargs.get("temperature", 0.2),
        }
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        response = requests.post(url, json=payload, headers=headers, timeout=(10, 120))
        response.raise_for_status()
        
        data = response.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
        return ""

    def stream(self, prompt: str, model_name: str, **kwargs) -> Iterator[str]:
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/DataTrust",
            "X-Title": "DataTrust",
        }
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": True,
            "temperature": kwargs.get("temperature", 0.2),
        }
        
        url = "https://openrouter.ai/api/v1/chat/completions"
        response = requests.post(url, json=payload, headers=headers, timeout=(10, 120), stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            
            if line.startswith("data: "):
                line = line[6:]
            
            line = line.strip()
            if not line or line == "[DONE]":
                continue
                
            try:
                data = json.loads(line)
                choices = data.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
            except Exception:
                pass

def get_llm_provider() -> LLMProvider:
    """Return the active LLM provider based on settings config."""
    if settings.OPENROUTER_API_KEY:
        return OpenRouterProvider()
    return OllamaProvider()
