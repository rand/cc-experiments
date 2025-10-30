//! Model comparison CLI application.
//!
//! Systematically compares multiple DSPy models with statistical analysis.

use anyhow::{Context, Result};
use model_comparison::{ComparisonConfig, Criterion, ModelComparator};
use std::path::PathBuf;

/// CLI arguments structure.
#[derive(Debug)]
struct Args {
    /// Paths to model configurations
    model_paths: Vec<PathBuf>,

    /// Paths to test sets
    test_sets: Vec<PathBuf>,

    /// Criteria specification (name:weight:direction)
    criteria: Vec<Criterion>,

    /// Require statistical significance
    require_significance: bool,

    /// Minimum effect size
    min_effect_size: f64,

    /// Number of runs per model
    num_runs: usize,

    /// Output format (table, json, html)
    output_format: OutputFormat,

    /// Output path
    output_path: Option<PathBuf>,

    /// Verbose output
    verbose: bool,
}

#[derive(Debug, Clone, Copy)]
enum OutputFormat {
    Table,
    Json,
    Html,
}

impl Default for Args {
    fn default() -> Self {
        Self {
            model_paths: vec![],
            test_sets: vec![],
            criteria: vec![
                Criterion::new("accuracy", 0.4, true),
                Criterion::new("latency_p95", 0.3, false),
                Criterion::new("token_usage", 0.2, false),
                Criterion::new("error_rate", 0.1, false),
            ],
            require_significance: true,
            min_effect_size: 0.3,
            num_runs: 3,
            output_format: OutputFormat::Table,
            output_path: None,
            verbose: false,
        }
    }
}

impl Args {
    /// Parse command line arguments.
    fn parse() -> Result<Self> {
        let mut args = Args::default();
        let env_args: Vec<String> = std::env::args().collect();

        let mut i = 1;
        while i < env_args.len() {
            match env_args[i].as_str() {
                "--models" => {
                    i += 1;
                    while i < env_args.len() && !env_args[i].starts_with("--") {
                        args.model_paths.push(PathBuf::from(&env_args[i]));
                        i += 1;
                    }
                    continue;
                }
                "--test-sets" => {
                    i += 1;
                    while i < env_args.len() && !env_args[i].starts_with("--") {
                        args.test_sets.push(PathBuf::from(&env_args[i]));
                        i += 1;
                    }
                    continue;
                }
                "--criteria" => {
                    i += 1;
                    if i < env_args.len() {
                        args.criteria = parse_criteria(&env_args[i])?;
                    }
                }
                "--require-significance" => {
                    args.require_significance = true;
                }
                "--no-require-significance" => {
                    args.require_significance = false;
                }
                "--min-effect-size" => {
                    i += 1;
                    if i < env_args.len() {
                        args.min_effect_size = env_args[i].parse()?;
                    }
                }
                "--num-runs" => {
                    i += 1;
                    if i < env_args.len() {
                        args.num_runs = env_args[i].parse()?;
                    }
                }
                "--format" => {
                    i += 1;
                    if i < env_args.len() {
                        args.output_format = match env_args[i].as_str() {
                            "table" => OutputFormat::Table,
                            "json" => OutputFormat::Json,
                            "html" => OutputFormat::Html,
                            _ => anyhow::bail!("Invalid format: {}", env_args[i]),
                        };
                    }
                }
                "--output" => {
                    i += 1;
                    if i < env_args.len() {
                        args.output_path = Some(PathBuf::from(&env_args[i]));
                    }
                }
                "--verbose" | "-v" => {
                    args.verbose = true;
                }
                "--help" | "-h" => {
                    print_usage();
                    std::process::exit(0);
                }
                _ => {
                    eprintln!("Unknown argument: {}", env_args[i]);
                    print_usage();
                    std::process::exit(1);
                }
            }
            i += 1;
        }

        // Validate arguments
        if args.model_paths.len() < 2 {
            anyhow::bail!("At least 2 models required");
        }

        if args.test_sets.is_empty() {
            anyhow::bail!("At least 1 test set required");
        }

        Ok(args)
    }
}

/// Parse criteria from command line format.
///
/// Format: "name:weight:direction,name:weight:direction,..."
/// Example: "accuracy:0.4:higher,latency_p95:0.3:lower"
fn parse_criteria(spec: &str) -> Result<Vec<Criterion>> {
    let mut criteria = Vec::new();

    for part in spec.split(',') {
        let components: Vec<&str> = part.split(':').collect();

        if components.len() != 3 {
            anyhow::bail!(
                "Invalid criterion format: '{}'. Expected 'name:weight:direction'",
                part
            );
        }

        let name = components[0].to_string();
        let weight: f64 = components[1].parse().context("Invalid weight")?;

        let higher_is_better = match components[2] {
            "higher" | "true" | "1" => true,
            "lower" | "false" | "0" => false,
            _ => anyhow::bail!("Invalid direction: '{}'. Use 'higher' or 'lower'", components[2]),
        };

        criteria.push(Criterion::new(name, weight, higher_is_better));
    }

    // Validate weights sum to approximately 1.0
    let total_weight: f64 = criteria.iter().map(|c| c.weight).sum();
    if (total_weight - 1.0).abs() > 0.01 {
        eprintln!(
            "Warning: Criterion weights sum to {:.2}, not 1.0. Weights will be normalized.",
            total_weight
        );
    }

    Ok(criteria)
}

