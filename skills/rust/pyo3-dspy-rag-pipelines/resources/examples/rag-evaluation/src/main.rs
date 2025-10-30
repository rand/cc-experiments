use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::fs;

/// Test query with ground truth for evaluation
#[derive(Debug, Deserialize, Serialize, Clone)]
struct TestQuery {
    id: String,
    query: String,
    relevant_docs: Vec<String>,
    ground_truth_answer: String,
    keywords: Vec<String>,
}

/// Test set containing multiple queries
#[derive(Debug, Deserialize, Serialize)]
struct TestSet {
    queries: Vec<TestQuery>,
}

/// Metrics for a single query evaluation
#[derive(Debug, Clone)]
struct QueryMetrics {
    query_id: String,
    // Retrieval metrics
    precision_at_k: f64,
    recall_at_k: f64,
    mrr: f64,
    ndcg: f64,
    // Generation metrics
    bleu: f64,
    rouge_1: f64,
    rouge_2: f64,
    rouge_l: f64,
    answer_relevance: f64,
}

/// Aggregate statistics across all queries
#[derive(Debug, Default)]
struct AggregateMetrics {
    avg_precision: f64,
    avg_recall: f64,
    avg_mrr: f64,
    avg_ndcg: f64,
    avg_bleu: f64,
    avg_rouge_1: f64,
    avg_rouge_2: f64,
    avg_rouge_l: f64,
    avg_relevance: f64,
    count: usize,
}

/// Main RAG evaluation framework
struct RagEvaluator {
    results: Vec<QueryMetrics>,
}

impl RagEvaluator {
    fn new() -> Self {
        Self {
            results: Vec::new(),
        }
    }

    /// Load test set from JSON file
    fn load_test_set(&self, path: &str) -> Result<TestSet> {
        let content = fs::read_to_string(path)
            .with_context(|| format!("Failed to read test set from {}", path))?;
        let test_set: TestSet = serde_json::from_str(&content)
            .with_context(|| "Failed to parse test set JSON")?;
        Ok(test_set)
    }

    /// Calculate precision@k: fraction of retrieved docs that are relevant
    fn precision_at_k(&self, retrieved: &[String], relevant: &HashSet<String>) -> f64 {
        if retrieved.is_empty() {
            return 0.0;
        }
        let relevant_count = retrieved
            .iter()
            .filter(|doc| relevant.contains(*doc))
            .count();
        relevant_count as f64 / retrieved.len() as f64
    }

    /// Calculate recall@k: fraction of relevant docs that are retrieved
    fn recall_at_k(&self, retrieved: &[String], relevant: &HashSet<String>) -> f64 {
        if relevant.is_empty() {
            return 0.0;
        }
        let retrieved_relevant = retrieved
            .iter()
            .filter(|doc| relevant.contains(*doc))
            .count();
        retrieved_relevant as f64 / relevant.len() as f64
    }

    /// Calculate Mean Reciprocal Rank: 1 / rank of first relevant doc
    fn mrr(&self, retrieved: &[String], relevant: &HashSet<String>) -> f64 {
        for (idx, doc) in retrieved.iter().enumerate() {
            if relevant.contains(doc) {
                return 1.0 / (idx + 1) as f64;
            }
        }
        0.0
    }

    /// Calculate NDCG (Normalized Discounted Cumulative Gain)
    fn ndcg(&self, retrieved: &[String], relevant: &HashSet<String>) -> f64 {
        if relevant.is_empty() {
            return 0.0;
        }

        // Calculate DCG
        let dcg: f64 = retrieved
            .iter()
            .enumerate()
            .map(|(idx, doc)| {
                let relevance = if relevant.contains(doc) { 1.0 } else { 0.0 };
                relevance / ((idx + 2) as f64).log2()
            })
            .sum();

        // Calculate IDCG (ideal DCG with perfect ranking)
        let idcg: f64 = (0..retrieved.len().min(relevant.len()))
            .map(|idx| 1.0 / ((idx + 2) as f64).log2())
            .sum();

        if idcg == 0.0 {
            0.0
        } else {
            dcg / idcg
        }
    }

