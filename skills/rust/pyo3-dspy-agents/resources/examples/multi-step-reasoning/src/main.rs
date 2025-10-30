//! Multi-Step Reasoning Examples
//!
//! This binary demonstrates the multi-step reasoning system with various
//! complex questions that require decomposition and synthesis.

use colored::Colorize;
use multi_step_reasoning::{MultiStepReasoner, ReasoningChain, ReasoningConfig};
use std::io::{self, Write};
use std::time::Instant;
use tracing::{info, warn};
use tracing_subscriber;

/// Example complex questions for multi-step reasoning
const EXAMPLE_QUESTIONS: &[(&str, &str)] = &[
    (
        "Historical Analysis",
        "What factors contributed to the fall of the Roman Empire and how did they interact?"
    ),
    (
        "Scientific Reasoning",
        "How does climate change affect ocean currents, and what are the cascading effects on weather patterns?"
    ),
    (
        "Economic Analysis",
        "What are the relationships between inflation, unemployment, and GDP growth in modern economies?"
    ),
    (
        "Technical Problem",
        "What are the trade-offs between microservices and monolithic architectures, and when should each be used?"
    ),
    (
        "Philosophical Question",
        "How do consciousness, free will, and determinism relate to each other in modern neuroscience?"
    ),
];

fn main() -> anyhow::Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter("multi_step_reasoning=info")
        .init();

    info!("Starting Multi-Step Reasoning Examples");

    // Print welcome banner
    print_banner();

    // Main menu loop
    loop {
        print_menu();

        let choice = read_input("Enter your choice (1-7): ")?;

        match choice.trim() {
            "1" => run_example_questions()?,
            "2" => run_custom_question()?,
            "3" => run_comparison_demo()?,
            "4" => run_chain_visualization_demo()?,
            "5" => run_export_demo()?,
            "6" => print_help(),
            "7" => {
                println!("{}", "Goodbye!".green().bold());
                break;
            }
            _ => {
                warn!("Invalid choice. Please try again.");
            }
        }

        println!("\n{}", "─".repeat(80).bright_black());
    }

    Ok(())
}

/// Print welcome banner
fn print_banner() {
    println!("\n{}", "═".repeat(80).cyan().bold());
    println!(
        "{}",
        "  Multi-Step Reasoning with DSPy".cyan().bold()
    );
    println!(
        "{}",
        "  Decompose → Solve → Synthesize".bright_white()
    );
    println!("{}\n", "═".repeat(80).cyan().bold());
}

/// Print main menu
fn print_menu() {
    println!("\n{}", "Main Menu".yellow().bold());
    println!("  1. Run example questions");
    println!("  2. Ask a custom question");
    println!("  3. Compare reasoning strategies");
    println!("  4. Visualize reasoning chains");
    println!("  5. Export reasoning to JSON");
    println!("  6. Help");
    println!("  7. Exit");
    println!();
}

/// Print help information
fn print_help() {
    println!("\n{}", "Multi-Step Reasoning Help".yellow().bold());
    println!("\n{}", "How it works:".green().bold());
    println!("  1. {} Your complex question is decomposed into simpler sub-questions", "Decompose:".cyan());
    println!("  2. {} Each sub-question is solved independently using ReAct", "Solve:".cyan());
    println!("  3. {} Sub-answers are combined into a coherent final answer", "Synthesize:".cyan());
    println!("\n{}", "Tips for best results:".green().bold());
    println!("  - Ask questions that have multiple interconnected aspects");
    println!("  - Be specific about what relationships or interactions you want to explore");
    println!("  - Complex questions work better than simple factual queries");
    println!("\n{}", "Example good questions:".green().bold());
    println!("  - How do X and Y interact to produce effect Z?");
    println!("  - What are the causes, effects, and feedback loops of phenomenon X?");
    println!("  - Compare and contrast A and B across multiple dimensions");
}

