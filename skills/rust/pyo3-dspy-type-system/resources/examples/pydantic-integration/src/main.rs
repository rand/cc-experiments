//! Pydantic Integration Example
//!
//! Demonstrates production-ready validation patterns with Pydantic and Rust serde.
//!
//! Key features:
//! - Bidirectional type mapping (Rust serde ↔ Pydantic)
//! - Field-level validation with Pydantic validators
//! - Validation error handling and recovery
//! - Type coercion and constraint enforcement
//! - Round-trip: Rust → JSON → Pydantic → JSON → Rust

use anyhow::{Context, Result};
use pyo3::prelude::*;
use pyo3::types::PyModule;
use serde::{Deserialize, Serialize};

/// User role matching Pydantic Literal type
#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "lowercase")]
enum Role {
    Basic,
    Premium,
    Admin,
}

/// User profile with validation constraints matching Pydantic model
#[derive(Debug, Serialize, Deserialize, Clone)]
struct UserProfile {
    email: String,
    age: u8,
    role: Role,
    #[serde(skip_serializing_if = "Option::is_none")]
    bio: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    website: Option<String>,
}

/// Review sentiment matching Pydantic Literal type
#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "lowercase")]
enum Sentiment {
    Positive,
    Neutral,
    Negative,
}

/// Product review with validation constraints matching Pydantic model
#[derive(Debug, Serialize, Deserialize, Clone)]
struct ProductReview {
    product_name: String,
    rating: u8,
    review_text: String,
    sentiment: Sentiment,
    verified_purchase: bool,
}

/// Validate a UserProfile using Pydantic
fn validate_user_profile(py: Python, profile: &UserProfile) -> Result<UserProfile> {
    // Import the models module
    let models_code = include_str!("../python/models.py");
    let models = PyModule::from_code(py, models_code, "models.py", "models")
        .context("Failed to load models.py")?;

    let user_profile_class = models.getattr("UserProfile")?;

    // Convert Rust struct to JSON
    let json_str = serde_json::to_string(profile)
        .context("Failed to serialize user profile")?;

    // Parse and validate with Pydantic
    let pydantic_model = user_profile_class
        .call_method1("model_validate_json", (json_str,))
        .context("Pydantic validation failed")?;

    // Convert back to JSON
    let validated_json = pydantic_model
        .call_method0("model_dump_json")?
        .extract::<String>()?;

    // Deserialize back to Rust
    let validated_profile: UserProfile = serde_json::from_str(&validated_json)
        .context("Failed to deserialize validated profile")?;

    Ok(validated_profile)
}

/// Validate a ProductReview using Pydantic
fn validate_product_review(py: Python, review: &ProductReview) -> Result<ProductReview> {
    // Import the models module
    let models_code = include_str!("../python/models.py");
    let models = PyModule::from_code(py, models_code, "models.py", "models")
        .context("Failed to load models.py")?;

    let review_class = models.getattr("ProductReview")?;

    // Convert Rust struct to JSON
    let json_str = serde_json::to_string(review)
        .context("Failed to serialize product review")?;

    // Parse and validate with Pydantic
    let pydantic_model = review_class
        .call_method1("model_validate_json", (json_str,))
        .context("Pydantic validation failed")?;

    // Convert back to JSON
    let validated_json = pydantic_model
        .call_method0("model_dump_json")?
        .extract::<String>()?;

    // Deserialize back to Rust
    let validated_review: ProductReview = serde_json::from_str(&validated_json)
        .context("Failed to deserialize validated review")?;

    Ok(validated_review)
}

