use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// UserProfile demonstrates various optional field patterns
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct UserProfile {
    // Required fields (no Option wrapper)
    pub user_id: String,
    pub username: String,

    // Optional text field
    #[serde(skip_serializing_if = "Option::is_none")]
    pub email: Option<String>,

    // Optional numeric field
    #[serde(skip_serializing_if = "Option::is_none")]
    pub age: Option<i64>,

    // Optional long text field
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bio: Option<String>,

    // Optional collection
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,

    // Optional boolean flag
    #[serde(skip_serializing_if = "Option::is_none")]
    pub is_verified: Option<bool>,

    // Optional nested structure
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<HashMap<String, String>>,
}

impl Default for UserProfile {
    fn default() -> Self {
        Self {
            user_id: String::new(),
            username: String::new(),
            email: None,
            age: None,
            bio: None,
            tags: Some(Vec::new()), // Default to empty collection
            is_verified: Some(false), // Default to unverified
            metadata: None,
        }
    }
}

impl UserProfile {
    /// Create a new profile with only required fields
    pub fn new(user_id: impl Into<String>, username: impl Into<String>) -> Self {
        Self {
            user_id: user_id.into(),
            username: username.into(),
            ..Default::default()
        }
    }

    /// Safe getter for email with default
    pub fn get_email(&self) -> String {
        self.email.clone().unwrap_or_default()
    }

    /// Safe getter for age with custom default
    pub fn get_age(&self) -> i64 {
        self.age.unwrap_or(18) // Default adult age
    }

    /// Safe getter for bio with computed default
    pub fn get_bio(&self) -> String {
        self.bio.clone().unwrap_or_else(|| {
            format!("User {} has not provided a bio.", self.username)
        })
    }

    /// Safe getter for tag count using optional chaining
    pub fn tag_count(&self) -> usize {
        self.tags.as_ref().map(|t| t.len()).unwrap_or(0)
    }

    /// Safe check for specific tag
    pub fn has_tag(&self, tag: &str) -> bool {
        self.tags
            .as_ref()
            .map(|tags| tags.iter().any(|t| t == tag))
            .unwrap_or(false)
    }

    /// Get verification status as string
    pub fn verification_status(&self) -> &str {
        match self.is_verified {
            Some(true) => "Verified",
            Some(false) => "Not verified",
            None => "Unknown",
        }
    }

    /// Get metadata value with default
    pub fn get_metadata(&self, key: &str) -> Option<String> {
        self.metadata
            .as_ref()
            .and_then(|map| map.get(key).cloned())
    }
}

