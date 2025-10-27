package main

/*
Disk-Level Encryption in Go

Demonstrates block-level encryption for disk volumes using:
- AES-256-XTS mode (standard for disk encryption)
- Sector-based encryption (512-byte or 4096-byte sectors)
- Key derivation from password (PBKDF2)
- Compatible with dm-crypt/LUKS patterns

Use cases:
- Encrypted file systems
- Virtual disk encryption
- Database volume encryption
*/

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"io"
	"os"

	"golang.org/x/crypto/pbkdf2"
	"golang.org/x/crypto/xts"
)

const (
	// Sector sizes (must match underlying storage)
	SectorSize512  = 512
	SectorSize4096 = 4096

	// Key size for AES-256-XTS (requires 2x 256-bit keys = 64 bytes)
	XTSKeySize = 64

	// PBKDF2 parameters
	PBKDF2Iterations = 100000
	SaltSize         = 32
)

// DiskEncryption handles sector-based disk encryption
type DiskEncryption struct {
	cipher     *xts.Cipher
	sectorSize int
}

// NewDiskEncryption creates a new disk encryption handler
func NewDiskEncryption(key []byte, sectorSize int) (*DiskEncryption, error) {
	if len(key) != XTSKeySize {
		return nil, fmt.Errorf("key must be %d bytes (512 bits)", XTSKeySize)
	}

	if sectorSize != SectorSize512 && sectorSize != SectorSize4096 {
		return nil, fmt.Errorf("sector size must be 512 or 4096 bytes")
	}

	// Create AES-256-XTS cipher
	cipher, err := xts.NewCipher(aes.NewCipher, key)
	if err != nil {
		return nil, fmt.Errorf("failed to create XTS cipher: %w", err)
	}

	return &DiskEncryption{
		cipher:     cipher,
		sectorSize: sectorSize,
	}, nil
}

// DeriveKeyFromPassword derives encryption key from password using PBKDF2
func DeriveKeyFromPassword(password string, salt []byte) []byte {
	return pbkdf2.Key(
		[]byte(password),
		salt,
		PBKDF2Iterations,
		XTSKeySize,
		sha256.New,
	)
}

// EncryptSector encrypts a single disk sector
func (d *DiskEncryption) EncryptSector(plaintext []byte, sectorNum uint64) ([]byte, error) {
	if len(plaintext) != d.sectorSize {
		return nil, fmt.Errorf("plaintext must be exactly %d bytes", d.sectorSize)
	}

	ciphertext := make([]byte, d.sectorSize)
	d.cipher.Encrypt(ciphertext, plaintext, sectorNum)

	return ciphertext, nil
}

// DecryptSector decrypts a single disk sector
func (d *DiskEncryption) DecryptSector(ciphertext []byte, sectorNum uint64) ([]byte, error) {
	if len(ciphertext) != d.sectorSize {
		return nil, fmt.Errorf("ciphertext must be exactly %d bytes", d.sectorSize)
	}

	plaintext := make([]byte, d.sectorSize)
	d.cipher.Decrypt(plaintext, ciphertext, sectorNum)

	return plaintext, nil
}

// EncryptData encrypts data larger than one sector
func (d *DiskEncryption) EncryptData(plaintext []byte) ([]byte, error) {
	// Pad to sector boundary
	paddedLen := ((len(plaintext) + d.sectorSize - 1) / d.sectorSize) * d.sectorSize
	padded := make([]byte, paddedLen)
	copy(padded, plaintext)

	// Store original length in first 8 bytes
	binary.LittleEndian.PutUint64(padded[len(plaintext):], uint64(len(plaintext)))

	// Encrypt sector by sector
	encrypted := make([]byte, len(padded))
	numSectors := len(padded) / d.sectorSize

	for i := 0; i < numSectors; i++ {
		sectorStart := i * d.sectorSize
		sectorEnd := sectorStart + d.sectorSize

		encryptedSector, err := d.EncryptSector(
			padded[sectorStart:sectorEnd],
			uint64(i),
		)
		if err != nil {
			return nil, err
		}

		copy(encrypted[sectorStart:sectorEnd], encryptedSector)
	}

	return encrypted, nil
}

// DecryptData decrypts data larger than one sector
func (d *DiskEncryption) DecryptData(ciphertext []byte) ([]byte, error) {
	if len(ciphertext)%d.sectorSize != 0 {
		return nil, fmt.Errorf("ciphertext length must be multiple of sector size")
	}

	// Decrypt sector by sector
	decrypted := make([]byte, len(ciphertext))
	numSectors := len(ciphertext) / d.sectorSize

	for i := 0; i < numSectors; i++ {
		sectorStart := i * d.sectorSize
		sectorEnd := sectorStart + d.sectorSize

		decryptedSector, err := d.DecryptSector(
			ciphertext[sectorStart:sectorEnd],
			uint64(i),
		)
		if err != nil {
			return nil, err
		}

		copy(decrypted[sectorStart:sectorEnd], decryptedSector)
	}

	return decrypted, nil
}