/// Run example questions
fn run_example_questions() -> anyhow::Result<()> {
    println!("\n{}", "Example Questions".yellow().bold());

    // Let user select an example
    for (idx, (category, question)) in EXAMPLE_QUESTIONS.iter().enumerate() {
        println!("  {}. {}: {}", idx + 1, category.cyan(), question);
    }

    let choice = read_input("\nSelect an example (1-5, or 0 for all): ")?;
    let choice = choice.trim();

    if choice == "0" {
        // Run all examples
        for (category, question) in EXAMPLE_QUESTIONS.iter() {
            println!("\n{}", "─".repeat(80).bright_black());
            run_single_question(category, question)?;
        }
    } else if let Ok(idx) = choice.parse::<usize>() {
        if idx > 0 && idx <= EXAMPLE_QUESTIONS.len() {
            let (category, question) = EXAMPLE_QUESTIONS[idx - 1];
            run_single_question(category, question)?;
        } else {
            println!("{}", "Invalid selection".red());
        }
    }

    Ok(())
}

/// Run a single question through the reasoner
fn run_single_question(category: &str, question: &str) -> anyhow::Result<()> {
    println!("\n{} {}", "Category:".green().bold(), category);
    println!("{} {}", "Question:".green().bold(), question);

    // Create reasoner with default config
    let config = ReasoningConfig::default();
    println!("\n{}", "Initializing reasoner...".bright_black());
    let reasoner = MultiStepReasoner::new(config)?;

    // Execute reasoning
    println!("{}", "Reasoning in progress...".bright_black());
    let start = Instant::now();
    let chain = reasoner.reason(question)?;
    let duration = start.elapsed();

    // Display results
    println!("\n{}", "Results:".green().bold());
    print_chain_summary(&chain);

    println!("\n{} {:.2}s", "Time taken:".bright_black(), duration.as_secs_f64());

    Ok(())
}

/// Run a custom question from user input
fn run_custom_question() -> anyhow::Result<()> {
    println!("\n{}", "Custom Question".yellow().bold());
    println!("Enter your complex question (or 'back' to return):");

    let question = read_input("> ")?;

    if question.trim().to_lowercase() == "back" {
        return Ok(());
    }

    run_single_question("Custom", &question)?;

    Ok(())
}

/// Compare different reasoning strategies
fn run_comparison_demo() -> anyhow::Result<()> {
    println!("\n{}", "Reasoning Strategy Comparison".yellow().bold());

    let question = "What are the economic, social, and environmental impacts of renewable energy adoption?";
    println!("{} {}", "Question:".green().bold(), question);

    // Strategy 1: Default configuration (max 5 sub-questions)
    println!("\n{}", "Strategy 1: Standard (max 5 sub-questions)".cyan().bold());
    let config1 = ReasoningConfig {
        max_sub_questions: 5,
        ..Default::default()
    };
    let reasoner1 = MultiStepReasoner::new(config1)?;
    let start = Instant::now();
    let chain1 = reasoner1.reason(question)?;
    let duration1 = start.elapsed();

    print_chain_summary(&chain1);
    println!("{} {:.2}s", "Time:".bright_black(), duration1.as_secs_f64());

    // Strategy 2: Fewer sub-questions for faster reasoning
    println!("\n{}", "Strategy 2: Fast (max 3 sub-questions)".cyan().bold());
    let config2 = ReasoningConfig {
        max_sub_questions: 3,
        ..Default::default()
    };
    let reasoner2 = MultiStepReasoner::new(config2)?;
    let start = Instant::now();
    let chain2 = reasoner2.reason(question)?;
    let duration2 = start.elapsed();

    print_chain_summary(&chain2);
    println!("{} {:.2}s", "Time:".bright_black(), duration2.as_secs_f64());

    // Strategy 3: More sub-questions for thorough analysis
    println!("\n{}", "Strategy 3: Thorough (max 8 sub-questions)".cyan().bold());
    let config3 = ReasoningConfig {
        max_sub_questions: 8,
        ..Default::default()
    };
    let reasoner3 = MultiStepReasoner::new(config3)?;
    let start = Instant::now();
    let chain3 = reasoner3.reason(question)?;
    let duration3 = start.elapsed();

    print_chain_summary(&chain3);
    println!("{} {:.2}s", "Time:".bright_black(), duration3.as_secs_f64());

    // Comparison summary
    println!("\n{}", "Comparison Summary:".yellow().bold());
    println!("  Standard:  {} steps in {:.2}s", chain1.len(), duration1.as_secs_f64());
    println!("  Fast:      {} steps in {:.2}s", chain2.len(), duration2.as_secs_f64());
    println!("  Thorough:  {} steps in {:.2}s", chain3.len(), duration3.as_secs_f64());

    Ok(())
}

