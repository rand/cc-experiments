#!/usr/bin/env python3
"""
Language Model Configuration Manager

Manage LM configurations for DSPy from Rust. Generate, validate, test, and switch
between different language model providers and configurations.

Usage:
    python lm_config_manager.py generate > config.json    # Generate from env
    python lm_config_manager.py validate config.json      # Validate config
    python lm_config_manager.py test config.json          # Test LM connection
    python lm_config_manager.py list                      # List supported providers
"""

import os
import sys
import json
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class Provider(str, Enum):
    """Supported LM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    TOGETHER = "together"
    OLLAMA = "ollama"


@dataclass
class LMConfig:
    """Language model configuration."""
    provider: str
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    api_key_env: Optional[str] = None  # Environment variable name
    base_url: Optional[str] = None  # For Ollama or custom endpoints

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, omitting None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LMConfig':
        """Create from dictionary."""
        return cls(**data)

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate configuration.

        Returns:
            (is_valid, error_message)
        """
        # Check provider
        if self.provider not in [p.value for p in Provider]:
            return False, f"Invalid provider: {self.provider}"

        # Check model
        if not self.model:
            return False, "Model name is required"

        # Check temperature
        if self.temperature is not None:
            if not (0 <= self.temperature <= 2):
                return False, f"Temperature must be 0-2, got {self.temperature}"

        # Check max_tokens
        if self.max_tokens is not None:
            if self.max_tokens < 1:
                return False, f"max_tokens must be positive, got {self.max_tokens}"

        # Provider-specific validation
        if self.provider == Provider.OLLAMA:
            if not self.base_url:
                return False, "Ollama requires base_url"

        return True, None

    def get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        if not self.api_key_env:
            # Use default env var for provider
            env_var = f"{self.provider.upper()}_API_KEY"
        else:
            env_var = self.api_key_env

        return os.environ.get(env_var)


