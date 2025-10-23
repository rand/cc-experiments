# Streaming and Progressive Loading

Content that appears instantly feels fast. Stream when possible, load progressively.

## Streaming Text

For real-time text streaming (like ChatGPT):

```typescript
function StreamingText({ stream }: { stream: ReadableStream<Uint8Array> }) {
  const [content, setContent] = useState('');
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    const reader = stream.getReader();
    const decoder = new TextDecoder();

    async function read() {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            setIsComplete(true);
            break;
          }
          
          const text = decoder.decode(value, { stream: true });
          setContent(prev => prev + text);
        }
      } catch (error) {
        console.error('Stream error:', error);
        setIsComplete(true);
      }
    }

    read();

    return () => {
      reader.cancel();
    };
  }, [stream]);

  return (
    <div className="streaming-content">
      {content}
      {!isComplete && <span className="cursor-blink">▊</span>}
    </div>
  );
}
```

### Cursor Animation

```css
.cursor-blink {
  animation: blink 1s ease-in-out infinite;
  font-family: 'JetBrains Mono', monospace;
}

@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}
```

## Progressive Loading Patterns

### 1. Skeleton Screens (Preferred)

Skeleton screens are better than spinners for predictable layouts.

```css
.skeleton {
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e0e0e0 50%,
    #f0f0f0 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  .skeleton {
    background: linear-gradient(
      90deg,
      #1a1a1a 25%,
      #2a2a2a 50%,
      #1a1a1a 75%
    );
  }
}
```

**Usage:**
```tsx
function CardSkeleton() {
  return (
    <div className="card">
      <div className="skeleton" style={{ height: '200px', marginBottom: '1rem' }} />
      <div className="skeleton" style={{ height: '1.5rem', width: '60%', marginBottom: '0.5rem' }} />
      <div className="skeleton" style={{ height: '1rem', width: '100%' }} />
      <div className="skeleton" style={{ height: '1rem', width: '80%' }} />
    </div>
  );
}
```

### 2. Incremental Rendering

Load critical content first, defer below-the-fold:

```typescript
function Page() {
  const [aboveFold, setAboveFold] = useState(null);
  const [belowFold, setBelowFold] = useState(null);

  useEffect(() => {
    // Load critical content immediately
    fetchAboveFold().then(setAboveFold);
    
    // Delay below-fold content
    setTimeout(() => {
      fetchBelowFold().then(setBelowFold);
    }, 100);
  }, []);

  return (
    <>
      {aboveFold ? <AboveFold data={aboveFold} /> : <Skeleton />}
      {belowFold ? <BelowFold data={belowFold} /> : null}
    </>
  );
}
```

### 3. Optimistic Updates

Assume success, rollback on error:

```typescript
function TodoList() {
  const [items, setItems] = useState<Todo[]>([]);

  const addItem = async (newItem: Omit<Todo, 'id'>) => {
    // Create temporary item
    const tempItem = { ...newItem, id: 'temp', pending: true };
    
    // Add immediately (optimistic)
    setItems(prev => [...prev, tempItem]);
    
    try {
      // Save to server
      const saved = await api.saveTodo(newItem);
      
      // Replace temp with real
      setItems(prev => prev.map(item => 
        item.id === 'temp' ? saved : item
      ));
    } catch (error) {
      // Rollback on error
      setItems(prev => prev.filter(item => item.id !== 'temp'));
      toast.error('Failed to add item');
    }
  };

  return (
    <div>
      {items.map(item => (
        <TodoItem 
          key={item.id} 
          item={item}
          isPending={item.pending}
        />
      ))}
    </div>
  );
}
```

## Loading Indicators

### Spinners

```css
/* Elegant spinner */
.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Dots loader (more subtle) */
.dots-loader {
  display: flex;
  gap: 4px;
}

.dot {
  width: 6px;
  height: 6px;
  background: var(--color-primary);
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite;
}

.dot:nth-child(1) { animation-delay: 0s; }
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}
```

### Progress Bars

```css
.progress-bar {
  width: 100%;
  height: 4px;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  transition: width 0.3s ease;
}

/* Indeterminate state */
.progress-fill.indeterminate {
  width: 30%;
  animation: indeterminate 1.5s ease-in-out infinite;
}

@keyframes indeterminate {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}
```

### Loading State Hierarchy

Choose based on operation duration:

1. **< 100ms**: No indicator (feels instant)
2. **100ms - 1s**: Spinner or indeterminate progress bar
3. **1s - 5s**: Skeleton screen + percentage if available
4. **5s+**: Progress bar + time estimate + cancel button

```typescript
function useLoadingIndicator(duration: number) {
  if (duration < 100) return null;
  if (duration < 1000) return <Spinner />;
  if (duration < 5000) return <Skeleton />;
  return <ProgressBar withCancel />;
}
```

## Best Practices

### Do:
- ✅ Use skeleton screens for predictable layouts
- ✅ Stream content when possible
- ✅ Load critical content first (above the fold)
- ✅ Show progress for operations > 1 second
- ✅ Provide cancel buttons for long operations
- ✅ Use optimistic updates for better perceived performance
- ✅ Respect reduced-motion preferences

### Don't:
- ❌ Show spinners for instant operations (< 100ms)
- ❌ Block entire UI during loading
- ❌ Use spinners when skeleton screens would be better
- ❌ Forget to handle loading errors
- ❌ Make users wait without feedback
- ❌ Ignore cancel requests during long operations

## Server-Sent Events (SSE)

For server-to-client streaming:

```typescript
function useSSE(url: string) {
  const [data, setData] = useState<string[]>([]);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      setData(prev => [...prev, event.data]);
    };

    eventSource.onerror = (err) => {
      setError(new Error('SSE connection error'));
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [url]);

  return { data, error };
}
```

## WebSockets

For bidirectional real-time communication:

```typescript
function useWebSocket(url: string) {
  const [messages, setMessages] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = (event) => {
      setMessages(prev => [...prev, event.data]);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const send = (message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  };

  return { messages, isConnected, send };
}
```
