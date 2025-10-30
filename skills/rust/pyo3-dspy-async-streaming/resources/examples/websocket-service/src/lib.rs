//! WebSocket Service Library
//!
//! Provides WebSocket connection management, message protocol, and DSPy integration
//! for real-time AI streaming.

use anyhow::{Context, Result};
use axum::extract::ws::{Message, WebSocket};
use futures::{SinkExt, StreamExt};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{broadcast, mpsc, RwLock};
use tracing::{debug, error, info, warn};
use uuid::Uuid;

/// Maximum message size (1 MB)
pub const MAX_MESSAGE_SIZE: usize = 1024 * 1024;

/// Ping interval for keeping connections alive
pub const PING_INTERVAL_SECS: u64 = 30;

/// Connection idle timeout
pub const IDLE_TIMEOUT_SECS: u64 = 300;

/// Client message types
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum ClientMessage {
    /// Query request with optional streaming
    Query {
        session_id: String,
        query: String,
        #[serde(default = "default_stream")]
        stream: bool,
        #[serde(default)]
        model: Option<String>,
        #[serde(default)]
        temperature: Option<f32>,
    },
    /// Ping to keep connection alive
    Ping,
    /// Request connection info
    Info,
}

fn default_stream() -> bool {
    true
}

/// Server message types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "lowercase")]
pub enum ServerMessage {
    /// Streaming token
    Token {
        session_id: String,
        token: String,
        index: usize,
    },
    /// Stream end marker
    End {
        session_id: String,
        total_tokens: usize,
        duration_ms: u64,
    },
    /// Error response
    Error {
        session_id: Option<String>,
        error: String,
        code: ErrorCode,
    },
    /// Pong response to ping
    Pong {
        timestamp: chrono::DateTime<chrono::Utc>,
    },
    /// Connection info
    Info {
        connection_id: String,
        connected_at: chrono::DateTime<chrono::Utc>,
        active_sessions: usize,
    },
}

/// Error codes for structured error handling
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ErrorCode {
    PythonError,
    ParseError,
    InvalidMessage,
    SessionNotFound,
    InternalError,
    RateLimited,
}

/// Connection information
#[derive(Debug, Clone)]
pub struct Connection {
    pub id: String,
    pub connected_at: chrono::DateTime<chrono::Utc>,
    pub tx: mpsc::UnboundedSender<ServerMessage>,
}

/// Active session information
#[derive(Debug, Clone)]
pub struct Session {
    pub id: String,
    pub query: String,
    pub started_at: chrono::DateTime<chrono::Utc>,
    pub connection_id: String,
}

/// Connection manager for tracking active connections and sessions
#[derive(Clone)]
pub struct ConnectionManager {
    connections: Arc<RwLock<HashMap<String, Connection>>>,
    sessions: Arc<RwLock<HashMap<String, Session>>>,
    broadcast_tx: broadcast::Sender<ServerMessage>,
}

impl ConnectionManager {
    /// Create a new connection manager
    pub fn new() -> Self {
        let (broadcast_tx, _) = broadcast::channel(100);
        Self {
            connections: Arc::new(RwLock::new(HashMap::new())),
            sessions: Arc::new(RwLock::new(HashMap::new())),
            broadcast_tx,
        }
    }

    /// Register a new connection
    pub async fn register_connection(
        &self,
        connection_id: String,
        tx: mpsc::UnboundedSender<ServerMessage>,
    ) {
        let connection = Connection {
            id: connection_id.clone(),
            connected_at: chrono::Utc::now(),
            tx,
        };
        let mut connections = self.connections.write().await;
        connections.insert(connection_id.clone(), connection);
        info!("Connection registered: {}", connection_id);
    }

    /// Unregister a connection
    pub async fn unregister_connection(&self, connection_id: &str) {
        let mut connections = self.connections.write().await;
        connections.remove(connection_id);

        // Clean up any sessions associated with this connection
        let mut sessions = self.sessions.write().await;
        sessions.retain(|_, session| session.connection_id != connection_id);

        info!("Connection unregistered: {}", connection_id);
    }

