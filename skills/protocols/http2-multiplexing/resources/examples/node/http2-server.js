/**
 * Node.js HTTP/2 Server Examples
 *
 * Complete examples demonstrating HTTP/2 features:
 * - Server push
 * - Stream prioritization
 * - Flow control
 * - Multiplexing
 */

const http2 = require('http2');
const fs = require('fs');
const path = require('path');

// ============================================================================
// Example 1: Basic HTTP/2 Server
// ============================================================================

function basicServer() {
    const server = http2.createSecureServer({
        key: fs.readFileSync('server-key.pem'),
        cert: fs.readFileSync('server-cert.pem')
    });

    server.on('stream', (stream, headers) => {
        const path = headers[':path'];

        console.log(`Request: ${headers[':method']} ${path}`);

        stream.respond({
            ':status': 200,
            'content-type': 'text/html'
        });

        stream.end('<html><body><h1>HTTP/2 Server</h1></body></html>');
    });

    server.listen(8443, () => {
        console.log('HTTP/2 server running on https://localhost:8443');
    });
}

// ============================================================================
// Example 2: Server Push
// ============================================================================

function serverWithPush() {
    const server = http2.createSecureServer({
        key: fs.readFileSync('server-key.pem'),
        cert: fs.readFileSync('server-cert.pem')
    });

    server.on('stream', (stream, headers) => {
        const requestPath = headers[':path'];

        if (requestPath === '/') {
            // Push CSS before sending HTML
            stream.pushStream({ ':path': '/style.css' }, (err, pushStream, headers) => {
                if (err) {
                    console.error('Push error:', err);
                    return;
                }

                console.log('Pushing /style.css');

                pushStream.respond({
                    ':status': 200,
                    'content-type': 'text/css',
                    'cache-control': 'public, max-age=31536000'
                });

                pushStream.end('body { font-family: sans-serif; color: #333; }');
            });

            // Push JavaScript
            stream.pushStream({ ':path': '/app.js' }, (err, pushStream, headers) => {
                if (err) {
                    console.error('Push error:', err);
                    return;
                }

                console.log('Pushing /app.js');

                pushStream.respond({
                    ':status': 200,
                    'content-type': 'application/javascript',
                    'cache-control': 'public, max-age=31536000'
                });

                pushStream.end('console.log("App loaded via server push");');
            });

            // Send HTML
            stream.respond({
                ':status': 200,
                'content-type': 'text/html'
            });

            stream.end(`
                <!DOCTYPE html>
                <html>
                <head>
                    <link rel="stylesheet" href="/style.css">
                    <script src="/app.js"></script>
                </head>
                <body>
                    <h1>HTTP/2 Server Push Demo</h1>
                    <p>CSS and JS were pushed by the server!</p>
                </body>
                </html>
            `);
        } else {
            // Regular request (client requested directly, or push was rejected)
            stream.respond({ ':status': 404 });
            stream.end('Not found');
        }
    });

    server.listen(8443, () => {
        console.log('HTTP/2 server with push on https://localhost:8443');
    });
}

// ============================================================================
// Example 3: Conditional Server Push (Cookie-based)
// ============================================================================

function serverWithConditionalPush() {
    const server = http2.createSecureServer({
        key: fs.readFileSync('server-key.pem'),
        cert: fs.readFileSync('server-cert.pem')
    });

    server.on('stream', (stream, headers) => {
        const requestPath = headers[':path'];
        const cookie = headers['cookie'] || '';

        if (requestPath === '/') {
            // Only push if client doesn't have cached assets
            const hasAssets = cookie.includes('has_assets=1');

            if (!hasAssets) {
                console.log('Client cache miss - pushing assets');

                stream.pushStream({ ':path': '/style.css' }, (err, pushStream) => {
                    if (!err) {
                        pushStream.respond({
                            ':status': 200,
                            'content-type': 'text/css',
                            'cache-control': 'public, max-age=31536000'
                        });
                        pushStream.end('body { background: #f0f0f0; }');
                    }
                });
            } else {
                console.log('Client has cached assets - skipping push');
            }

            // Send HTML with cookie
            stream.respond({
                ':status': 200,
                'content-type': 'text/html',
                'set-cookie': 'has_assets=1; Max-Age=31536000; Path=/'
            });

            stream.end('<html><body><h1>Conditional Push</h1></body></html>');
        }
    });

    server.listen(8443);
}

