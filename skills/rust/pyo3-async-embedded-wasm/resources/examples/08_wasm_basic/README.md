# Example 08: WASM Basic

Basic WASM compilation with dual-target support (browser WASM + Python extension).

## Building

### For WASM (browser)
```bash
wasm-pack build --target web
```

### For Python extension
```bash
maturin develop
```

## Key Concepts
- Conditional compilation for WASM vs native
- wasm-bindgen integration
- Data processing in WASM
- Size optimization