    /// Calculate BLEU score for generated text
    fn bleu(&self, generated: &str, reference: &str) -> f64 {
        let gen_tokens: Vec<&str> = generated.split_whitespace().collect();
        let ref_tokens: Vec<&str> = reference.split_whitespace().collect();

        if gen_tokens.is_empty() || ref_tokens.is_empty() {
            return 0.0;
        }

        // Brevity penalty
        let bp = if gen_tokens.len() < ref_tokens.len() {
            (1.0 - (ref_tokens.len() as f64 / gen_tokens.len() as f64)).exp()
        } else {
            1.0
        };

        // Calculate precision for unigrams (simplified BLEU-1)
        let gen_set: HashSet<_> = gen_tokens.iter().collect();
        let ref_set: HashSet<_> = ref_tokens.iter().collect();
        let matches = gen_set.intersection(&ref_set).count();
        let precision = matches as f64 / gen_tokens.len() as f64;

        bp * precision
    }

    /// Calculate ROUGE-N score (n-gram overlap)
    fn rouge_n(&self, generated: &str, reference: &str, n: usize) -> f64 {
        let gen_tokens: Vec<&str> = generated.split_whitespace().collect();
        let ref_tokens: Vec<&str> = reference.split_whitespace().collect();

        if gen_tokens.len() < n || ref_tokens.len() < n {
            return 0.0;
        }

        let gen_ngrams: HashSet<Vec<&str>> = gen_tokens
            .windows(n)
            .map(|w| w.to_vec())
            .collect();
        let ref_ngrams: HashSet<Vec<&str>> = ref_tokens
            .windows(n)
            .map(|w| w.to_vec())
            .collect();

        let matches = gen_ngrams.intersection(&ref_ngrams).count();
        if ref_ngrams.is_empty() {
            0.0
        } else {
            matches as f64 / ref_ngrams.len() as f64
        }
    }

    /// Calculate ROUGE-L (Longest Common Subsequence)
    fn rouge_l(&self, generated: &str, reference: &str) -> f64 {
        let gen_tokens: Vec<&str> = generated.split_whitespace().collect();
        let ref_tokens: Vec<&str> = reference.split_whitespace().collect();

        let lcs_length = self.lcs_length(&gen_tokens, &ref_tokens);

        if ref_tokens.is_empty() {
            0.0
        } else {
            lcs_length as f64 / ref_tokens.len() as f64
        }
    }

    /// Calculate longest common subsequence length
    fn lcs_length(&self, a: &[&str], b: &[&str]) -> usize {
        let m = a.len();
        let n = b.len();
        let mut dp = vec![vec![0; n + 1]; m + 1];

        for i in 1..=m {
            for j in 1..=n {
                if a[i - 1] == b[j - 1] {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                } else {
                    dp[i][j] = dp[i - 1][j].max(dp[i][j - 1]);
                }
            }
        }

        dp[m][n]
    }

    /// Calculate answer relevance based on keyword overlap
    fn answer_relevance(&self, generated: &str, keywords: &[String]) -> f64 {
        if keywords.is_empty() {
            return 0.0;
        }

        let generated_lower = generated.to_lowercase();
        let matches = keywords
            .iter()
            .filter(|kw| generated_lower.contains(&kw.to_lowercase()))
            .count();

        matches as f64 / keywords.len() as f64
    }

    /// Evaluate a single query
    fn evaluate_query(
        &self,
        query_id: &str,
        retrieved: &[String],
        relevant: &[String],
        generated: &str,
        reference: &str,
        keywords: &[String],
    ) -> QueryMetrics {
        let relevant_set: HashSet<String> = relevant.iter().cloned().collect();

        QueryMetrics {
            query_id: query_id.to_string(),
            precision_at_k: self.precision_at_k(retrieved, &relevant_set),
            recall_at_k: self.recall_at_k(retrieved, &relevant_set),
            mrr: self.mrr(retrieved, &relevant_set),
            ndcg: self.ndcg(retrieved, &relevant_set),
            bleu: self.bleu(generated, reference),
            rouge_1: self.rouge_n(generated, reference, 1),
            rouge_2: self.rouge_n(generated, reference, 2),
            rouge_l: self.rouge_l(generated, reference),
            answer_relevance: self.answer_relevance(generated, keywords),
        }
    }