    /// Start a new session
    pub async fn start_session(&self, session_id: String, query: String, connection_id: String) {
        let session = Session {
            id: session_id.clone(),
            query,
            started_at: chrono::Utc::now(),
            connection_id,
        };
        let mut sessions = self.sessions.write().await;
        sessions.insert(session_id.clone(), session);
        debug!("Session started: {}", session_id);
    }

    /// End a session
    pub async fn end_session(&self, session_id: &str) {
        let mut sessions = self.sessions.write().await;
        sessions.remove(session_id);
        debug!("Session ended: {}", session_id);
    }

    /// Send message to a specific connection
    pub async fn send_to_connection(
        &self,
        connection_id: &str,
        message: ServerMessage,
    ) -> Result<()> {
        let connections = self.connections.read().await;
        if let Some(connection) = connections.get(connection_id) {
            connection
                .tx
                .send(message)
                .context("Failed to send message to connection")?;
            Ok(())
        } else {
            Err(anyhow::anyhow!("Connection not found: {}", connection_id))
        }
    }

    /// Broadcast message to all connections
    pub fn broadcast(&self, message: ServerMessage) -> Result<()> {
        self.broadcast_tx
            .send(message)
            .context("Failed to broadcast message")?;
        Ok(())
    }

    /// Get connection count
    pub async fn connection_count(&self) -> usize {
        let connections = self.connections.read().await;
        connections.len()
    }

    /// Get active session count
    pub async fn session_count(&self) -> usize {
        let sessions = self.sessions.read().await;
        sessions.len()
    }

    /// Get connection info
    pub async fn get_connection_info(&self, connection_id: &str) -> Option<Connection> {
        let connections = self.connections.read().await;
        connections.get(connection_id).cloned()
    }

    /// Subscribe to broadcast messages
    pub fn subscribe(&self) -> broadcast::Receiver<ServerMessage> {
        self.broadcast_tx.subscribe()
    }
}

impl Default for ConnectionManager {
    fn default() -> Self {
        Self::new()
    }
}

/// WebSocket handler for managing individual connections
pub struct WebSocketHandler {
    connection_id: String,
    manager: ConnectionManager,
    tx: mpsc::UnboundedSender<ServerMessage>,
    rx: mpsc::UnboundedReceiver<ServerMessage>,
}

impl WebSocketHandler {
    /// Create a new WebSocket handler
    pub fn new(manager: ConnectionManager) -> Self {
        let connection_id = Uuid::new_v4().to_string();
        let (tx, rx) = mpsc::unbounded_channel();

        Self {
            connection_id,
            manager,
            tx,
            rx,
        }
    }

    /// Handle WebSocket connection
    pub async fn handle(mut self, socket: WebSocket) {
        info!("WebSocket connection established: {}", self.connection_id);

        // Register connection
        self.manager
            .register_connection(self.connection_id.clone(), self.tx.clone())
            .await;

        // Subscribe to broadcasts
        let mut broadcast_rx = self.manager.subscribe();

        // Split socket into sender and receiver
        let (mut ws_tx, mut ws_rx) = socket.split();

        // Send initial connection message
        let connect_msg = ServerMessage::Info {
            connection_id: self.connection_id.clone(),
            connected_at: chrono::Utc::now(),
            active_sessions: 0,
        };
        if let Ok(text) = serde_json::to_string(&connect_msg) {
            let _ = ws_tx.send(Message::Text(text)).await;
        }

        // Message processing loop
        loop {
            tokio::select! {
                // Handle incoming WebSocket messages
                Some(result) = ws_rx.next() => {
                    match result {
                        Ok(msg) => {
                            if let Err(e) = self.handle_client_message(msg).await {
                                error!("Error handling client message: {}", e);
                                let error_msg = ServerMessage::Error {
                                    session_id: None,
                                    error: e.to_string(),
                                    code: ErrorCode::InternalError,
                                };
                                if let Ok(text) = serde_json::to_string(&error_msg) {
                                    let _ = ws_tx.send(Message::Text(text)).await;
                                }
                            }
                        }
                        Err(e) => {
                            error!("WebSocket error: {}", e);
                            break;
                        }
                    }
                }
                // Handle outgoing messages to this connection
                Some(msg) = self.rx.recv() => {
                    if let Ok(text) = serde_json::to_string(&msg) {
                        if let Err(e) = ws_tx.send(Message::Text(text)).await {
                            error!("Failed to send message: {}", e);
                            break;
                        }
                    }
                }
                // Handle broadcast messages
                Ok(msg) = broadcast_rx.recv() => {
                    if let Ok(text) = serde_json::to_string(&msg) {
                        let _ = ws_tx.send(Message::Text(text)).await;
                    }
                }
                // Connection idle timeout
                _ = tokio::time::sleep(tokio::time::Duration::from_secs(IDLE_TIMEOUT_SECS)) => {
                    warn!("Connection idle timeout: {}", self.connection_id);
                    break;
                }
            }
        }

        // Clean up
        self.manager.unregister_connection(&self.connection_id).await;
        info!("WebSocket connection closed: {}", self.connection_id);
    }