// ============================================================================
// Example 4: Stream Prioritization
// ============================================================================

function serverWithPrioritization() {
    const server = http2.createSecureServer({
        key: fs.readFileSync('server-key.pem'),
        cert: fs.readFileSync('server-cert.pem')
    });

    server.on('stream', (stream, headers) => {
        const requestPath = headers[':path'];

        // Set priority based on resource type
        if (requestPath.endsWith('.css')) {
            // High priority for CSS (critical rendering path)
            stream.priority({
                parent: 0,
                weight: 256,
                exclusive: false
            });
        } else if (requestPath.endsWith('.js')) {
            // Medium priority for JavaScript
            stream.priority({
                parent: 0,
                weight: 128,
                exclusive: false
            });
        } else if (requestPath.match(/\.(jpg|png|gif)$/)) {
            // Low priority for images
            stream.priority({
                parent: 0,
                weight: 64,
                exclusive: false
            });
        }

        stream.respond({ ':status': 200 });
        stream.end(`Content for ${requestPath}`);
    });

    server.listen(8443);
}

// ============================================================================
// Example 5: Flow Control
// ============================================================================

function serverWithFlowControl() {
    const server = http2.createSecureServer({
        key: fs.readFileSync('server-key.pem'),
        cert: fs.readFileSync('server-cert.pem')
    });

    server.on('stream', (stream, headers) => {
        stream.respond({ ':status': 200 });

        // Send large payload respecting flow control
        const largeData = Buffer.alloc(1024 * 1024 * 10); // 10MB

        let offset = 0;
        const chunkSize = 16384; // 16KB chunks

        function sendChunk() {
            if (offset >= largeData.length) {
                stream.end();
                return;
            }

            // Check if stream is still writable
            if (stream.destroyed) {
                return;
            }

            const chunk = largeData.slice(offset, offset + chunkSize);
            const canContinue = stream.write(chunk);

            offset += chunkSize;

            if (canContinue) {
                // Stream buffer not full, send next chunk
                setImmediate(sendChunk);
            } else {
                // Wait for drain event
                stream.once('drain', sendChunk);
            }
        }

        sendChunk();
    });

    server.listen(8443);
}

// ============================================================================
// Example 6: HTTP/2 Client (Multiplexing Demo)
// ============================================================================

function http2Client() {
    const client = http2.connect('https://localhost:8443', {
        rejectUnauthorized: false // For self-signed certs
    });

    client.on('error', (err) => console.error('Client error:', err));

    // Make multiple concurrent requests on single connection
    const paths = ['/page1', '/page2', '/page3', '/page4', '/page5'];

    paths.forEach((path) => {
        const req = client.request({
            ':path': path,
            ':method': 'GET'
        });

        req.on('response', (headers) => {
            console.log(`Response for ${path}: ${headers[':status']}`);
        });

        let data = '';
        req.on('data', (chunk) => {
            data += chunk;
        });

        req.on('end', () => {
            console.log(`${path} complete (${data.length} bytes)`);
        });

        req.end();
    });

    // Close after all requests complete
    setTimeout(() => client.close(), 5000);
}

// ============================================================================
// Example 7: API Server with JSON
// ============================================================================

