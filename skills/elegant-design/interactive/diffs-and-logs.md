# Diffs and Log Viewers

Version control UIs and log viewers need clarity and scannability.

## Diff Viewers

Show changes clearly and elegantly.

### Split View Layout

```css
.diff-viewer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
}

.diff-side {
  background: var(--color-background);
  overflow-x: auto;
}

.diff-line {
  padding: 2px 8px;
  line-height: 1.6;
  min-height: 1.6em;
}

.diff-line-removed {
  background: rgba(255, 0, 0, 0.1);
  border-left: 3px solid rgba(255, 0, 0, 0.5);
}

.diff-line-added {
  background: rgba(0, 255, 0, 0.1);
  border-left: 3px solid rgba(0, 255, 0, 0.5);
}

.diff-line-modified {
  background: rgba(255, 165, 0, 0.1);
  border-left: 3px solid rgba(255, 165, 0, 0.5);
}

.diff-line-unchanged {
  color: var(--color-muted-foreground);
}
```

### Unified Diff (Inline View)

```css
.diff-unified {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  line-height: 1.6;
}

.diff-line {
  padding: 2px 8px;
  display: flex;
  gap: 1rem;
}

.diff-line-number {
  color: var(--color-muted-foreground);
  min-width: 3ch;
  text-align: right;
  user-select: none;
}

.diff-line-removed {
  background: #fff5f5;
  color: #c53030;
}

.diff-line-removed::before {
  content: '- ';
  color: #c53030;
  user-select: none;
}

.diff-line-added {
  background: #f0fff4;
  color: #22543d;
}

.diff-line-added::before {
  content: '+ ';
  color: #22543d;
  user-select: none;
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  .diff-line-removed {
    background: rgba(255, 0, 0, 0.15);
    color: #ff6b6b;
  }
  
  .diff-line-added {
    background: rgba(0, 255, 0, 0.15);
    color: #4ade80;
  }
}
```

### Character-Level Diff

Highlight changed characters within lines:

```typescript
import * as Diff from 'diff';

function renderWordDiff(oldText: string, newText: string) {
  const diffs = Diff.diffWords(oldText, newText);
  
  return diffs.map((part, index) => {
    if (part.added) {
      return <ins key={index} className="char-added">{part.value}</ins>;
    }
    if (part.removed) {
      return <del key={index} className="char-removed">{part.value}</del>;
    }
    return <span key={index}>{part.value}</span>;
  });
}
```

```css
.char-added {
  background: rgba(0, 255, 0, 0.3);
  text-decoration: none;
}

.char-removed {
  background: rgba(255, 0, 0, 0.3);
  text-decoration: line-through;
}
```

## Log Viewers

Logs need to be scannable, searchable, and filterable.

### Log Entry Structure

```css
.log-viewer {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.log-entry {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  gap: 1rem;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid var(--color-border);
  align-items: center;
}

.log-entry:hover {
  background: rgba(0, 0, 0, 0.03);
}

.log-timestamp {
  color: var(--color-muted-foreground);
  font-size: 12px;
  user-select: none;
}

.log-level {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.log-level-error {
  background: rgba(255, 0, 0, 0.1);
  color: #c53030;
}

.log-level-warn {
  background: rgba(255, 165, 0, 0.1);
  color: #dd6b20;
}

.log-level-info {
  background: rgba(0, 123, 255, 0.1);
  color: #2b6cb0;
}

.log-level-debug {
  background: rgba(128, 128, 128, 0.1);
  color: #718096;
}

.log-message {
  font-family: 'JetBrains Mono', monospace;
  word-break: break-word;
}

.log-metadata {
  color: var(--color-muted-foreground);
  font-size: 12px;
}
```

### Virtual Scrolling

For 10,000+ log entries, use virtual scrolling:

```typescript
import { FixedSizeList } from 'react-window';

function LogViewer({ logs }: { logs: LogEntry[] }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={logs.length}
      itemSize={30}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          <LogEntry log={logs[index]} />
        </div>
      )}
    </FixedSizeList>
  );
}
```

### Log Filtering

```typescript
function LogViewer({ logs }: { logs: LogEntry[] }) {
  const [filter, setFilter] = useState({
    levels: ['error', 'warn', 'info', 'debug'],
    search: '',
  });

  const filteredLogs = useMemo(() => {
    return logs.filter(log => {
      if (!filter.levels.includes(log.level)) return false;
      if (filter.search && !log.message.toLowerCase().includes(filter.search.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [logs, filter]);

  return (
    <div>
      <LogFilter filter={filter} setFilter={setFilter} />
      <div className="log-entries">
        {filteredLogs.map((log, i) => (
          <LogEntry key={i} log={log} />
        ))}
      </div>
    </div>
  );
}
```

### JSON Log Formatting

Pretty-print JSON logs:

```typescript
function LogMessage({ message }: { message: string }) {
  // Try to parse as JSON
  let parsed: any;
  try {
    parsed = JSON.parse(message);
  } catch {
    return <span>{message}</span>;
  }

  return (
    <details>
      <summary>JSON log (click to expand)</summary>
      <pre style={{ marginTop: '0.5rem' }}>
        {JSON.stringify(parsed, null, 2)}
      </pre>
    </details>
  );
}
```

## Best Practices

### Diffs:
- ✅ Use split view for side-by-side comparison
- ✅ Use unified view for single-file review
- ✅ Highlight character-level changes
- ✅ Use subtle background colors
- ✅ Make line numbers non-selectable
- ✅ Use JetBrains Mono for consistent character width
- ✅ Support both light and dark modes

### Logs:
- ✅ Color-code severity levels
- ✅ Use virtual scrolling for large logs (10,000+)
- ✅ Provide search and filter
- ✅ Show timestamps consistently (ISO 8601)
- ✅ Support log export (CSV/JSON)
- ✅ Auto-scroll for live logs (with pause button)
- ✅ Highlight search matches
- ✅ Expand/collapse for stack traces

### Don't:
- ❌ Use tiny fonts (< 13px for logs)
- ❌ Show thousands of logs without virtual scrolling
- ❌ Forget to make diffs accessible (keyboard nav)
- ❌ Use harsh colors for status (subtle is better)
- ❌ Ignore dark mode
- ❌ Make log timestamps hard to read
