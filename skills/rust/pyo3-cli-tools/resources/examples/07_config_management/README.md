# Example 07: Configuration Management

Fast TOML/YAML configuration file handling with PyO3 and serde.

## Features
- Load/save TOML configs
- Load/save YAML configs
- Merge multiple config files
- Type-safe configuration

## Usage
```python
import config_management

# Load config
config = config_management.load_toml("config.toml")
# Modify and save
config_management.save_toml("config.toml", config)
```

## Next Steps
- Example 08: Interactive prompts
