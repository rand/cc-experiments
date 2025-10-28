// EdDSA (Ed25519) Artifact Signing Example
//
// Demonstrates Ed25519 signature generation and verification for artifact signing.
// Ed25519 is a modern signature algorithm with excellent performance and security properties.
//
// Features:
// - Ed25519 key generation
// - Fast signature generation
// - Signature verification
// - Batch signing
// - JSON manifest creation
//
// Production Considerations:
// - Ed25519 provides ~128-bit security level
// - Fixed key size (256 bits) and signature size (512 bits)
// - Extremely fast compared to RSA and ECDSA
// - No parameter choices (deterministic, simple API)
// - Suitable for high-throughput signing operations

package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"time"
)

// SignatureBundle contains signature and metadata
type SignatureBundle struct {
	Signature     string            `json:"signature"`
	ArtifactHash  string            `json:"artifact_hash"`
	HashAlgorithm string            `json:"hash_algorithm"`
	Algorithm     string            `json:"algorithm"`
	Timestamp     string            `json:"timestamp"`
	Metadata      map[string]string `json:"metadata,omitempty"`
}

// Manifest contains multiple signed artifacts
type Manifest struct {
	Version   string                      `json:"version"`
	Timestamp string                      `json:"timestamp"`
	Artifacts map[string]SignatureBundle  `json:"artifacts"`
	PublicKey string                      `json:"public_key"`
}

// generateKeyPair generates an Ed25519 key pair
func generateKeyPair() (ed25519.PublicKey, ed25519.PrivateKey, error) {
	publicKey, privateKey, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return nil, nil, fmt.Errorf("key generation failed: %w", err)
	}
	return publicKey, privateKey, nil
}

// saveKeyPair saves keys to PEM files
func saveKeyPair(publicKey ed25519.PublicKey, privateKey ed25519.PrivateKey, baseName string) error {
	// Save private key
	privateFile := fmt.Sprintf("%s-private.key", baseName)
	if err := os.WriteFile(privateFile, privateKey, 0600); err != nil {
		return fmt.Errorf("failed to save private key: %w", err)
	}

	// Save public key
	publicFile := fmt.Sprintf("%s-public.key", baseName)
	if err := os.WriteFile(publicFile, publicKey, 0644); err != nil {
		return fmt.Errorf("failed to save public key: %w", err)
	}

	return nil
}

// signArtifact signs data and returns signature bundle
func signArtifact(privateKey ed25519.PrivateKey, data []byte, metadata map[string]string) *SignatureBundle {
	// Sign data
	signature := ed25519.Sign(privateKey, data)

	// Compute artifact hash
	hash := sha256.Sum256(data)

	return &SignatureBundle{
		Signature:     hex.EncodeToString(signature),
		ArtifactHash:  hex.EncodeToString(hash[:]),
		HashAlgorithm: "SHA-256",
		Algorithm:     "Ed25519",
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
		Metadata:      metadata,
	}
}

// verifyArtifact verifies signature bundle
func verifyArtifact(publicKey ed25519.PublicKey, data []byte, bundle *SignatureBundle) bool {
	// Decode signature
	signature, err := hex.DecodeString(bundle.Signature)
	if err != nil {
		fmt.Printf("Failed to decode signature: %v\n", err)
		return false
	}

	// Verify signature
	if !ed25519.Verify(publicKey, data, signature) {
		return false
	}

	// Verify hash
	hash := sha256.Sum256(data)
	expectedHash := hex.EncodeToString(hash[:])
	if expectedHash != bundle.ArtifactHash {
		fmt.Println("Hash mismatch!")
		return false
	}

	return true
}

// createManifest creates a manifest with multiple signed artifacts
func createManifest(publicKey ed25519.PublicKey, privateKey ed25519.PrivateKey, files map[string][]byte) (*Manifest, error) {
	manifest := &Manifest{
		Version:   "1.0",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Artifacts: make(map[string]SignatureBundle),
		PublicKey: base64.StdEncoding.EncodeToString(publicKey),
	}

	for filename, data := range files {
		metadata := map[string]string{
			"filename": filename,
			"size":     fmt.Sprintf("%d", len(data)),
		}

		bundle := signArtifact(privateKey, data, metadata)
		manifest.Artifacts[filename] = *bundle
	}

	return manifest, nil
}

// verifyManifest verifies all artifacts in manifest
func verifyManifest(manifest *Manifest, files map[string][]byte) map[string]bool {
	// Decode public key
	publicKey, err := base64.StdEncoding.DecodeString(manifest.PublicKey)
	if err != nil {
		fmt.Printf("Failed to decode public key: %v\n", err)
		return nil
	}

	results := make(map[string]bool)

	for filename, bundle := range manifest.Artifacts {
		data, exists := files[filename]
		if !exists {
			fmt.Printf("Warning: %s not found\n", filename)
			results[filename] = false
			continue
		}

		isValid := verifyArtifact(ed25519.PublicKey(publicKey), data, &bundle)
		results[filename] = isValid
	}

	return results
}

