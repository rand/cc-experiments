use anyhow::{anyhow, Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;

/// Supported Language Model providers
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Provider {
    OpenAI,
    Anthropic,
    Cohere,
    Ollama,
}

impl Provider {
    /// Parse provider from string
    pub fn from_str(s: &str) -> Result<Self> {
        match s.to_lowercase().as_str() {
            "openai" => Ok(Provider::OpenAI),
            "anthropic" => Ok(Provider::Anthropic),
            "cohere" => Ok(Provider::Cohere),
            "ollama" => Ok(Provider::Ollama),
            _ => Err(anyhow!(
                "Invalid provider '{}'. Supported: openai, anthropic, cohere, ollama",
                s
            )),
        }
    }

    /// Get default model for provider
    pub fn default_model(&self) -> &str {
        match self {
            Provider::OpenAI => "gpt-3.5-turbo",
            Provider::Anthropic => "claude-3-haiku-20240307",
            Provider::Cohere => "command",
            Provider::Ollama => "llama2",
        }
    }

    /// Get default base URL for provider
    pub fn default_base_url(&self) -> Option<&str> {
        match self {
            Provider::OpenAI => Some("https://api.openai.com/v1"),
            Provider::Anthropic => Some("https://api.anthropic.com"),
            Provider::Cohere => Some("https://api.cohere.ai"),
            Provider::Ollama => Some("http://localhost:11434"),
        }
    }

    /// Check if provider requires API key
    pub fn requires_api_key(&self) -> bool {
        match self {
            Provider::OpenAI | Provider::Anthropic | Provider::Cohere => true,
            Provider::Ollama => false,
        }
    }
}

/// Language Model configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LMConfig {
    provider: Provider,
    api_key: Option<String>,
    model: String,
    base_url: Option<String>,
    additional_params: HashMap<String, String>,
}

impl LMConfig {
    /// Load configuration from environment variables
    pub fn from_env() -> Result<Self> {
        // Load .env file if present
        dotenv::dotenv().ok();

        let provider_str = env::var("LM_PROVIDER")
            .context("LM_PROVIDER environment variable not set")?;

        let provider = Provider::from_str(&provider_str)?;

        let mut config = LMConfig {
            provider,
            api_key: None,
            model: provider.default_model().to_string(),
            base_url: provider.default_base_url().map(|s| s.to_string()),
            additional_params: HashMap::new(),
        };

        // Load provider-specific configuration
        match provider {
            Provider::OpenAI => config.load_openai_config()?,
            Provider::Anthropic => config.load_anthropic_config()?,
            Provider::Cohere => config.load_cohere_config()?,
            Provider::Ollama => config.load_ollama_config()?,
        }

        Ok(config)
    }

    /// Load OpenAI-specific configuration
    fn load_openai_config(&mut self) -> Result<()> {
        self.api_key = Some(
            env::var("OPENAI_API_KEY")
                .context("OPENAI_API_KEY not set")?,
        );

        if let Ok(model) = env::var("OPENAI_MODEL") {
            self.model = model;
        }

        if let Ok(base_url) = env::var("OPENAI_BASE_URL") {
            self.base_url = Some(base_url);
        }

        if let Ok(org_id) = env::var("OPENAI_ORG_ID") {
            self.additional_params.insert("organization_id".to_string(), org_id);
        }

        Ok(())
    }

    /// Load Anthropic-specific configuration
    fn load_anthropic_config(&mut self) -> Result<()> {
        self.api_key = Some(
            env::var("ANTHROPIC_API_KEY")
                .context("ANTHROPIC_API_KEY not set")?,
        );

        if let Ok(model) = env::var("ANTHROPIC_MODEL") {
            self.model = model;
        }

        if let Ok(version) = env::var("ANTHROPIC_VERSION") {
            self.additional_params.insert("api_version".to_string(), version);
        } else {
            self.additional_params.insert("api_version".to_string(), "2023-06-01".to_string());
        }

        Ok(())
    }

    /// Load Cohere-specific configuration
    fn load_cohere_config(&mut self) -> Result<()> {
        self.api_key = Some(
            env::var("COHERE_API_KEY")
                .context("COHERE_API_KEY not set")?,
        );

        if let Ok(model) = env::var("COHERE_MODEL") {
            self.model = model;
        }

        Ok(())
    }

    /// Load Ollama-specific configuration
    fn load_ollama_config(&mut self) -> Result<()> {
        if let Ok(base_url) = env::var("OLLAMA_BASE_URL") {
            self.base_url = Some(base_url);
        }

        if let Ok(model) = env::var("OLLAMA_MODEL") {
            self.model = model;
        }

        Ok(())
    }