// EncryptedVolume represents an encrypted disk volume
type EncryptedVolume struct {
	path       string
	encryption *DiskEncryption
	file       *os.File
}

// CreateEncryptedVolume creates a new encrypted volume file
func CreateEncryptedVolume(path string, password string, size int64) (*EncryptedVolume, error) {
	// Generate random salt
	salt := make([]byte, SaltSize)
	if _, err := io.ReadFull(rand.Reader, salt); err != nil {
		return nil, fmt.Errorf("failed to generate salt: %w", err)
	}

	// Derive key from password
	key := DeriveKeyFromPassword(password, salt)

	// Create encryption handler
	encryption, err := NewDiskEncryption(key, SectorSize4096)
	if err != nil {
		return nil, err
	}

	// Create volume file
	file, err := os.Create(path)
	if err != nil {
		return nil, fmt.Errorf("failed to create volume file: %w", err)
	}

	// Write header: magic(8) + version(4) + salt(32)
	header := make([]byte, 512)
	copy(header[0:8], []byte("DISKENC1"))
	binary.LittleEndian.PutUint32(header[8:12], 1) // version
	copy(header[12:12+SaltSize], salt)

	if _, err := file.Write(header); err != nil {
		file.Close()
		return nil, fmt.Errorf("failed to write header: %w", err)
	}

	// Pre-allocate volume
	if err := file.Truncate(size); err != nil {
		file.Close()
		return nil, fmt.Errorf("failed to allocate volume: %w", err)
	}

	return &EncryptedVolume{
		path:       path,
		encryption: encryption,
		file:       file,
	}, nil
}

// OpenEncryptedVolume opens an existing encrypted volume
func OpenEncryptedVolume(path string, password string) (*EncryptedVolume, error) {
	file, err := os.OpenFile(path, os.O_RDWR, 0600)
	if err != nil {
		return nil, fmt.Errorf("failed to open volume: %w", err)
	}

	// Read header
	header := make([]byte, 512)
	if _, err := file.Read(header); err != nil {
		file.Close()
		return nil, fmt.Errorf("failed to read header: %w", err)
	}

	// Verify magic
	magic := string(header[0:8])
	if magic != "DISKENC1" {
		file.Close()
		return nil, fmt.Errorf("invalid volume format")
	}

	// Extract salt
	salt := header[12 : 12+SaltSize]

	// Derive key from password
	key := DeriveKeyFromPassword(password, salt)

	// Create encryption handler
	encryption, err := NewDiskEncryption(key, SectorSize4096)
	if err != nil {
		file.Close()
		return nil, err
	}

	return &EncryptedVolume{
		path:       path,
		encryption: encryption,
		file:       file,
	}, nil
}

// WriteSector writes encrypted data to a specific sector
func (v *EncryptedVolume) WriteSector(sectorNum uint64, data []byte) error {
	encrypted, err := v.encryption.EncryptSector(data, sectorNum)
	if err != nil {
		return err
	}

	// Skip header (512 bytes) + seek to sector
	offset := int64(512 + sectorNum*uint64(v.encryption.sectorSize))
	if _, err := v.file.Seek(offset, 0); err != nil {
		return err
	}

	if _, err := v.file.Write(encrypted); err != nil {
		return err
	}

	return v.file.Sync()
}

// ReadSector reads and decrypts a specific sector
func (v *EncryptedVolume) ReadSector(sectorNum uint64) ([]byte, error) {
	// Skip header + seek to sector
	offset := int64(512 + sectorNum*uint64(v.encryption.sectorSize))
	if _, err := v.file.Seek(offset, 0); err != nil {
		return nil, err
	}

	encrypted := make([]byte, v.encryption.sectorSize)
	if _, err := io.ReadFull(v.file, encrypted); err != nil {
		return nil, err
	}

	return v.encryption.DecryptSector(encrypted, sectorNum)
}

// Close closes the encrypted volume
func (v *EncryptedVolume) Close() error {
	return v.file.Close()
}