/// Demonstrate chain visualization
fn run_chain_visualization_demo() -> anyhow::Result<()> {
    println!("\n{}", "Chain Visualization Demo".yellow().bold());

    let question = "How do supply and demand interact to determine market prices?";
    println!("{} {}", "Question:".green().bold(), question);

    let config = ReasoningConfig::default();
    let reasoner = MultiStepReasoner::new(config)?;
    let chain = reasoner.reason(question)?;

    println!("\n{}", "Full Chain Visualization:".cyan().bold());
    println!("{}", chain.visualize());

    println!("\n{}", "Step-by-Step Breakdown:".cyan().bold());
    for (idx, step) in chain.steps.iter().enumerate() {
        println!("\n{} {}", format!("Step {}:", idx + 1).yellow().bold(), step.question);

        if !step.thought.is_empty() {
            println!("  {} {}", "💭".bright_black(), step.thought.bright_black());
        }

        if let Some(action) = &step.action {
            println!("  {} {}", "⚡".yellow(), action.yellow());
        }

        if let Some(observation) = &step.observation {
            println!("  {} {}", "👁️".cyan(), observation.cyan());
        }

        if let Some(conclusion) = &step.conclusion {
            println!("  {} {}", "✓".green(), conclusion.green());
        }

        if let Some(confidence) = step.confidence {
            let conf_str = format!("{:.1}%", confidence * 100.0);
            let colored_conf = if confidence > 0.8 {
                conf_str.green()
            } else if confidence > 0.6 {
                conf_str.yellow()
            } else {
                conf_str.red()
            };
            println!("  {} {}", "📊".bright_black(), colored_conf);
        }
    }

    Ok(())
}

/// Demonstrate exporting reasoning chains
fn run_export_demo() -> anyhow::Result<()> {
    println!("\n{}", "Export Demo".yellow().bold());

    let question = "What are the key differences between machine learning and traditional programming?";
    println!("{} {}", "Question:".green().bold(), question);

    let config = ReasoningConfig::default();
    let reasoner = MultiStepReasoner::new(config)?;
    let chain = reasoner.reason(question)?;

    // Export to JSON
    let json = chain.to_json()?;

    println!("\n{}", "Exported JSON:".cyan().bold());
    println!("{}", json.bright_black());

    // Demonstrate re-importing
    println!("\n{}", "Re-importing from JSON...".cyan().bold());
    let restored_chain = ReasoningChain::from_json(&json)?;

    println!("✓ Successfully restored chain with {} steps", restored_chain.len());

    if let Some(conclusion) = &restored_chain.final_conclusion {
        println!("\n{}", "Restored Conclusion:".green().bold());
        println!("{}", conclusion);
    }

    Ok(())
}

/// Print a summary of a reasoning chain
fn print_chain_summary(chain: &ReasoningChain) {
    println!("\n{} {}", "Steps:".cyan().bold(), chain.len());

    // Show first few steps
    let preview_count = chain.steps.len().min(3);
    for step in chain.steps.iter().take(preview_count) {
        println!("  {} {}", format!("{}.", step.step_number).bright_black(), step.question);
    }

    if chain.steps.len() > preview_count {
        println!("  {} ({} more steps...)", "...".bright_black(), chain.steps.len() - preview_count);
    }

    if let Some(conclusion) = &chain.final_conclusion {
        println!("\n{}", "Final Conclusion:".green().bold());
        println!("{}", conclusion);
    }

    if let Some(confidence) = chain.overall_confidence {
        let conf_str = format!("Overall Confidence: {:.1}%", confidence * 100.0);
        let colored = if confidence > 0.8 {
            conf_str.green()
        } else if confidence > 0.6 {
            conf_str.yellow()
        } else {
            conf_str.red()
        };
        println!("\n{}", colored);
    }
}

/// Read input from user
fn read_input(prompt: &str) -> io::Result<String> {
    print!("{}", prompt);
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    Ok(input.trim().to_string())
}