    /// Add evaluation result
    fn add_result(&mut self, metrics: QueryMetrics) {
        self.results.push(metrics);
    }

    /// Calculate aggregate statistics
    fn aggregate(&self) -> AggregateMetrics {
        if self.results.is_empty() {
            return AggregateMetrics::default();
        }

        let count = self.results.len();
        AggregateMetrics {
            avg_precision: self.results.iter().map(|m| m.precision_at_k).sum::<f64>() / count as f64,
            avg_recall: self.results.iter().map(|m| m.recall_at_k).sum::<f64>() / count as f64,
            avg_mrr: self.results.iter().map(|m| m.mrr).sum::<f64>() / count as f64,
            avg_ndcg: self.results.iter().map(|m| m.ndcg).sum::<f64>() / count as f64,
            avg_bleu: self.results.iter().map(|m| m.bleu).sum::<f64>() / count as f64,
            avg_rouge_1: self.results.iter().map(|m| m.rouge_1).sum::<f64>() / count as f64,
            avg_rouge_2: self.results.iter().map(|m| m.rouge_2).sum::<f64>() / count as f64,
            avg_rouge_l: self.results.iter().map(|m| m.rouge_l).sum::<f64>() / count as f64,
            avg_relevance: self.results.iter().map(|m| m.answer_relevance).sum::<f64>() / count as f64,
            count,
        }
    }