function apiServer() {
    const server = http2.createSecureServer({
        key: fs.readFileSync('server-key.pem'),
        cert: fs.readFileSync('server-cert.pem')
    });

    server.on('stream', (stream, headers) => {
        const method = headers[':method'];
        const path = headers[':path'];

        console.log(`${method} ${path}`);

        // CORS headers
        const responseHeaders = {
            'access-control-allow-origin': '*',
            'access-control-allow-methods': 'GET, POST, PUT, DELETE',
            'access-control-allow-headers': 'Content-Type, Authorization'
        };

        if (method === 'OPTIONS') {
            stream.respond({
                ':status': 204,
                ...responseHeaders
            });
            stream.end();
            return;
        }

        // API routes
        if (path === '/api/users' && method === 'GET') {
            stream.respond({
                ':status': 200,
                'content-type': 'application/json',
                ...responseHeaders
            });

            stream.end(JSON.stringify({
                users: [
                    { id: 1, name: 'Alice' },
                    { id: 2, name: 'Bob' }
                ]
            }));
        } else if (path.startsWith('/api/users/') && method === 'GET') {
            const userId = path.split('/').pop();

            stream.respond({
                ':status': 200,
                'content-type': 'application/json',
                ...responseHeaders
            });

            stream.end(JSON.stringify({
                id: userId,
                name: `User ${userId}`
            }));
        } else {
            stream.respond({
                ':status': 404,
                'content-type': 'application/json',
                ...responseHeaders
            });

            stream.end(JSON.stringify({ error: 'Not found' }));
        }
    });

    server.listen(8443, () => {
        console.log('HTTP/2 API server on https://localhost:8443');
    });
}

// ============================================================================
// Example 8: File Server with Server Push
// ============================================================================

function fileServer() {
    const server = http2.createSecureServer({
        key: fs.readFileSync('server-key.pem'),
        cert: fs.readFileSync('server-cert.pem')
    });

    const publicDir = path.join(__dirname, 'public');

    server.on('stream', (stream, headers) => {
        const requestPath = headers[':path'];
        const filePath = path.join(publicDir, requestPath === '/' ? 'index.html' : requestPath);

        // Security: prevent directory traversal
        if (!filePath.startsWith(publicDir)) {
            stream.respond({ ':status': 403 });
            stream.end('Forbidden');
            return;
        }

        // Push related resources for HTML files
        if (filePath.endsWith('index.html')) {
            // Parse HTML and push linked resources
            const resources = ['/css/main.css', '/js/app.js'];

            resources.forEach((resource) => {
                stream.pushStream({ ':path': resource }, (err, pushStream) => {
                    if (err) return;

                    const resourcePath = path.join(publicDir, resource);
                    const ext = path.extname(resource);
                    const contentType = {
                        '.css': 'text/css',
                        '.js': 'application/javascript',
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg'
                    }[ext] || 'application/octet-stream';

                    fs.readFile(resourcePath, (err, data) => {
                        if (err) {
                            pushStream.respond({ ':status': 404 });
                            pushStream.end();
                        } else {
                            pushStream.respond({
                                ':status': 200,
                                'content-type': contentType,
                                'cache-control': 'public, max-age=31536000'
                            });
                            pushStream.end(data);
                        }
                    });
                });
            });
        }

        // Send requested file
        fs.readFile(filePath, (err, data) => {
            if (err) {
                stream.respond({ ':status': 404 });
                stream.end('Not found');
            } else {
                const ext = path.extname(filePath);
                const contentType = {
                    '.html': 'text/html',
                    '.css': 'text/css',
                    '.js': 'application/javascript',
                    '.json': 'application/json',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg'
                }[ext] || 'application/octet-stream';

                stream.respond({
                    ':status': 200,
                    'content-type': contentType
                });
                stream.end(data);
            }
        });
    });

    server.listen(8443, () => {
        console.log('HTTP/2 file server on https://localhost:8443');
    });
}

// ============================================================================
// Run Examples
// ============================================================================

// Uncomment to run different examples:

// basicServer();
// serverWithPush();
// serverWithConditionalPush();
// serverWithPrioritization();
// serverWithFlowControl();
// apiServer();
// fileServer();

// To run client:
// http2Client();

// Export for use as module
module.exports = {
    basicServer,
    serverWithPush,
    serverWithConditionalPush,
    serverWithPrioritization,
    serverWithFlowControl,
    http2Client,
    apiServer,
    fileServer
};