fn main() -> Result<()> {
    println!("=== Pydantic Integration Example ===\n");

    Python::with_gil(|py| {
        // Test 1: Valid user profile
        println!("Creating valid user profile...");
        let valid_user = UserProfile {
            email: "alice@example.com".to_string(),
            age: 28,
            role: Role::Premium,
            bio: Some("Software engineer interested in AI".to_string()),
            website: Some("https://alice.dev".to_string()),
        };

        match validate_user_profile(py, &valid_user) {
            Ok(validated) => {
                println!("✓ User profile validated successfully\n");
                println!("User details:");
                println!("  Email: {}", validated.email);
                println!("  Age: {}", validated.age);
                println!("  Role: {:?}", validated.role);
                if let Some(bio) = &validated.bio {
                    println!("  Bio: {}", bio);
                }
                if let Some(website) = &validated.website {
                    println!("  Website: {}", website);
                }
                println!();
            }
            Err(e) => println!("✗ Unexpected error: {}\n", e),
        }

        // Test 2: Invalid email format
        println!("Creating invalid user (bad email)...");
        let invalid_email = UserProfile {
            email: "not-an-email".to_string(),
            age: 25,
            role: Role::Basic,
            bio: None,
            website: None,
        };

        match validate_user_profile(py, &invalid_email) {
            Ok(_) => println!("✗ Should have failed validation\n"),
            Err(e) => println!("✓ Validation failed (expected): {}\n", e),
        }

        // Test 3: Age out of range
        println!("Creating invalid user (age out of range)...");
        let invalid_age = UserProfile {
            email: "bob@example.com".to_string(),
            age: 150,
            role: Role::Basic,
            bio: None,
            website: None,
        };

        match validate_user_profile(py, &invalid_age) {
            Ok(_) => println!("✗ Should have failed validation\n"),
            Err(e) => println!("✓ Validation failed (expected): {}\n", e),
        }

        // Test 4: Valid product review
        println!("Creating product review...");
        let review = ProductReview {
            product_name: "Ergonomic Keyboard".to_string(),
            rating: 5,
            review_text: "Excellent keyboard, great for typing all day".to_string(),
            sentiment: Sentiment::Positive,
            verified_purchase: true,
        };

        match validate_product_review(py, &review) {
            Ok(validated) => {
                println!("✓ Product review validated successfully\n");
                println!("Review details:");
                println!("  Product: {}", validated.product_name);
                println!("  Rating: {}", validated.rating);
                println!("  Text: {}", validated.review_text);
                println!("  Sentiment: {:?}", validated.sentiment);
                println!("  Verified: {}", validated.verified_purchase);
                println!();
            }
            Err(e) => println!("✗ Unexpected error: {}\n", e),
        }

        // Test 5: Sentiment-rating mismatch
        println!("Creating review with sentiment-rating mismatch...");
        let mismatched = ProductReview {
            product_name: "Bad Product".to_string(),
            rating: 5,
            review_text: "This product is terrible and broke immediately".to_string(),
            sentiment: Sentiment::Negative,
            verified_purchase: true,
        };

        match validate_product_review(py, &mismatched) {
            Ok(_) => println!("✗ Should have failed validation\n"),
            Err(e) => println!("✓ Validation failed (expected): {}\n", e),
        }

        // Test 6: Validation recovery
        println!("Testing validation recovery...");
        let fixable = UserProfile {
            email: "ALICE@EXAMPLE.COM".to_string(),
            age: 30,
            role: Role::Basic,
            bio: Some("   Short bio   ".to_string()),
            website: Some("https://example.com".to_string()),
        };

        println!("Attempting to fix invalid data...");
        match validate_user_profile(py, &fixable) {
            Ok(fixed) => {
                println!("✓ Data fixed and validated successfully");
                println!("  Original email: {}", fixable.email);
                println!("  Fixed email: {}", fixed.email);
                if let (Some(original), Some(cleaned)) = (&fixable.bio, &fixed.bio) {
                    println!("  Original bio: '{}'", original);
                    println!("  Cleaned bio: '{}'", cleaned);
                }
                println!();
            }
            Err(e) => println!("✗ Could not fix: {}\n", e),
        }

        Ok::<(), anyhow::Error>(())
    })?;

    println!("=== Example Complete ===");
    Ok(())
}