fn main() -> Result<()> {
    println!("=== Optional Fields Example ===\n");

    // Example 1: Complete profile with all fields
    println!("1. Complete Profile (all fields present):");
    let complete_json = r#"{
        "user_id": "usr_001",
        "username": "alice",
        "email": "alice@example.com",
        "age": 28,
        "bio": "Software engineer and open source enthusiast",
        "tags": ["rust", "python", "dspy"],
        "is_verified": true,
        "metadata": {
            "location": "San Francisco",
            "joined": "2024-01-15"
        }
    }"#;

    let complete: UserProfile = serde_json::from_str(complete_json)?;
    println!("Parsed: {:#?}\n", complete);
    println!("Email: {}", complete.get_email());
    println!("Age: {}", complete.get_age());
    println!("Bio: {}", complete.get_bio());
    println!("Tags: {}", complete.tag_count());
    println!("Status: {}", complete.verification_status());
    println!("Has 'rust' tag: {}", complete.has_tag("rust"));
    println!(
        "Location: {}\n",
        complete.get_metadata("location").unwrap_or_default()
    );

    // Example 2: Minimal profile (only required fields)
    println!("2. Minimal Profile (only required fields):");
    let minimal_json = r#"{
        "user_id": "usr_002",
        "username": "bob"
    }"#;

    let minimal: UserProfile = serde_json::from_str(minimal_json)?;
    println!("Parsed: {:#?}\n", minimal);
    println!("Email: '{}' (empty default)", minimal.get_email());
    println!("Age: {} (default)", minimal.get_age());
    println!("Bio: {}", minimal.get_bio());
    println!("Tags: {} (default)", minimal.tag_count());
    println!("Status: {}", minimal.verification_status());
    println!("Has 'rust' tag: {}\n", minimal.has_tag("rust"));

    // Example 3: Partial profile (mix of Some and None)
    println!("3. Partial Profile (mix of Some/None):");
    let partial_json = r#"{
        "user_id": "usr_003",
        "username": "charlie",
        "email": "charlie@example.com",
        "tags": ["python"]
    }"#;

    let partial: UserProfile = serde_json::from_str(partial_json)?;
    println!("Parsed: {:#?}\n", partial);
    println!("Email: {}", partial.get_email());
    println!("Age: {} (default)", partial.get_age());
    println!("Tags: {}", partial.tag_count());
    println!("Has 'python' tag: {}", partial.has_tag("python"));
    println!("Has 'rust' tag: {}\n", partial.has_tag("rust"));

    // Example 4: Creating profiles programmatically
    println!("4. Programmatic Creation:");
    let mut diana = UserProfile::new("usr_004", "diana");
    println!("New profile: {:#?}\n", diana);
    println!("Default email: '{}'", diana.get_email());
    println!("Default age: {}", diana.get_age());
    println!("Default is_verified: {}\n", diana.verification_status());

    // Updating optional fields
    diana.email = Some("diana@example.com".to_string());
    diana.age = Some(32);
    diana.bio = Some("Data scientist specializing in ML".to_string());
    diana.tags = Some(vec!["python".to_string(), "ml".to_string()]);
    diana.is_verified = Some(true);

    let mut metadata = HashMap::new();
    metadata.insert("department".to_string(), "Research".to_string());
    diana.metadata = Some(metadata);

    println!("Updated profile: {:#?}\n", diana);
    println!("Email: {}", diana.get_email());
    println!("Age: {}", diana.get_age());
    println!("Status: {}\n", diana.verification_status());

    // Example 5: Serialization (None values are omitted)
    println!("5. Serialization (clean JSON):");
    let serialized = serde_json::to_string_pretty(&minimal)?;
    println!("Minimal profile JSON:\n{}\n", serialized);

    let serialized_complete = serde_json::to_string_pretty(&complete)?;
    println!("Complete profile JSON:\n{}\n", serialized_complete);

    // Example 6: Optional chaining patterns
    println!("6. Optional Chaining Patterns:");
    let test_profile = UserProfile {
        user_id: "usr_005".to_string(),
        username: "eve".to_string(),
        tags: Some(vec![
            "rust".to_string(),
            "systems".to_string(),
            "performance".to_string(),
        ]),
        ..Default::default()
    };

    // Pattern 1: map + unwrap_or
    let first_tag = test_profile
        .tags
        .as_ref()
        .and_then(|tags| tags.first())
        .map(|tag| tag.as_str())
        .unwrap_or("no-tag");
    println!("First tag: {}", first_tag);

    // Pattern 2: filter + count
    let long_tags = test_profile
        .tags
        .as_ref()
        .map(|tags| tags.iter().filter(|t| t.len() > 5).count())
        .unwrap_or(0);
    println!("Tags longer than 5 chars: {}", long_tags);

    // Pattern 3: transform collection
    let tag_string = test_profile
        .tags
        .as_ref()
        .map(|tags| tags.join(", "))
        .unwrap_or_else(|| "None".to_string());
    println!("Tags as string: {}\n", tag_string);

    // Example 7: Handling empty vs None
    println!("7. Empty vs None distinction:");
    let empty_tags_profile = UserProfile {
        user_id: "usr_006".to_string(),
        username: "frank".to_string(),
        tags: Some(Vec::new()), // Empty collection
        ..Default::default()
    };

    let no_tags_profile = UserProfile {
        user_id: "usr_007".to_string(),
        username: "grace".to_string(),
        tags: None, // No collection
        ..Default::default()
    };

    println!("Empty tags (Some(vec![])):");
    println!("  tags.is_some(): {}", empty_tags_profile.tags.is_some());
    println!("  tag_count(): {}\n", empty_tags_profile.tag_count());

    println!("No tags (None):");
    println!("  tags.is_some(): {}", no_tags_profile.tags.is_some());
    println!("  tag_count(): {}\n", no_tags_profile.tag_count());

    println!("=== Example Complete ===");
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_profile() {
        let profile = UserProfile::default();
        assert_eq!(profile.user_id, "");
        assert_eq!(profile.username, "");
        assert_eq!(profile.email, None);
        assert_eq!(profile.age, None);
        assert_eq!(profile.tags, Some(Vec::new()));
        assert_eq!(profile.is_verified, Some(false));
    }

    #[test]
    fn test_new_profile() {
        let profile = UserProfile::new("123", "alice");
        assert_eq!(profile.user_id, "123");
        assert_eq!(profile.username, "alice");
        assert_eq!(profile.get_email(), "");
        assert_eq!(profile.get_age(), 18);
    }

    #[test]
    fn test_safe_getters() {
        let profile = UserProfile {
            user_id: "1".to_string(),
            username: "test".to_string(),
            email: Some("test@example.com".to_string()),
            age: Some(25),
            ..Default::default()
        };

        assert_eq!(profile.get_email(), "test@example.com");
        assert_eq!(profile.get_age(), 25);
    }

    #[test]
    fn test_tag_operations() {
        let profile = UserProfile {
            user_id: "1".to_string(),
            username: "test".to_string(),
            tags: Some(vec!["rust".to_string(), "python".to_string()]),
            ..Default::default()
        };

        assert_eq!(profile.tag_count(), 2);
        assert!(profile.has_tag("rust"));
        assert!(profile.has_tag("python"));
        assert!(!profile.has_tag("java"));
    }

    #[test]
    fn test_verification_status() {
        let verified = UserProfile {
            is_verified: Some(true),
            ..Default::default()
        };
        assert_eq!(verified.verification_status(), "Verified");

        let unverified = UserProfile {
            is_verified: Some(false),
            ..Default::default()
        };
        assert_eq!(unverified.verification_status(), "Not verified");

        let unknown = UserProfile {
            is_verified: None,
            ..Default::default()
        };
        assert_eq!(unknown.verification_status(), "Unknown");
    }
}
