//! JWT authentication and validation

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use hmac::{Hmac, Mac};
use sha2::Sha256;
use base64::{Engine as _, engine::general_purpose};

type HmacSha256 = Hmac<Sha256>;

#[pyfunction]
fn sign_token(payload: String, secret: String) -> PyResult<String> {
    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| PyValueError::new_err(format!("Invalid key: {}", e)))?;

    mac.update(payload.as_bytes());
    let signature = mac.finalize().into_bytes();

    Ok(general_purpose::URL_SAFE_NO_PAD.encode(signature))
}

#[pyfunction]
fn verify_token(payload: String, signature: String, secret: String) -> PyResult<bool> {
    let mut mac = HmacSha256::new_from_slice(secret.as_bytes())
        .map_err(|e| PyValueError::new_err(format!("Invalid key: {}", e)))?;

    mac.update(payload.as_bytes());

    let sig_bytes = general_purpose::URL_SAFE_NO_PAD.decode(signature)
        .map_err(|e| PyValueError::new_err(format!("Invalid signature: {}", e)))?;

    Ok(mac.verify_slice(&sig_bytes).is_ok())
}

#[pyfunction]
fn hash_password(password: String) -> PyResult<String> {
    use argon2::{Argon2, PasswordHasher};
    use argon2::password_hash::SaltString;

    let salt = SaltString::generate(&mut rand::thread_rng());
    let argon2 = Argon2::default();

    argon2.hash_password(password.as_bytes(), &salt)
        .map(|hash| hash.to_string())
        .map_err(|e| PyRuntimeError::new_err(format!("Hash failed: {}", e)))
}

#[pyfunction]
fn verify_password(password: String, hash: String) -> PyResult<bool> {
    use argon2::{Argon2, PasswordVerifier, PasswordHash};

    let parsed_hash = PasswordHash::new(&hash)
        .map_err(|e| PyValueError::new_err(format!("Invalid hash: {}", e)))?;

    Ok(Argon2::default()
        .verify_password(password.as_bytes(), &parsed_hash)
        .is_ok())
}

#[pymodule]
fn jwt_auth(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sign_token, m)?)?;
    m.add_function(wrap_pyfunction!(verify_token, m)?)?;
    m.add_function(wrap_pyfunction!(hash_password, m)?)?;
    m.add_function(wrap_pyfunction!(verify_password, m)?)?;
    Ok(())
}
