use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=signatures.txt");
    println!("cargo:rerun-if-changed=build.rs");

    // Get project paths
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR not set");
    let out_dir = PathBuf::from(&manifest_dir).join("src");

    // Input: signatures.txt
    let signatures_file = PathBuf::from(&manifest_dir).join("signatures.txt");
    if !signatures_file.exists() {
        panic!(
            "signatures.txt not found at: {}",
            signatures_file.display()
        );
    }

    // Output: src/generated.rs
    let output_file = out_dir.join("generated.rs");

    // Locate signature_codegen.py
    // It should be at ../../signature_codegen.py relative to this example
    let codegen_script = PathBuf::from(&manifest_dir)
        .join("..")
        .join("..")
        .join("signature_codegen.py");

    if !codegen_script.exists() {
        panic!(
            "signature_codegen.py not found at: {}\n\
             Expected location: skills/rust/pyo3-dspy-type-system/signature_codegen.py",
            codegen_script.display()
        );
    }

    println!("cargo:warning=Running signature codegen...");
    println!(
        "cargo:warning=  Script: {}",
        codegen_script.display()
    );
    println!(
        "cargo:warning=  Input:  {}",
        signatures_file.display()
    );
    println!(
        "cargo:warning=  Output: {}",
        output_file.display()
    );

    // Execute Python codegen script
    let output = Command::new("python3")
        .arg(&codegen_script)
        .arg(&signatures_file)
        .arg(&output_file)
        .output()
        .expect("Failed to execute signature_codegen.py");

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);

        eprintln!("=== Code Generation Failed ===");
        eprintln!("STDOUT:\n{}", stdout);
        eprintln!("STDERR:\n{}", stderr);
        eprintln!("==============================");

        panic!(
            "signature_codegen.py failed with exit code: {:?}",
            output.status.code()
        );
    }

    // Verify output file was created
    if !output_file.exists() {
        panic!(
            "Code generation completed but output file not found: {}",
            output_file.display()
        );
    }

    // Print generation stats
    let stdout = String::from_utf8_lossy(&output.stdout);
    if !stdout.is_empty() {
        println!("cargo:warning=Codegen output: {}", stdout.trim());
    }

    // Read generated file to count types
    let generated_content = fs::read_to_string(&output_file)
        .expect("Failed to read generated file");

    let struct_count = generated_content.matches("pub struct").count();
    println!(
        "cargo:warning=Successfully generated {} types from signatures",
        struct_count
    );

    // Validate generated code compiles (basic syntax check)
    if generated_content.is_empty() {
        panic!("Generated file is empty - codegen may have failed silently");
    }

    if !generated_content.contains("#[derive(") {
        panic!("Generated file missing derive attributes - invalid output");
    }
}
