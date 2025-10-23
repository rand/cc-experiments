# Terminals and Code Display

Terminals and code blocks need to be readable, beautiful, and functional.

## Terminal Interfaces

Terminals are where developers feel at home. Make them beautiful with JetBrains Mono.

### Visual Design

```css
.terminal {
  background: #0d1117; /* GitHub dark background */
  color: #c9d1d9;
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  line-height: 1.5;
  padding: 1rem;
  border-radius: 8px;
  overflow: auto;
}

.terminal-prompt {
  color: #58a6ff; /* Bright blue */
  user-select: none;
}

.terminal-prompt::before {
  content: '$ ';
  color: #8b949e; /* Muted gray */
}

.terminal-output {
  white-space: pre-wrap;
  word-break: break-word;
}
```

### ANSI Color Support

Support standard ANSI escape codes for colored terminal output.

```typescript
// ANSI color mapping (standard 16 colors)
const ansiColors = {
  // Normal colors (30-37)
  30: '#24292f', // black
  31: '#cf222e', // red
  32: '#1a7f37', // green
  33: '#9a6700', // yellow
  34: '#0969da', // blue
  35: '#8250df', // magenta
  36: '#1b7c83', // cyan
  37: '#6e7781', // white
  
  // Bright colors (90-97)
  90: '#57606a', // bright black (gray)
  91: '#ff6b6b', // bright red
  92: '#4ade80', // bright green
  93: '#fbbf24', // bright yellow
  94: '#60a5fa', // bright blue
  95: '#c084fc', // bright magenta
  96: '#22d3ee', // bright cyan
  97: '#f5f5f5', // bright white
};

function parseAnsi(text: string): React.ReactNode[] {
  const ansiRegex = /\x1b\[([0-9;]+)m/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let currentColor: string | null = null;

  let match;
  while ((match = ansiRegex.exec(text)) !== null) {
    // Add text before this code
    if (match.index > lastIndex) {
      const textPart = text.slice(lastIndex, match.index);
      parts.push(
        currentColor ? (
          <span key={parts.length} style={{ color: currentColor }}>
            {textPart}
          </span>
        ) : (
          textPart
        )
      );
    }

    // Parse color code
    const codes = match[1].split(';').map(Number);
    if (codes[0] === 0) {
      currentColor = null; // reset
    } else if (ansiColors[codes[0]]) {
      currentColor = ansiColors[codes[0]];
    }

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    const textPart = text.slice(lastIndex);
    parts.push(
      currentColor ? (
        <span key={parts.length} style={{ color: currentColor }}>
          {textPart}
        </span>
      ) : (
        textPart
      )
    );
  }

  return parts;
}
```

### Terminal Features

**Essential features:**
- **Command history**: Up/down arrows to cycle through past commands
- **Auto-completion**: Tab to complete common commands/paths
- **Output streaming**: Show output as it arrives
- **Clear command**: Button or Ctrl+L to clear terminal
- **Copy output**: Click to copy command output
- **Line wrapping**: Wrap long lines intelligently

```typescript
function Terminal() {
  const [history, setHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [input, setInput] = useState('');
  const [output, setOutput] = useState<string[]>([]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIndex < history.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setInput(history[history.length - 1 - newIndex]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setInput(history[history.length - 1 - newIndex]);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setInput('');
      }
    } else if (e.key === 'Enter') {
      handleCommand(input);
      setHistory([...history, input]);
      setHistoryIndex(-1);
      setInput('');
    }
  };

  return (
    <div className="terminal">
      <div className="terminal-output">
        {output.map((line, i) => (
          <div key={i}>{parseAnsi(line)}</div>
        ))}
      </div>
      <div className="terminal-input-line">
        <span className="terminal-prompt">$</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="terminal-input"
        />
      </div>
    </div>
  );
}
```

### Terminal Aesthetics

**Three style options:**

1. **clean-professional** (recommended):
```css
.terminal-clean {
  background: #0d1117;
  /* No effects, perfect clarity */
}
```

2. **retro-modern** (subtle effects):
```css
.terminal-retro {
  background: #0d1117;
  text-shadow: 0 0 2px currentColor;
  background-image: 
    repeating-linear-gradient(
      0deg,
      rgba(0, 0, 0, 0.15),
      rgba(0, 0, 0, 0.15) 1px,
      transparent 1px,
      transparent 2px
    );
}
```

3. **themed** (match color scheme):
Use GitHub, Dracula, Nord, or other popular terminal themes.

## Code Display & Syntax Highlighting

### Shiki (Primary Choice)

Use Shiki for server-side syntax highlighting with TextMate grammars.

```typescript
import { codeToHtml } from 'shiki';

async function highlightCode(code: string, lang: string) {
  return await codeToHtml(code, {
    lang,
    theme: 'github-dark', // or 'github-light', 'dracula', 'nord', etc.
  });
}

// In component
<div dangerouslySetInnerHTML={{ __html: highlightedCode }} />
```

### Code Block Design

```css
.code-block {
  background: #0d1117;
  border-radius: 8px;
  overflow: hidden;
  margin: 1.5rem 0;
  box-shadow: var(--shadow-lg);
  font-family: 'JetBrains Mono', monospace;
}

.code-header {
  background: #161b22;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #30363d;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.code-language {
  font-size: 0.75rem;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.code-content {
  padding: 1rem;
  overflow-x: auto;
  font-size: 14px;
  line-height: 1.6;
}

/* Line numbers */
.code-line {
  display: table-row;
}

.code-line-number {
  display: table-cell;
  padding-right: 1rem;
  color: #6e7781;
  text-align: right;
  user-select: none;
  width: 1%;
}

.code-line-content {
  display: table-cell;
}
```

### Copy Button

```typescript
function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const copyCode = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button 
      onClick={copyCode}
      className="copy-button"
      aria-label="Copy code"
    >
      {copied ? <Check size={16} /> : <Copy size={16} />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}
```

### Line Highlighting

Highlight specific lines for emphasis:

```css
.code-line-highlighted {
  background: rgba(255, 255, 0, 0.1);
  border-left: 3px solid #f9c74f;
  padding-left: calc(1rem - 3px);
}
```

## Semantic Highlighting

Go beyond syntax: highlight meaning.

**Use cases:**
- Different colors for local vs global variables
- Highlight unused variables in gray
- Bold function definitions
- Underline errors/warnings
- Dim deprecated code

```typescript
// Using tree-sitter or LSP for semantic analysis
function applySemanticHighlighting(tokens: Token[]) {
  return tokens.map(token => {
    if (token.type === 'variable.unused') {
      return {
        ...token,
        style: 'opacity: 0.5; text-decoration: line-through;'
      };
    }
    if (token.type === 'function.definition') {
      return {
        ...token,
        style: 'font-weight: 600;'
      };
    }
    if (token.type === 'variable.parameter') {
      return {
        ...token,
        style: 'font-style: italic;'
      };
    }
    return token;
  });
}
```

## Best Practices

### Do:
- ✅ Use JetBrains Mono at 14px minimum
- ✅ Support ANSI colors in terminals
- ✅ Provide copy buttons on code blocks
- ✅ Enable ligatures in monospace fonts
- ✅ Use Shiki for accurate syntax highlighting
- ✅ Show language label on code blocks
- ✅ Support line highlighting
- ✅ Provide line numbers (optional, toggleable)

### Don't:
- ❌ Use font smaller than 14px for code
- ❌ Show raw ANSI escape codes
- ❌ Forget to make code blocks scrollable
- ❌ Mix multiple monospace fonts
- ❌ Use syntax highlighters without proper theme support
- ❌ Forget keyboard accessibility (tab through code)