class ConfigManager:
    """Manage LM configurations."""

    # Default models for each provider
    DEFAULT_MODELS = {
        Provider.OPENAI: "gpt-3.5-turbo",
        Provider.ANTHROPIC: "claude-3-sonnet-20240229",
        Provider.COHERE: "command-r-plus",
        Provider.TOGETHER: "mistralai/Mixtral-8x7B-Instruct-v0.1",
        Provider.OLLAMA: "llama2",
    }

    @classmethod
    def generate_from_env(cls) -> LMConfig:
        """Generate configuration from environment variables.

        Environment variables:
            LM_PROVIDER: Provider name (default: openai)
            LM_MODEL: Model name (default: provider-specific)
            LM_TEMPERATURE: Temperature (optional)
            LM_MAX_TOKENS: Max tokens (optional)
            LM_BASE_URL: Base URL for Ollama (optional)
        """
        provider = os.environ.get("LM_PROVIDER", Provider.OPENAI.value).lower()

        # Get model, use default if not specified
        model = os.environ.get(
            "LM_MODEL",
            cls.DEFAULT_MODELS.get(Provider(provider), "gpt-3.5-turbo")
        )

        config = LMConfig(
            provider=provider,
            model=model,
            temperature=float(os.environ["LM_TEMPERATURE"])
                if "LM_TEMPERATURE" in os.environ else None,
            max_tokens=int(os.environ["LM_MAX_TOKENS"])
                if "LM_MAX_TOKENS" in os.environ else None,
            base_url=os.environ.get("LM_BASE_URL"),
        )

        return config

    @classmethod
    def load_from_file(cls, path: str) -> LMConfig:
        """Load configuration from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return LMConfig.from_dict(data)

    @classmethod
    def save_to_file(cls, config: LMConfig, path: str):
        """Save configuration to JSON file."""
        with open(path, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)

    @classmethod
    def test_connection(cls, config: LMConfig) -> tuple[bool, Optional[str]]:
        """Test connection to language model.

        Returns:
            (success, error_message)
        """
        try:
            import dspy

            # Configure DSPy with this config
            if config.provider == Provider.OPENAI.value:
                lm = dspy.OpenAI(model=config.model)
            elif config.provider == Provider.ANTHROPIC.value:
                lm = dspy.Anthropic(model=config.model)
            elif config.provider == Provider.COHERE.value:
                lm = dspy.Cohere(model=config.model)
            elif config.provider == Provider.TOGETHER.value:
                lm = dspy.Together(model=config.model)
            elif config.provider == Provider.OLLAMA.value:
                lm = dspy.OllamaLocal(
                    model=config.model,
                    base_url=config.base_url or "http://localhost:11434"
                )
            else:
                return False, f"Unsupported provider: {config.provider}"

            # Configure
            dspy.settings.configure(lm=lm)

            # Test with simple prediction
            predict = dspy.Predict("question -> answer")
            result = predict(question="Test: respond with 'OK'")

            if result.answer:
                return True, None
            else:
                return False, "Empty response from LM"

        except Exception as e:
            return False, str(e)

    @classmethod
    def list_providers(cls) -> Dict[str, Dict[str, Any]]:
        """List all supported providers with details."""
        return {
            Provider.OPENAI.value: {
                "description": "OpenAI GPT models",
                "default_model": cls.DEFAULT_MODELS[Provider.OPENAI],
                "env_var": "OPENAI_API_KEY",
                "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            },
            Provider.ANTHROPIC.value: {
                "description": "Anthropic Claude models",
                "default_model": cls.DEFAULT_MODELS[Provider.ANTHROPIC],
                "env_var": "ANTHROPIC_API_KEY",
                "models": [
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307",
                ],
            },
            Provider.COHERE.value: {
                "description": "Cohere models",
                "default_model": cls.DEFAULT_MODELS[Provider.COHERE],
                "env_var": "COHERE_API_KEY",
                "models": ["command-r-plus", "command-r", "command"],
            },
            Provider.TOGETHER.value: {
                "description": "Together AI models",
                "default_model": cls.DEFAULT_MODELS[Provider.TOGETHER],
                "env_var": "TOGETHER_API_KEY",
                "models": [
                    "mistralai/Mixtral-8x7B-Instruct-v0.1",
                    "meta-llama/Llama-3-70b-chat-hf",
                ],
            },
            Provider.OLLAMA.value: {
                "description": "Ollama local models",
                "default_model": cls.DEFAULT_MODELS[Provider.OLLAMA],
                "env_var": None,
                "models": ["llama2", "mistral", "codellama"],
                "requires": "base_url (e.g., http://localhost:11434)",
            },
        }


def cmd_generate(args):
    """Generate config from environment."""
    config = ConfigManager.generate_from_env()

    # Validate
    is_valid, error = config.validate()
    if not is_valid:
        print(f"Warning: {error}", file=sys.stderr)

    # Output JSON
    print(json.dumps(config.to_dict(), indent=2))


def cmd_validate(args):
    """Validate config file."""
    try:
        config = ConfigManager.load_from_file(args.config)

        is_valid, error = config.validate()

        if is_valid:
            print(f"✓ Configuration is valid")
            print(f"  Provider: {config.provider}")
            print(f"  Model: {config.model}")

            # Check API key
            api_key = config.get_api_key()
            if api_key:
                print(f"  API Key: Found in environment")
            else:
                print(f"  ⚠ API Key: Not found in environment")

            sys.exit(0)
        else:
            print(f"✗ Configuration is invalid: {error}")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def cmd_test(args):
    """Test LM connection."""
    try:
        config = ConfigManager.load_from_file(args.config)

        print(f"Testing connection to {config.provider} ({config.model})...")

        success, error = ConfigManager.test_connection(config)

        if success:
            print(f"✓ Connection successful!")
            sys.exit(0)
        else:
            print(f"✗ Connection failed: {error}")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


def cmd_list(args):
    """List supported providers."""
    providers = ConfigManager.list_providers()

    print("\nSupported Language Model Providers:\n")
    print("=" * 60)

    for name, info in providers.items():
        print(f"\n{name.upper()}")
        print(f"  Description: {info['description']}")
        print(f"  Default Model: {info['default_model']}")

        if info.get('env_var'):
            print(f"  API Key: {info['env_var']}")

        if info.get('requires'):
            print(f"  Requires: {info['requires']}")

        print(f"  Example Models: {', '.join(info['models'][:3])}")

    print("\n" + "=" * 60 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage LM configurations for DSPy"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Generate command
    parser_gen = subparsers.add_parser('generate', help='Generate config from environment')

    # Validate command
    parser_val = subparsers.add_parser('validate', help='Validate config file')
    parser_val.add_argument('config', help='Path to config file')

    # Test command
    parser_test = subparsers.add_parser('test', help='Test LM connection')
    parser_test.add_argument('config', help='Path to config file')

    # List command
    parser_list = subparsers.add_parser('list', help='List supported providers')

    args = parser.parse_args()

    if args.command == 'generate':
        cmd_generate(args)
    elif args.command == 'validate':
        cmd_validate(args)
    elif args.command == 'test':
        cmd_test(args)
    elif args.command == 'list':
        cmd_list(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