    /// Handle individual client message
    async fn handle_client_message(&mut self, message: Message) -> Result<()> {
        match message {
            Message::Text(text) => {
                debug!("Received text message: {}", text);
                let client_msg: ClientMessage = serde_json::from_str(&text)
                    .context("Failed to parse client message")?;
                self.process_client_message(client_msg).await?;
            }
            Message::Binary(data) => {
                debug!("Received binary message: {} bytes", data.len());
                let client_msg: ClientMessage = serde_json::from_slice(&data)
                    .context("Failed to parse binary message")?;
                self.process_client_message(client_msg).await?;
            }
            Message::Ping(_) => {
                debug!("Received ping");
            }
            Message::Pong(_) => {
                debug!("Received pong");
            }
            Message::Close(_) => {
                info!("Received close frame");
            }
        }
        Ok(())
    }

    /// Process parsed client message
    async fn process_client_message(&mut self, message: ClientMessage) -> Result<()> {
        match message {
            ClientMessage::Query {
                session_id,
                query,
                stream,
                model,
                temperature,
            } => {
                info!(
                    "Processing query - session: {}, stream: {}, query: {}",
                    session_id, stream, query
                );

                // Start session
                self.manager
                    .start_session(session_id.clone(), query.clone(), self.connection_id.clone())
                    .await;

                // Process query
                if stream {
                    self.process_streaming_query(session_id, query, model, temperature)
                        .await?;
                } else {
                    self.process_blocking_query(session_id, query, model, temperature)
                        .await?;
                }
            }
            ClientMessage::Ping => {
                debug!("Processing ping");
                let pong = ServerMessage::Pong {
                    timestamp: chrono::Utc::now(),
                };
                self.tx.send(pong).context("Failed to send pong")?;
            }
            ClientMessage::Info => {
                debug!("Processing info request");
                let info = ServerMessage::Info {
                    connection_id: self.connection_id.clone(),
                    connected_at: chrono::Utc::now(),
                    active_sessions: self.manager.session_count().await,
                };
                self.tx.send(info).context("Failed to send info")?;
            }
        }
        Ok(())
    }

    /// Process streaming query with token-by-token updates
    async fn process_streaming_query(
        &mut self,
        session_id: String,
        query: String,
        model: Option<String>,
        temperature: Option<f32>,
    ) -> Result<()> {
        let start_time = std::time::Instant::now();
        let tx = self.tx.clone();
        let manager = self.manager.clone();
        let session_id_clone = session_id.clone();

        // Spawn Python task
        tokio::task::spawn_blocking(move || {
            let result: Result<()> = Python::with_gil(|py| {
                // Mock streaming implementation
                // In production, integrate with actual DSPy streaming
                let tokens = vec![
                    "Hello", " there", "!", " I", " am", " a", " streaming", " response", " from",
                    " DSPy", ".", " This", " demonstrates", " real", "-time", " token", " delivery",
                    " over", " WebSocket", ".",
                ];

                for (index, token) in tokens.iter().enumerate() {
                    let msg = ServerMessage::Token {
                        session_id: session_id.clone(),
                        token: token.to_string(),
                        index,
                    };

                    if let Err(e) = tx.send(msg) {
                        error!("Failed to send token: {}", e);
                        return Err(anyhow::anyhow!("Failed to send token: {}", e));
                    }

                    // Simulate processing time
                    std::thread::sleep(std::time::Duration::from_millis(50));
                }

                Ok(())
            });

            // Send end message
            let duration = start_time.elapsed();
            let end_msg = ServerMessage::End {
                session_id: session_id_clone.clone(),
                total_tokens: 20,
                duration_ms: duration.as_millis() as u64,
            };
            let _ = tx.send(end_msg);

            // End session
            tokio::runtime::Handle::current().block_on(async {
                manager.end_session(&session_id_clone).await;
            });

            result
        })
        .await
        .context("Failed to spawn Python task")??;

        Ok(())
    }