// Example 1: Basic sector encryption
func exampleBasicSectorEncryption() {
	fmt.Println("=== Basic Sector Encryption ===")

	// Generate key (in production, derive from password or use KMS)
	key := make([]byte, XTSKeySize)
	if _, err := io.ReadFull(rand.Reader, key); err != nil {
		panic(err)
	}

	// Create disk encryption handler
	encryption, err := NewDiskEncryption(key, SectorSize512)
	if err != nil {
		panic(err)
	}

	// Prepare data (must be exactly 512 bytes)
	plaintext := make([]byte, SectorSize512)
	copy(plaintext, []byte("Sensitive data in sector 0"))

	// Encrypt sector
	ciphertext, err := encryption.EncryptSector(plaintext, 0)
	if err != nil {
		panic(err)
	}

	fmt.Printf("✓ Encrypted sector 0\n")
	fmt.Printf("  Plaintext (first 50 bytes): %s\n", plaintext[:50])
	fmt.Printf("  Ciphertext (first 50 bytes): %x...\n", ciphertext[:50])

	// Decrypt sector
	decrypted, err := encryption.DecryptSector(ciphertext, 0)
	if err != nil {
		panic(err)
	}

	fmt.Printf("✓ Decrypted sector 0\n")

	// Verify
	if string(decrypted[:50]) != string(plaintext[:50]) {
		panic("decryption verification failed")
	}
	fmt.Println("✓ Verification passed")
}

// Example 2: Password-based encryption
func examplePasswordEncryption() {
	fmt.Println("\n=== Password-Based Encryption ===")

	password := "SecurePassword123!"
	salt := make([]byte, SaltSize)
	if _, err := io.ReadFull(rand.Reader, salt); err != nil {
		panic(err)
	}

	// Derive key from password
	key := DeriveKeyFromPassword(password, salt)
	fmt.Printf("✓ Derived key from password (PBKDF2, %d iterations)\n", PBKDF2Iterations)

	// Create encryption
	encryption, err := NewDiskEncryption(key, SectorSize4096)
	if err != nil {
		panic(err)
	}

	// Encrypt data
	data := []byte("Protected financial records")
	padded := make([]byte, SectorSize4096)
	copy(padded, data)

	encrypted, err := encryption.EncryptSector(padded, 0)
	if err != nil {
		panic(err)
	}

	fmt.Println("✓ Encrypted with password-derived key")

	// Later: decrypt with same password + salt
	derivedKey := DeriveKeyFromPassword(password, salt)
	decryption, err := NewDiskEncryption(derivedKey, SectorSize4096)
	if err != nil {
		panic(err)
	}

	decrypted, err := decryption.DecryptSector(encrypted, 0)
	if err != nil {
		panic(err)
	}

	fmt.Printf("✓ Decrypted: %s\n", string(decrypted[:len(data)]))
}

// Example 3: Encrypted volume
func exampleEncryptedVolume() {
	fmt.Println("\n=== Encrypted Volume ===")

	volumePath := "/tmp/encrypted_volume.dat"
	password := "VolumePassword456"

	// Create volume (1 MB)
	volume, err := CreateEncryptedVolume(volumePath, password, 1024*1024)
	if err != nil {
		panic(err)
	}
	defer os.Remove(volumePath)

	fmt.Println("✓ Created encrypted volume (1 MB)")

	// Write data to sectors
	for i := uint64(0); i < 10; i++ {
		data := make([]byte, SectorSize4096)
		copy(data, []byte(fmt.Sprintf("Data in sector %d", i)))

		if err := volume.WriteSector(i, data); err != nil {
			panic(err)
		}
	}

	fmt.Println("✓ Wrote 10 encrypted sectors")
	volume.Close()

	// Reopen volume
	volume, err = OpenEncryptedVolume(volumePath, password)
	if err != nil {
		panic(err)
	}
	defer volume.Close()

	fmt.Println("✓ Reopened encrypted volume")

	// Read back data
	for i := uint64(0); i < 10; i++ {
		data, err := volume.ReadSector(i)
		if err != nil {
			panic(err)
		}

		fmt.Printf("  Sector %d: %s\n", i, string(data[:50]))
	}

	fmt.Println("✓ Read all encrypted sectors")
}

func main() {
	fmt.Println("Disk-Level Encryption Examples (Go)")
	fmt.Println("=" + string(make([]byte, 60)))
	fmt.Println()
	fmt.Println("Requirements:")
	fmt.Println("  go get golang.org/x/crypto/xts")
	fmt.Println("  go get golang.org/x/crypto/pbkdf2")
	fmt.Println()
	fmt.Println("=" + string(make([]byte, 60)))
	fmt.Println()

	exampleBasicSectorEncryption()
	examplePasswordEncryption()
	exampleEncryptedVolume()

	fmt.Println("\n=== All Examples Completed ===")
	fmt.Println("\nBest Practices:")
	fmt.Println("  • Use AES-256-XTS for disk encryption (IEEE P1619 standard)")
	fmt.Println("  • Derive keys with PBKDF2 (100,000+ iterations)")
	fmt.Println("  • Use unique sector numbers as tweaks (prevents block reordering)")
	fmt.Println("  • Match sector size to underlying storage (512 or 4096 bytes)")
	fmt.Println("  • Store salt securely (volume header or separate file)")
}