    /// Validate configuration
    pub fn validate(&self) -> Result<()> {
        // Check API key requirement
        if self.provider.requires_api_key() && self.api_key.is_none() {
            return Err(anyhow!(
                "{:?} provider requires an API key",
                self.provider
            ));
        }

        // Validate API key format if present
        if let Some(ref key) = self.api_key {
            if key.is_empty() {
                return Err(anyhow!("API key cannot be empty"));
            }

            // Provider-specific validation
            match self.provider {
                Provider::OpenAI => {
                    if !key.starts_with("sk-") {
                        return Err(anyhow!("OpenAI API key should start with 'sk-'"));
                    }
                }
                Provider::Anthropic => {
                    if !key.starts_with("sk-ant-") {
                        return Err(anyhow!("Anthropic API key should start with 'sk-ant-'"));
                    }
                }
                _ => {}
            }
        }

        // Validate model name
        if self.model.is_empty() {
            return Err(anyhow!("Model name cannot be empty"));
        }

        // Validate base URL if present
        if let Some(ref url) = self.base_url {
            if url.is_empty() {
                return Err(anyhow!("Base URL cannot be empty"));
            }
            if !url.starts_with("http://") && !url.starts_with("https://") {
                return Err(anyhow!("Base URL must start with http:// or https://"));
            }
        }

        Ok(())
    }

    /// Test connection to provider (simulated)
    pub fn test_connection(&self) -> Result<()> {
        println!("Testing connection to {:?}...", self.provider);

        match self.provider {
            Provider::OpenAI => {
                println!("  Verifying OpenAI API key format...");
                if let Some(ref key) = self.api_key {
                    if key.len() < 20 {
                        return Err(anyhow!("OpenAI API key seems too short"));
                    }
                }
                println!("  API key format valid");
            }
            Provider::Anthropic => {
                println!("  Verifying Anthropic API key format...");
                if let Some(ref key) = self.api_key {
                    if key.len() < 20 {
                        return Err(anyhow!("Anthropic API key seems too short"));
                    }
                }
                println!("  API key format valid");
            }
            Provider::Cohere => {
                println!("  Verifying Cohere API key format...");
                if let Some(ref key) = self.api_key {
                    if key.len() < 20 {
                        return Err(anyhow!("Cohere API key seems too short"));
                    }
                }
                println!("  API key format valid");
            }
            Provider::Ollama => {
                println!("  Checking Ollama base URL...");
                if let Some(ref url) = self.base_url {
                    println!("  Base URL: {}", url);
                }
                println!("  Note: Ensure Ollama server is running locally");
            }
        }

        println!("Connection test passed!");
        Ok(())
    }

    /// Display configuration details
    pub fn display(&self) {
        println!("\nConfiguration details:");
        println!("  Provider: {:?}", self.provider);
        println!("  Model: {}", self.model);

        if let Some(ref url) = self.base_url {
            println!("  Base URL: {}", url);
        }

        if let Some(ref key) = self.api_key {
            let masked = format!("{}...{}", &key[..8], &key[key.len()-4..]);
            println!("  API Key: {}", masked);
        }

        if !self.additional_params.is_empty() {
            println!("  Additional params:");
            for (key, value) in &self.additional_params {
                println!("    {}: {}", key, value);
            }
        }
    }

    /// Get provider
    pub fn provider(&self) -> Provider {
        self.provider
    }

    /// Get model name
    pub fn model(&self) -> &str {
        &self.model
    }

    /// Get API key
    pub fn api_key(&self) -> Option<&str> {
        self.api_key.as_deref()
    }

    /// Get base URL
    pub fn base_url(&self) -> Option<&str> {
        self.base_url.as_deref()
    }
}

fn main() -> Result<()> {
    println!("Initializing LM Configuration...\n");

    // Load configuration from environment
    let config = LMConfig::from_env()
        .context("Failed to load configuration from environment")?;

    println!("Provider: {:?}", config.provider());
    println!("Model: {}", config.model());

    // Validate configuration
    config.validate()
        .context("Configuration validation failed")?;

    println!("Configuration validated successfully\n");

    // Test connection
    config.test_connection()
        .context("Connection test failed")?;

    // Display full configuration
    config.display();

    println!("\nConfiguration ready for use!");

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_provider_parsing() {
        assert_eq!(Provider::from_str("openai").unwrap(), Provider::OpenAI);
        assert_eq!(Provider::from_str("OpenAI").unwrap(), Provider::OpenAI);
        assert_eq!(Provider::from_str("anthropic").unwrap(), Provider::Anthropic);
        assert_eq!(Provider::from_str("cohere").unwrap(), Provider::Cohere);
        assert_eq!(Provider::from_str("ollama").unwrap(), Provider::Ollama);
        assert!(Provider::from_str("invalid").is_err());
    }

    #[test]
    fn test_default_models() {
        assert_eq!(Provider::OpenAI.default_model(), "gpt-3.5-turbo");
        assert_eq!(Provider::Anthropic.default_model(), "claude-3-haiku-20240307");
        assert_eq!(Provider::Cohere.default_model(), "command");
        assert_eq!(Provider::Ollama.default_model(), "llama2");
    }

    #[test]
    fn test_api_key_requirements() {
        assert!(Provider::OpenAI.requires_api_key());
        assert!(Provider::Anthropic.requires_api_key());
        assert!(Provider::Cohere.requires_api_key());
        assert!(!Provider::Ollama.requires_api_key());
    }
}