    /// Process blocking query with complete response
    async fn process_blocking_query(
        &mut self,
        session_id: String,
        query: String,
        model: Option<String>,
        temperature: Option<f32>,
    ) -> Result<()> {
        let start_time = std::time::Instant::now();
        let tx = self.tx.clone();
        let manager = self.manager.clone();
        let session_id_clone = session_id.clone();

        // Spawn Python task
        tokio::task::spawn_blocking(move || {
            let result: Result<String> = Python::with_gil(|py| {
                // Mock blocking implementation
                // In production, integrate with actual DSPy
                std::thread::sleep(std::time::Duration::from_millis(500));
                Ok("This is a complete response from DSPy.".to_string())
            });

            match result {
                Ok(response) => {
                    // Send as single token
                    let msg = ServerMessage::Token {
                        session_id: session_id.clone(),
                        token: response,
                        index: 0,
                    };
                    let _ = tx.send(msg);

                    // Send end message
                    let duration = start_time.elapsed();
                    let end_msg = ServerMessage::End {
                        session_id: session_id_clone.clone(),
                        total_tokens: 1,
                        duration_ms: duration.as_millis() as u64,
                    };
                    let _ = tx.send(end_msg);
                }
                Err(e) => {
                    let error_msg = ServerMessage::Error {
                        session_id: Some(session_id_clone.clone()),
                        error: e.to_string(),
                        code: ErrorCode::PythonError,
                    };
                    let _ = tx.send(error_msg);
                }
            }

            // End session
            tokio::runtime::Handle::current().block_on(async {
                manager.end_session(&session_id_clone).await;
            });
        })
        .await
        .context("Failed to spawn Python task")?;

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_connection_manager() {
        let manager = ConnectionManager::new();
        let (tx, _rx) = mpsc::unbounded_channel();

        // Register connection
        manager.register_connection("conn-1".to_string(), tx).await;
        assert_eq!(manager.connection_count().await, 1);

        // Start session
        manager
            .start_session("session-1".to_string(), "test query".to_string(), "conn-1".to_string())
            .await;
        assert_eq!(manager.session_count().await, 1);

        // End session
        manager.end_session("session-1").await;
        assert_eq!(manager.session_count().await, 0);

        // Unregister connection
        manager.unregister_connection("conn-1").await;
        assert_eq!(manager.connection_count().await, 0);
    }

    #[test]
    fn test_message_serialization() {
        let msg = ServerMessage::Token {
            session_id: "test".to_string(),
            token: "hello".to_string(),
            index: 0,
        };

        let json = serde_json::to_string(&msg).unwrap();
        let parsed: ServerMessage = serde_json::from_str(&json).unwrap();

        match parsed {
            ServerMessage::Token { session_id, token, index } => {
                assert_eq!(session_id, "test");
                assert_eq!(token, "hello");
                assert_eq!(index, 0);
            }
            _ => panic!("Wrong message type"),
        }
    }

    #[test]
    fn test_client_message_parsing() {
        let json = r#"{"type":"query","session_id":"123","query":"test","stream":true}"#;
        let msg: ClientMessage = serde_json::from_str(json).unwrap();

        match msg {
            ClientMessage::Query { session_id, query, stream, .. } => {
                assert_eq!(session_id, "123");
                assert_eq!(query, "test");
                assert_eq!(stream, true);
            }
            _ => panic!("Wrong message type"),
        }
    }
}
