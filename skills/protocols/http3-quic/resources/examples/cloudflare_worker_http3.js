/**
 * Cloudflare Workers HTTP/3 Example
 *
 * Cloudflare Workers automatically support HTTP/3 at the edge.
 * This example demonstrates HTTP/3 features and optimizations.
 *
 * Deploy:
 *   wrangler publish
 *
 * Test:
 *   curl --http3 https://your-worker.workers.dev
 *   curl -I https://your-worker.workers.dev | grep -i alt-svc
 *
 * Features:
 *   - Automatic HTTP/3 support (no configuration needed)
 *   - 0-RTT optimization for fast connections
 *   - Connection migration support
 *   - Edge caching with HTTP/3
 */

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

/**
 * Handle incoming request
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function handleRequest(request) {
  const url = new URL(request.url)
  const path = url.pathname

  // Route based on path
  switch (path) {
    case '/':
      return handleHome(request)
    case '/api/data':
      return handleAPI(request)
    case '/stream':
      return handleStream(request)
    case '/cache':
      return handleCache(request)
    case '/protocol-info':
      return handleProtocolInfo(request)
    default:
      return new Response('Not Found', { status: 404 })
  }
}

/**
 * Home page
 */
function handleHome(request) {
  const html = `
<!DOCTYPE html>
<html>
<head>
  <title>HTTP/3 on Cloudflare Workers</title>
  <meta charset="utf-8">
</head>
<body>
  <h1>HTTP/3 Demo on Cloudflare Workers</h1>
  <p>This page is served over HTTP/3 (QUIC)</p>

  <h2>Protocol Information</h2>
  <div id="protocol-info">Loading...</div>

  <h2>Endpoints</h2>
  <ul>
    <li><a href="/api/data">API Data (JSON)</a></li>
    <li><a href="/stream">Server-Sent Events Stream</a></li>
    <li><a href="/cache">Cached Response</a></li>
    <li><a href="/protocol-info">Protocol Info (JSON)</a></li>
  </ul>

  <script>
    // Fetch protocol info
    fetch('/protocol-info')
      .then(r => r.json())
      .then(data => {
        document.getElementById('protocol-info').innerHTML =
          '<pre>' + JSON.stringify(data, null, 2) + '</pre>'
      })

    // Check performance API
    window.addEventListener('load', () => {
      const nav = performance.getEntriesByType('navigation')[0]
      if (nav) {
        console.log('Protocol:', nav.nextHopProtocol)
        console.log('Connection Time:', nav.connectEnd - nav.connectStart, 'ms')
        console.log('TLS Time:', nav.secureConnectionStart ?
          nav.connectEnd - nav.secureConnectionStart : 'N/A', 'ms')
      }
    })
  </script>
</body>
</html>
  `

  return new Response(html, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'public, max-age=3600',
      // Note: Cloudflare automatically adds Alt-Svc header
    }
  })
}

/**
 * API endpoint
 */
async function handleAPI(request) {
  // Simulate API delay
  await sleep(100)

  const data = {
    timestamp: Date.now(),
    message: 'Hello from HTTP/3',
    protocol: request.cf?.httpProtocol || 'unknown',
    country: request.cf?.country || 'unknown',
    colo: request.cf?.colo || 'unknown',
    features: {
      http3: true,
      '0rtt': request.cf?.tlsVersion === '0-RTT',
      tlsVersion: request.cf?.tlsVersion || 'unknown',
    }
  }

  return new Response(JSON.stringify(data, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache',
    }
  })
}

/**
 * Server-Sent Events stream
 */
async function handleStream(request) {
  const { readable, writable } = new TransformStream()
  const writer = writable.getWriter()
  const encoder = new TextEncoder()

  // Stream events
  streamEvents(writer, encoder)

  return new Response(readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    }
  })
}

async function streamEvents(writer, encoder) {
  try {
    for (let i = 0; i < 10; i++) {
      const event = `data: ${JSON.stringify({
        id: i,
        timestamp: Date.now(),
        message: `Event ${i}`
      })}\n\n`

      await writer.write(encoder.encode(event))
      await sleep(1000)
    }

    await writer.close()
  } catch (err) {
    console.error('Stream error:', err)
  }
}

/**
 * Cached response (demonstrates edge caching with HTTP/3)
 */
async function handleCache(request) {
  const cache = caches.default
  const cacheKey = new Request(request.url, request)

  // Try cache first
  let response = await cache.match(cacheKey)

  if (!response) {
    // Generate response
    const data = {
      timestamp: Date.now(),
      message: 'This response is cached at the edge',
      ttl: 3600,
    }

    response = new Response(JSON.stringify(data, null, 2), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=3600',
        'X-Cache': 'MISS',
      }
    })

    // Store in cache
    await cache.put(cacheKey, response.clone())
  } else {
    // Add cache hit header
    response = new Response(response.body, response)
    response.headers.set('X-Cache', 'HIT')
  }

  return response
}

/**
 * Protocol information
 */
function handleProtocolInfo(request) {
  const cf = request.cf || {}

  const info = {
    // Request info
    url: request.url,
    method: request.method,

    // Cloudflare metadata
    httpProtocol: cf.httpProtocol || 'unknown',
    tlsVersion: cf.tlsVersion || 'unknown',
    tlsCipher: cf.tlsCipher || 'unknown',
    country: cf.country || 'unknown',
    colo: cf.colo || 'unknown',
    asn: cf.asn || 'unknown',

    // HTTP/3 features
    features: {
      http3: cf.httpProtocol === 'HTTP/3',
      '0rtt': cf.tlsVersion === '0-RTT',
      earlyData: cf.tlsVersion === '0-RTT',
    },

    // Request headers
    headers: Object.fromEntries(request.headers),

    // Notes
    notes: {
      http3: 'Cloudflare automatically enables HTTP/3',
      '0rtt': '0-RTT allows zero-latency connection resumption',
      migration: 'QUIC supports connection migration (WiFi to cellular)',
      multiplexing: 'No head-of-line blocking (unlike HTTP/2)',
    }
  }

  return new Response(JSON.stringify(info, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-cache',
    }
  })
}

/**
 * Sleep utility
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * wrangler.toml configuration:
 *
 * name = "http3-demo"
 * type = "javascript"
 * account_id = "your-account-id"
 * workers_dev = true
 * route = "https://your-domain.com/*"
 * zone_id = "your-zone-id"
 *
 * [env.production]
 * name = "http3-demo-production"
 * route = "https://your-domain.com/*"
 */

/**
 * Testing:
 *
 * # Check HTTP/3 support
 * curl -I https://your-worker.workers.dev | grep -i alt-svc
 *
 * # Test with HTTP/3 (curl 7.66+)
 * curl --http3 https://your-worker.workers.dev/protocol-info
 *
 * # Check protocol in browser DevTools
 * 1. Open DevTools → Network tab
 * 2. Load page
 * 3. Check "Protocol" column (should show "h3")
 *
 * # Performance comparison
 * curl -w "@curl-format.txt" --http3 https://your-worker.workers.dev
 * curl -w "@curl-format.txt" --http2 https://your-worker.workers.dev
 *
 * # curl-format.txt:
 *     time_namelookup:  %{time_namelookup}\n
 *        time_connect:  %{time_connect}\n
 *     time_appconnect:  %{time_appconnect}\n
 *       time_redirect:  %{time_redirect}\n
 *    time_pretransfer:  %{time_pretransfer}\n
 *  time_starttransfer:  %{time_starttransfer}\n
 *                     ----------\n
 *          time_total:  %{time_total}\n
 */
