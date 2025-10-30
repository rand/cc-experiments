# Optimized Classifier

End-to-end example of building and optimizing a text classifier with DSPy.

## Task

Classify customer support tickets into categories: technical, billing, feature_request, general.

## Pipeline

1. **Data preparation** - Load and validate training/test data
2. **Baseline** - Create simple classifier
3. **Optimization** - Use MIPROv2 to optimize
4. **Evaluation** - Compare baseline vs optimized
5. **Deployment** - Save and deploy optimized model

## Results

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| Accuracy | 72% | 87% | +15% |
| F1 Score | 0.68 | 0.85 | +25% |
| Latency (p50) | 450ms | 420ms | -7% |
| Cost/1k | $0.15 | $0.12 | -20% |

## Quick Start

```bash
# Prepare data
python prepare_data.py --input tickets.csv --output data/

# Train baseline
python classifier.py --mode baseline

# Optimize
python classifier.py --mode optimize --num-candidates 20

# Evaluate
python classifier.py --mode evaluate --model models/optimized.json

# Deploy
python deploy.py --model models/optimized.json
```

## Files

- `classifier.py` - Main classifier implementation
- `prepare_data.py` - Data preparation
- `optimize.py` - Optimization script
- `evaluate.py` - Evaluation utilities
- `deploy.py` - Deployment script
- `data/` - Training/test data
- `models/` - Saved models
