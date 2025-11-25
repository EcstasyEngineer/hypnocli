#!/usr/bin/env python3
"""Provider-agnostic LLM client using OpenAI-compatible API.

Supports any provider with OpenAI-compatible endpoints (OpenAI, xAI/Grok,
OpenRouter, local models via Ollama/LM Studio, etc.)

Configuration via environment variables:
    LLM_API_KEY     - API key (required)
    LLM_BASE_URL    - API endpoint (default: https://api.openai.com/v1)
    LLM_MODEL       - Model name (default: gpt-4o)

Or use provider shortcuts for LLM_BASE_URL:
    openai   -> https://api.openai.com/v1
    xai      -> https://api.x.ai/v1
    openrouter -> https://openrouter.ai/api/v1
    ollama   -> http://localhost:11434/v1
"""
import os
import sys
from pathlib import Path
from typing import Optional, List

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not found. Install with: pip install openai", file=sys.stderr)
    sys.exit(1)


# Provider shortcuts - expand to full URLs
PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1",
    "xai": "https://api.x.ai/v1",
    "grok": "https://api.x.ai/v1",  # alias
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}

# Default model per provider (optional convenience)
PROVIDER_DEFAULTS = {
    "https://api.openai.com/v1": "gpt-4o",
    "https://api.x.ai/v1": "grok-4-0414",
    "https://openrouter.ai/api/v1": "anthropic/claude-sonnet-4",
    "http://localhost:11434/v1": "llama3",
    "http://localhost:1234/v1": "local-model",
}


def _load_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Load environment variable, checking .env file if not in environment."""
    value = os.environ.get(var_name)
    if value:
        return value

    # Try .env in repo root
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(var_name + '=') and not line.startswith('#'):
                    return line.split('=', 1)[1].strip('"\'')

    return default


def _resolve_base_url(url_or_shortcut: str) -> str:
    """Resolve provider shortcut to full URL, or return as-is if already a URL."""
    lower = url_or_shortcut.lower().strip()
    if lower in PROVIDER_URLS:
        return PROVIDER_URLS[lower]
    return url_or_shortcut


def get_client() -> tuple[OpenAI, str]:
    """Get configured OpenAI client and model name.

    Returns:
        Tuple of (OpenAI client, model name)

    Raises:
        ValueError: If API key not configured
    """
    api_key = _load_env('LLM_API_KEY') or _load_env('OPENAI_API_KEY')
    base_url_raw = _load_env('LLM_BASE_URL') or _load_env('OPENAI_BASE_URL') or 'openai'
    base_url = _resolve_base_url(base_url_raw)

    # Model: explicit env > provider default > generic fallback
    model = _load_env('LLM_MODEL') or _load_env('OPENAI_MODEL')
    if not model:
        model = PROVIDER_DEFAULTS.get(base_url, 'gpt-4o')

    if not api_key:
        raise ValueError(
            "API key not found. Set LLM_API_KEY or OPENAI_API_KEY environment variable.\n"
            "Example .env file:\n"
            "  LLM_API_KEY=your-key-here\n"
            "  LLM_BASE_URL=xai\n"
            "  LLM_MODEL=grok-4-0414"
        )

    client = OpenAI(api_key=api_key, base_url=base_url)

    print(f"[info] LLM client initialized", file=sys.stderr)
    print(f"[info]   Provider: {base_url}", file=sys.stderr)
    print(f"[info]   Model: {model}", file=sys.stderr)

    return client, model


def generate(
    prompt: str,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    client: Optional[OpenAI] = None,
    model: Optional[str] = None
) -> str:
    """Generate text using configured LLM.

    Args:
        prompt: User prompt
        system_prompt: System prompt (optional)
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate
        client: OpenAI client (uses get_client() if not provided)
        model: Model override (uses configured model if not provided)

    Returns:
        Generated text
    """
    if client is None:
        client, default_model = get_client()
        if model is None:
            model = default_model
    elif model is None:
        _, model = get_client()  # Just get the model name

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"[error] API call failed: {e}", file=sys.stderr)
        raise


def list_models(client: Optional[OpenAI] = None) -> List[str]:
    """List available models from the provider."""
    if client is None:
        client, _ = get_client()
    try:
        models = client.models.list()
        return [m.id for m in models.data]
    except Exception as e:
        print(f"[warn] Could not list models: {e}", file=sys.stderr)
        return []


def test_connection() -> bool:
    """Test API connection with a simple prompt."""
    try:
        response = generate(
            "Say 'Connection successful' and nothing else.",
            temperature=0.0,
            max_tokens=10
        )
        success = 'success' in response.lower()
        if success:
            print(f"[ok] Connection test passed", file=sys.stderr)
        else:
            print(f"[warn] Unexpected response: {response}", file=sys.stderr)
        return success
    except Exception as e:
        print(f"[error] Connection test failed: {e}", file=sys.stderr)
        return False


# Backwards compatibility shim - remove after updating all imports
class GrokClient:
    """DEPRECATED: Use llm_client.generate() directly instead."""

    def __init__(self, api_key=None, base_url=None, model=None):
        print("[warn] GrokClient is deprecated. Use llm_client.generate() instead.", file=sys.stderr)
        self._client, self._model = get_client()
        if model:
            self._model = model

    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=2000, model=None):
        return generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            client=self._client,
            model=model or self._model
        )

    def list_models(self):
        return list_models(self._client)

    def test_connection(self):
        return test_connection()


def main():
    """CLI for testing LLM client."""
    import argparse

    parser = argparse.ArgumentParser(description="Test LLM client connection")
    parser.add_argument('--list-models', action='store_true', help='List available models')
    parser.add_argument('--test', action='store_true', help='Test API connection')
    parser.add_argument('--prompt', type=str, help='Test with custom prompt')
    parser.add_argument('--model', type=str, help='Model override')

    args = parser.parse_args()

    try:
        client, model = get_client()
        if args.model:
            model = args.model

        if args.list_models:
            print("[info] Available models:", file=sys.stderr)
            models = list_models(client)
            for m in models:
                print(f"  - {m}")

        if args.test or not any([args.list_models, args.prompt]):
            test_connection()

        if args.prompt:
            print("[info] Generating response...", file=sys.stderr)
            response = generate(args.prompt, client=client, model=model)
            print("\n--- Response ---")
            print(response)
            print("--- End ---\n")

    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