func main() {
	fmt.Println("Ed25519 Artifact Signing Example")
	fmt.Println(strings.Repeat("=", 60))

	// 1. Generate key pair
	fmt.Println("\n1. Generating Ed25519 key pair...")
	publicKey, privateKey, err := generateKeyPair()
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}

	if err := saveKeyPair(publicKey, privateKey, "ed25519"); err != nil {
		fmt.Printf("Error saving keys: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("   Keys saved to ed25519-private.key and ed25519-public.key")
	fmt.Printf("   Public key: %s\n", hex.EncodeToString(publicKey)[:32]+"...")

	// 2. Sign single artifact
	fmt.Println("\n2. Signing artifact...")
	artifact := []byte("This is a binary artifact that needs signing.")

	metadata := map[string]string{
		"version": "1.0.0",
		"type":    "binary",
	}

	bundle := signArtifact(privateKey, artifact, metadata)
	fmt.Printf("   Signature: %s...\n", bundle.Signature[:32])
	fmt.Printf("   Hash: %s\n", bundle.ArtifactHash)
	fmt.Printf("   Timestamp: %s\n", bundle.Timestamp)

	// Save signature
	bundleJSON, _ := json.MarshalIndent(bundle, "", "  ")
	if err := os.WriteFile("artifact.sig", bundleJSON, 0644); err != nil {
		fmt.Printf("Error saving signature: %v\n", err)
	}
	fmt.Println("   Signature saved to artifact.sig")

	// 3. Verify signature
	fmt.Println("\n3. Verifying signature...")
	isValid := verifyArtifact(publicKey, artifact, bundle)
	fmt.Printf("   Signature valid: %v\n", isValid)

	// 4. Test with modified artifact
	fmt.Println("\n4. Testing with modified artifact...")
	modifiedArtifact := []byte("This is a MODIFIED artifact.")
	isValid = verifyArtifact(publicKey, modifiedArtifact, bundle)
	fmt.Printf("   Signature valid: %v (expected: false)\n", isValid)

	// 5. Sign multiple artifacts
	fmt.Println("\n5. Signing multiple artifacts...")

	files := map[string][]byte{
		"binary-1": []byte("Binary artifact 1 content"),
		"binary-2": []byte("Binary artifact 2 content"),
		"config":   []byte(`{"setting": "value"}`),
	}

	manifest, err := createManifest(publicKey, privateKey, files)
	if err != nil {
		fmt.Printf("Error creating manifest: %v\n", err)
		os.Exit(1)
	}

	manifestJSON, _ := json.MarshalIndent(manifest, "", "  ")
	if err := os.WriteFile("manifest.json", manifestJSON, 0644); err != nil {
		fmt.Printf("Error saving manifest: %v\n", err)
	}
	fmt.Printf("   Signed %d artifacts\n", len(manifest.Artifacts))
	fmt.Println("   Manifest saved to manifest.json")

	// 6. Verify manifest
	fmt.Println("\n6. Verifying manifest...")
	results := verifyManifest(manifest, files)
	for filename, isValid := range results {
		status := "✓"
		if !isValid {
			status = "✗"
		}
		fmt.Printf("   %s %s\n", status, filename)
	}

	// 7. Performance demonstration
	fmt.Println("\n7. Performance demonstration...")
	fmt.Println("   Signing 1000 artifacts...")

	start := time.Now()
	for i := 0; i < 1000; i++ {
		data := []byte(fmt.Sprintf("Artifact %d", i))
		_ = signArtifact(privateKey, data, nil)
	}
	elapsed := time.Since(start)
	fmt.Printf("   Time: %v\n", elapsed)
	fmt.Printf("   Rate: %.0f signatures/second\n", 1000.0/elapsed.Seconds())

	// 8. Comparison with other algorithms
	fmt.Println("\n8. Ed25519 advantages:")
	fmt.Println("   - Key size: 256 bits (vs RSA-2048: 2048 bits)")
	fmt.Println("   - Signature size: 512 bits (vs RSA-2048: 2048 bits)")
	fmt.Println("   - Speed: ~10-100x faster than RSA/ECDSA")
	fmt.Println("   - Security: ~128-bit security level")
	fmt.Println("   - Deterministic: Same message always produces same signature")

	fmt.Println("\n" + strings.Repeat("=", 60))
	fmt.Println("Production recommendations:")
	fmt.Println("- Use Ed25519 for high-throughput signing")
	fmt.Println("- Store private keys in secure key management systems")
	fmt.Println("- Include timestamps in signatures for audit trails")
	fmt.Println("- Verify signatures before using artifacts")
	fmt.Println("- Consider Ed25519ph for large files (prehashed)")
	fmt.Println("- Implement key rotation policies")
}

// Import strings for Repeat function
import "strings"
