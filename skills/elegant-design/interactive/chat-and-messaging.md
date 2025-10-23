# Chat and Messaging Interfaces

Chat is a conversation, not a document. Design for flow and readability.

## Message Structure

```typescript
interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  attachments?: Attachment[];
}
```

## Visual Design Guidelines

**Layout:**
- **Alternating alignment**: User messages right, assistant left (or use color/avatar distinction)
- **Generous padding**: 16-24px within messages for readability
- **Subtle backgrounds**: Use background color to distinguish roles, not heavy borders
- **Avatar placement**: Left side with 8-12px spacing
- **Time stamps**: Subtle, small (11-12px), gray, right-aligned or on hover
- **Max width**: 65-75 characters (600-800px) for message content

```css
.chat-container {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.message {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: 12px;
  max-width: 75%;
}

.message-user {
  align-self: flex-end;
  background: var(--color-primary);
  color: var(--color-primary-foreground);
}

.message-assistant {
  align-self: flex-start;
  background: var(--color-muted);
  color: var(--color-foreground);
}

.message-timestamp {
  font-size: 11px;
  color: var(--color-muted-foreground);
  margin-top: var(--space-1);
}
```

## Message States

```css
/* Sending state - subtle opacity */
.message-sending {
  opacity: 0.6;
  transition: opacity 0.2s;
}

/* Error state - clear but not alarming */
.message-error {
  border-left: 3px solid var(--color-error);
  background: color-mix(in srgb, var(--color-error) 5%, transparent);
}

/* Streaming state - subtle pulse */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.message-streaming::after {
  content: '▊';
  animation: pulse 1s ease-in-out infinite;
  font-family: 'JetBrains Mono', monospace;
}
```

## Input Area Design

**Features:**
- **Auto-expanding textarea**: Grows with content, max 6-8 lines before scroll
- **Clear send button**: Icon + text on desktop, icon only on mobile
- **Attachment preview**: Show thumbnails of uploaded files
- **Character limit**: Show remaining count only when approaching limit
- **Loading state**: Disable input, show spinner in send button

```typescript
const ChatInput = () => {
  const [message, setMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 8 * 24)}px`; // max 8 lines
    }
  };

  return (
    <div className="chat-input">
      <textarea
        ref={textareaRef}
        value={message}
        onChange={(e) => {
          setMessage(e.target.value);
          adjustHeight();
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
        placeholder="Type a message..."
        disabled={isSubmitting}
      />
      <button onClick={handleSend} disabled={isSubmitting || !message.trim()}>
        {isSubmitting ? <Spinner /> : <SendIcon />}
      </button>
    </div>
  );
};
```

## Scroll Behavior

**CRITICAL:** Respect user scroll position while auto-scrolling for new messages.

```typescript
function ChatMessages({ messages }: { messages: Message[] }) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isUserScrolling, setIsUserScrolling] = useState(false);

  const scrollToBottom = () => {
    if (!isUserScrolling) {
      messagesEndRef.current?.scrollIntoView({ 
        behavior: 'smooth',
        block: 'end'
      });
    }
  };

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollHeight, scrollTop, clientHeight } = container;
      // User is near bottom if within 100px
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      setIsUserScrolling(!isNearBottom);
    };

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div ref={scrollContainerRef} className="messages-container">
      {messages.map((msg) => (
        <Message key={msg.id} message={msg} />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}
```

## Markdown Rendering

**Libraries:**
- `react-markdown` - Parse and render markdown
- `remark-gfm` - GitHub Flavored Markdown support
- `rehype-sanitize` - Sanitize HTML to prevent XSS

```typescript
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

function MessageContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeSanitize]}
      components={{
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          return !inline && match ? (
            <SyntaxHighlighter
              style={oneDark}
              language={match[1]}
              PreTag="div"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          ) : (
            <code className={className} {...props}>
              {children}
            </code>
          );
        }
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

## Streaming Messages

For real-time streaming (like ChatGPT):

```typescript
function StreamingMessage({ stream }: { stream: ReadableStream }) {
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
      }
    }

    read();
  }, [stream]);

  return (
    <div className="streaming-message">
      <MessageContent content={content} />
      {!isComplete && <span className="cursor-blink">▊</span>}
    </div>
  );
}
```

## Best Practices

### Do:
- ✅ Preserve user scroll position (don't force scroll if reading)
- ✅ Show message status (sending, sent, error)
- ✅ Support markdown and code highlighting
- ✅ Use generous spacing (16-24px padding)
- ✅ Limit message width (65-75 characters)
- ✅ Show timestamps subtly
- ✅ Support keyboard shortcuts (Enter to send, Shift+Enter for newline)
- ✅ Sanitize HTML to prevent XSS

### Don't:
- ❌ Force scroll when user is reading older messages
- ❌ Make messages too wide (hard to read)
- ❌ Use heavy borders or shadows
- ❌ Show timestamps prominently (they're noise)
- ❌ Forget error recovery (retry failed messages)
- ❌ Block input during streaming (allow cancellation)
- ❌ Render unsanitized HTML from user input
