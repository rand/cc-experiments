# Multi-Provider LM Configuration Example

This example demonstrates how to configure and manage multiple Language Model providers using environment-based configuration in Rust.

## Overview

The example shows how to:
- Support multiple LM providers (OpenAI, Anthropic, Cohere, Ollama)
- Load configuration from environment variables
- Implement provider selection logic
- Test connections to each provider
- Handle provider-specific errors and requirements
- Validate configuration before use

## Supported Providers

### OpenAI
- Requires: API key
- Optional: Model name, base URL, organization ID
- Default model: `gpt-3.5-turbo`

### Anthropic
- Requires: API key
- Optional: Model name, version
- Default model: `claude-3-haiku-20240307`

### Cohere
- Requires: API key
- Optional: Model name
- Default model: `command`

### Ollama
- Requires: Base URL
- Optional: Model name
- Default model: `llama2`
- Default URL: `http://localhost:11434`

## Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
```bash
# Choose your provider
LM_PROVIDER=openai

# OpenAI configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo

# Or use Anthropic
# LM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-3-haiku-20240307

# Or use Cohere
# LM_PROVIDER=cohere
# COHERE_API_KEY=...
# COHERE_MODEL=command

# Or use Ollama (local)
# LM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama2
```

3. Build and run:
```bash
cargo build
cargo run
```

## Usage

The application will:
1. Load configuration from environment variables
2. Validate the selected provider's configuration
3. Test the connection to the provider
4. Display configuration details

### Switching Providers

Simply change the `LM_PROVIDER` environment variable:

```bash
# Use OpenAI
export LM_PROVIDER=openai
cargo run

# Use Anthropic
export LM_PROVIDER=anthropic
cargo run

# Use local Ollama
export LM_PROVIDER=ollama
cargo run
```

## Configuration Structure

The `LMConfig` struct provides a type-safe way to manage provider configurations:

```rust
pub struct LMConfig {
    provider: Provider,
    api_key: Option<String>,
    model: String,
    base_url: Option<String>,
    additional_params: HashMap<String, String>,
}
```

### Provider Enum

```rust
pub enum Provider {
    OpenAI,
    Anthropic,
    Cohere,
    Ollama,
}
```

## Error Handling

The example demonstrates proper error handling for:
- Missing required API keys
- Invalid provider names
- Connection failures
- Provider-specific validation errors

Each error includes descriptive messages to help diagnose configuration issues.

## Example Output

```
Initializing LM Configuration...
Provider: OpenAI
Model: gpt-3.5-turbo
Configuration validated successfully

Testing connection to OpenAI...
Connection test passed!

Configuration details:
  Provider: OpenAI
  Model: gpt-3.5-turbo
  Base URL: https://api.openai.com/v1
  Additional params: organization_id=org-...
```

## Integration with DSPy

This configuration pattern can be integrated with DSPy by:

1. Loading the configuration at startup
2. Passing provider details to DSPy's LM initialization
3. Using the same environment variables across Rust and Python

Example integration:
```rust
let config = LMConfig::from_env()?;
config.validate()?;

// Pass to Python/DSPy via PyO3
Python::with_gil(|py| {
    let dspy = py.import("dspy")?;
    let lm = match config.provider {
        Provider::OpenAI => {
            dspy.call_method1("OpenAI", (config.model, config.api_key))?
        }
        // ... other providers
    };
    Ok(())
})
```

## Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LM_PROVIDER` | Yes | - | Provider name: `openai`, `anthropic`, `cohere`, `ollama` |
| `OPENAI_API_KEY` | If using OpenAI | - | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-3.5-turbo` | OpenAI model name |
| `OPENAI_BASE_URL` | No | `https://api.openai.com/v1` | OpenAI API base URL |
| `OPENAI_ORG_ID` | No | - | OpenAI organization ID |
| `ANTHROPIC_API_KEY` | If using Anthropic | - | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-3-haiku-20240307` | Anthropic model name |
| `ANTHROPIC_VERSION` | No | `2023-06-01` | Anthropic API version |
| `COHERE_API_KEY` | If using Cohere | - | Cohere API key |
| `COHERE_MODEL` | No | `command` | Cohere model name |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | No | `llama2` | Ollama model name |

## Best Practices

1. **Never commit `.env` files**: Always use `.env.example` as a template
2. **Validate early**: Check configuration at startup, not at first use
3. **Provider-specific defaults**: Set sensible defaults for each provider
4. **Clear error messages**: Help users diagnose configuration issues quickly
5. **Type safety**: Use enums and structs to prevent invalid configurations
6. **Environment isolation**: Use different `.env` files for dev/staging/prod

## Testing

To test without real API calls, you can use Ollama locally:

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2

# Run the example
export LM_PROVIDER=ollama
cargo run
```

## Next Steps

- Add configuration file support (TOML/YAML)
- Implement retry logic with exponential backoff
- Add request/response logging
- Support multiple concurrent providers
- Add provider-specific optimization flags
- Implement configuration hot-reloading

## Dependencies

- `pyo3`: Python integration
- `anyhow`: Error handling
- `serde`: Serialization
- `serde_json`: JSON support
- `dotenv`: Environment variable loading

## License

This example is part of the DSPy-PyO3 fundamentals skill resources.