/// Print usage information.
fn print_usage() {
    println!(
        r#"Model Comparison Tool

USAGE:
    model-comparison --models <MODEL>... --test-sets <TEST_SET>... [OPTIONS]

OPTIONS:
    --models <MODEL>...
            Paths to model configurations (2-5 models)

    --test-sets <TEST_SET>...
            Paths to test sets in JSONL format

    --criteria <SPEC>
            Criteria specification in format: "name:weight:direction,..."
            Example: "accuracy:0.4:higher,latency_p95:0.3:lower"
            Default: "accuracy:0.4:higher,latency_p95:0.3:lower,token_usage:0.2:lower,error_rate:0.1:lower"

    --require-significance
            Require statistical significance for winner (default: true)

    --no-require-significance
            Do not require statistical significance

    --min-effect-size <VALUE>
            Minimum effect size (Cohen's d) to consider (default: 0.3)

    --num-runs <N>
            Number of evaluation runs per model (default: 3)

    --format <FORMAT>
            Output format: table, json, html (default: table)

    --output <PATH>
            Output path (stdout if not specified)

    --verbose, -v
            Verbose output

    --help, -h
            Print this help message

EXAMPLES:
    # Basic comparison with 3 models
    model-comparison \
        --models model1.json model2.json baseline.json \
        --test-sets data/test.jsonl

    # Advanced comparison with custom criteria
    model-comparison \
        --models gpt4.json gpt35.json claude.json \
        --test-sets data/test.jsonl data/holdout.jsonl \
        --criteria "accuracy:0.5:higher,latency_p95:0.3:lower,cost:0.2:lower" \
        --min-effect-size 0.4 \
        --num-runs 5 \
        --format html \
        --output comparison-report.html

    # Quick comparison without significance requirement
    model-comparison \
        --models modelA.json modelB.json \
        --test-sets data/quick-test.jsonl \
        --no-require-significance \
        --num-runs 1 \
        --format table
"#
    );
}

#[tokio::main]
async fn main() -> Result<()> {
    // Parse arguments
    let args = Args::parse().context("Failed to parse arguments")?;

    if args.verbose {
        println!("Model Comparison Tool");
        println!("====================\n");
        println!("Models: {:?}", args.model_paths);
        println!("Test sets: {:?}", args.test_sets);
        println!("Criteria: {} criteria", args.criteria.len());
        println!("Require significance: {}", args.require_significance);
        println!("Min effect size: {}", args.min_effect_size);
        println!("Num runs: {}", args.num_runs);
        println!();
    }

    // Create comparison configuration
    let config = ComparisonConfig {
        test_sets: args.test_sets.clone(),
        criteria: args.criteria.clone(),
        require_significance: args.require_significance,
        min_effect_size: args.min_effect_size,
        num_runs: args.num_runs,
        alpha: 0.05,
    };

    // Create comparator
    let comparator = ModelComparator::new(config);

    // Run comparison
    if args.verbose {
        println!("Running comparison...\n");
    }

    let start = std::time::Instant::now();
    let results = comparator
        .compare_models(&args.model_paths)
        .await
        .context("Comparison failed")?;
    let elapsed = start.elapsed();

    if args.verbose {
        println!("Comparison completed in {:.2}s\n", elapsed.as_secs_f64());
    }

    // Generate output based on format
    match args.output_format {
        OutputFormat::Table => {
            let table = results.to_ascii_table();
            print_or_save(&table, args.output_path.as_ref())?;

            // Print winner information
            if let Some(winner) = &results.winner {
                println!("\nWinner: {} (score: {:.3})", winner.model_name, winner.total_score);
                println!("{}", winner.recommendation);

                if !winner.significant_improvements.is_empty() {
                    println!("\nSignificant improvements:");
                    for improvement in &winner.significant_improvements {
                        println!("  - {}", improvement);
                    }
                }
            }
        }
        OutputFormat::Json => {
            let json = serde_json::to_string_pretty(&results)?;
            print_or_save(&json, args.output_path.as_ref())?;
        }
        OutputFormat::Html => {
            let html = results.generate_html_report();
            print_or_save(&html, args.output_path.as_ref())?;

            if args.verbose && args.output_path.is_some() {
                println!("HTML report saved to: {:?}", args.output_path.unwrap());
            }
        }
    }

    // Export detailed results if verbose
    if args.verbose {
        let json_path = "comparison-results.json";
        results.export_json(json_path)?;
        println!("\nDetailed results exported to: {}", json_path);
    }

    Ok(())
}

/// Print to stdout or save to file.
fn print_or_save(content: &str, path: Option<&PathBuf>) -> Result<()> {
    match path {
        Some(p) => {
            std::fs::write(p, content).context("Failed to write output file")?;
        }
        None => {
            println!("{}", content);
        }
    }
    Ok(())
}
