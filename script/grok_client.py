#!/usr/bin/env python3
"""Grok API client for hypnosis script generation.

Uses OpenAI-compatible API pointing to X.AI endpoints.
"""
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai package not found. Install with: pip install openai", file=sys.stderr)
    sys.exit(1)


class GrokClient:
    """Client for Grok API via OpenAI-compatible interface."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        """Initialize Grok client.

        Args:
            api_key: X.AI API key (defaults to OPENAI_API_KEY env var)
            base_url: API base URL (defaults to OPENAI_BASE_URL env var or https://api.x.ai/v1)
            model: Model name (defaults to OPENAI_MODEL env var or latest available)
        """
        # Load from environment or .env file
        if api_key is None:
            api_key = self._load_env_var('OPENAI_API_KEY')

        if base_url is None:
            base_url = self._load_env_var('OPENAI_BASE_URL', default='https://api.x.ai/v1')

        if model is None:
            model = self._load_env_var('OPENAI_MODEL', default='grok-4-fast-non-reasoning')

        if not api_key:
            raise ValueError("API key not found. Set OPENAI_API_KEY environment variable or pass api_key argument.")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model
        self.base_url = base_url

        print(f"[info] Initialized Grok client", file=sys.stderr)
        print(f"[info]   Base URL: {base_url}", file=sys.stderr)
        print(f"[info]   Model: {model}", file=sys.stderr)

    def _load_env_var(self, var_name: str, default: Optional[str] = None) -> Optional[str]:
        """Load environment variable, checking .env file if needed."""
        # Check environment first
        value = os.environ.get(var_name)
        if value:
            return value

        # Try loading from local .env in repo root
        env_path = Path(__file__).resolve().parent.parent / '.env'
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(var_name + '=') and not line.startswith('#'):
                        return line.split('=', 1)[1]

        return default

    def list_models(self) -> List[str]:
        """List available models."""
        try:
            models = self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            print(f"[warn] Could not list models: {e}", file=sys.stderr)
            return []

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None
    ) -> str:
        """Generate text using Grok API.

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            model: Model name (defaults to instance model)

        Returns:
            Generated text
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"[error] API call failed: {e}", file=sys.stderr)
            raise

    def test_connection(self) -> bool:
        """Test API connection with a simple prompt.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.generate(
                "Say 'Connection successful' and nothing else.",
                temperature=0.0,
                max_tokens=10
            )

            success = 'success' in response.lower()

            if success:
                print(f"[ok] API connection test passed", file=sys.stderr)
                print(f"[ok] Response: {response.strip()}", file=sys.stderr)
            else:
                print(f"[warn] Unexpected response: {response}", file=sys.stderr)

            return success

        except Exception as e:
            print(f"[error] Connection test failed: {e}", file=sys.stderr)
            return False


def main():
    """Test Grok API client."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Grok API client")
    parser.add_argument('--list-models', action='store_true', help='List available models')
    parser.add_argument('--test', action='store_true', help='Test API connection')
    parser.add_argument('--prompt', type=str, help='Test with custom prompt')
    parser.add_argument('--model', type=str, help='Model to use (default: from env or grok-4-fast)')

    args = parser.parse_args()

    try:
        client = GrokClient(model=args.model)

        if args.list_models:
            print("[info] Available models:", file=sys.stderr)
            models = client.list_models()
            if models:
                for model in models:
                    print(f"  - {model}")
            else:
                print("  (Could not retrieve model list)")

        if args.test or not any([args.list_models, args.prompt]):
            client.test_connection()

        if args.prompt:
            print("[info] Generating response...", file=sys.stderr)
            response = client.generate(args.prompt)
            print("\n--- Generated Response ---")
            print(response)
            print("--- End ---\n")

    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