    /// Generate HTML report
    fn generate_report(&self, output_path: &str) -> Result<()> {
        let aggregate = self.aggregate();

        let mut html = format!(
            r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG Pipeline Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-label {{ font-weight: bold; color: #666; }}
        .metric-value {{ font-size: 24px; color: #4CAF50; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #4CAF50; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f5f5f5; }}
        .bar {{ background: #4CAF50; height: 20px; border-radius: 3px; }}
        .bar-container {{ background: #ddd; height: 20px; border-radius: 3px; width: 200px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>RAG Pipeline Evaluation Report</h1>
        <div class="summary">
            <h2>Aggregate Metrics (n = {})</h2>
            <div class="metric">
                <div class="metric-label">Avg Precision@k</div>
                <div class="metric-value">{:.3}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg Recall@k</div>
                <div class="metric-value">{:.3}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg MRR</div>
                <div class="metric-value">{:.3}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg NDCG</div>
                <div class="metric-value">{:.3}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg BLEU</div>
                <div class="metric-value">{:.3}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg ROUGE-L</div>
                <div class="metric-value">{:.3}</div>
            </div>
        </div>

        <h2>Per-Query Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Query ID</th>
                    <th>Precision@k</th>
                    <th>Recall@k</th>
                    <th>MRR</th>
                    <th>NDCG</th>
                    <th>BLEU</th>
                    <th>ROUGE-1</th>
                    <th>ROUGE-L</th>
                    <th>Relevance</th>
                </tr>
            </thead>
            <tbody>
"#,
            aggregate.count,
            aggregate.avg_precision,
            aggregate.avg_recall,
            aggregate.avg_mrr,
            aggregate.avg_ndcg,
            aggregate.avg_bleu,
            aggregate.avg_rouge_l,
        );

        for result in &self.results {
            html.push_str(&format!(
                r#"                <tr>
                    <td>{}</td>
                    <td>{:.3}</td>
                    <td>{:.3}</td>
                    <td>{:.3}</td>
                    <td>{:.3}</td>
                    <td>{:.3}</td>
                    <td>{:.3}</td>
                    <td>{:.3}</td>
                    <td>{:.3}</td>
                </tr>
"#,
                result.query_id,
                result.precision_at_k,
                result.recall_at_k,
                result.mrr,
                result.ndcg,
                result.bleu,
                result.rouge_1,
                result.rouge_l,
                result.answer_relevance,
            ));
        }

        html.push_str(
            r#"            </tbody>
        </table>
    </div>
</body>
</html>
"#,
        );

        fs::write(output_path, html)
            .with_context(|| format!("Failed to write report to {}", output_path))?;

        Ok(())
    }
}

/// Mock RAG system for demonstration
fn mock_rag_pipeline(query: &str) -> (Vec<String>, String) {
    // Mock retrieval: return some document IDs
    let retrieved = vec![
        "doc1".to_string(),
        "doc2".to_string(),
        "doc3".to_string(),
        "doc5".to_string(),
        "doc8".to_string(),
    ];

    // Mock generation: simple answer based on query
    let generated = match query {
        q if q.contains("machine learning") => {
            "Machine learning is a field of artificial intelligence that enables systems to learn from data and improve performance."
        }
        q if q.contains("neural network") => {
            "Neural networks are computational models inspired by biological neural networks in the brain."
        }
        q if q.contains("gradient descent") => {
            "Gradient descent is an optimization algorithm used to minimize loss functions in machine learning."
        }
        _ => "This is a generated answer based on retrieved context.",
    };

    (retrieved, generated.to_string())
}

fn main() -> Result<()> {
    println!("=== RAG Pipeline Evaluation ===\n");

    let mut evaluator = RagEvaluator::new();

    // Load test set
    let test_set = evaluator
        .load_test_set("testset.json")
        .context("Failed to load test set")?;

    println!("Loaded {} test queries\n", test_set.queries.len());

    // Evaluate each query
    for test_query in &test_set.queries {
        println!("Query: {}", test_query.query);

        // Run mock RAG pipeline
        let (retrieved_docs, generated_answer) = mock_rag_pipeline(&test_query.query);

        println!("Retrieved: {} documents", retrieved_docs.len());
        let relevant_in_results = retrieved_docs
            .iter()
            .filter(|doc| test_query.relevant_docs.contains(doc))
            .count();
        println!("Relevant in results: {}\n", relevant_in_results);

        // Evaluate
        let metrics = evaluator.evaluate_query(
            &test_query.id,
            &retrieved_docs,
            &test_query.relevant_docs,
            &generated_answer,
            &test_query.ground_truth_answer,
            &test_query.keywords,
        );

        // Display results
        println!("Retrieval Metrics:");
        println!("  Precision@5: {:.3}", metrics.precision_at_k);
        println!("  Recall@5: {:.3}", metrics.recall_at_k);
        println!("  MRR: {:.3}", metrics.mrr);
        println!("  NDCG@5: {:.3}", metrics.ndcg);

        println!("\nGenerated Answer: {}", generated_answer);

        println!("\nGeneration Metrics:");
        println!("  BLEU: {:.3}", metrics.bleu);
        println!("  ROUGE-1: {:.3}", metrics.rouge_1);
        println!("  ROUGE-2: {:.3}", metrics.rouge_2);
        println!("  ROUGE-L: {:.3}", metrics.rouge_l);
        println!("  Answer Relevance: {:.3}", metrics.answer_relevance);

        println!("\n---\n");

        evaluator.add_result(metrics);
    }

    // Display aggregate statistics
    let aggregate = evaluator.aggregate();
    println!("Aggregate Statistics ({} queries):", aggregate.count);
    println!("  Avg Precision@5: {:.3}", aggregate.avg_precision);
    println!("  Avg Recall@5: {:.3}", aggregate.avg_recall);
    println!("  Avg MRR: {:.3}", aggregate.avg_mrr);
    println!("  Avg NDCG@5: {:.3}", aggregate.avg_ndcg);
    println!("  Avg BLEU: {:.3}", aggregate.avg_bleu);
    println!("  Avg ROUGE-1: {:.3}", aggregate.avg_rouge_1);
    println!("  Avg ROUGE-2: {:.3}", aggregate.avg_rouge_2);
    println!("  Avg ROUGE-L: {:.3}", aggregate.avg_rouge_l);
    println!("  Avg Relevance: {:.3}", aggregate.avg_relevance);

    // Generate HTML report
    evaluator.generate_report("evaluation_report.html")?;
    println!("\nReport saved to: evaluation_report.html");

    Ok(())
}
