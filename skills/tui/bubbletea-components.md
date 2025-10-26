---
name: bubbletea-components
description: Building UIs with pre-made components
---



# Bubble Tea Components (Bubbles)

**Use this skill when:**
- Building UIs with pre-made components
- Using Charm.sh Bubbles library
- Implementing common UI patterns
- Styling with Lip Gloss
- Creating consistent TUI interfaces

## Text Input

```go
import "github.com/charmbracelet/bubbles/textinput"

type model struct {
    textInput textinput.Model
}

func initialModel() model {
    ti := textinput.New()
    ti.Placeholder = "Enter your name"
    ti.Focus()
    ti.CharLimit = 156
    ti.Width = 20

    return model{textInput: ti}
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmd tea.Cmd
    m.textInput, cmd = m.textInput.Update(msg)
    return m, cmd
}

func (m model) View() string {
    return m.textInput.View()
}
```

## List Component

```go
import "github.com/charmbracelet/bubbles/list"

type item struct {
    title, desc string
}

func (i item) Title() string       { return i.title }
func (i item) Description() string { return i.desc }
func (i item) FilterValue() string { return i.title }

func newList() list.Model {
    items := []list.Item{
        item{title: "Item 1", desc: "Description 1"},
        item{title: "Item 2", desc: "Description 2"},
    }

    l := list.New(items, list.NewDefaultDelegate(), 0, 0)
    l.Title = "My List"
    return l
}
```

## Viewport (Scrolling)

```go
import "github.com/charmbracelet/bubbles/viewport"

type model struct {
    viewport viewport.Model
    ready    bool
}

func (m model) Init() tea.Cmd {
    return nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.WindowSizeMsg:
        if !m.ready {
            m.viewport = viewport.New(msg.Width, msg.Height-2)
            m.viewport.SetContent(longContent)
            m.ready = true
        }

    case tea.KeyMsg:
        var cmd tea.Cmd
        m.viewport, cmd = m.viewport.Update(msg)
        return m, cmd
    }

    return m, nil
}
```

## Spinner

```go
import "github.com/charmbracelet/bubbles/spinner"

type model struct {
    spinner spinner.Model
    loading bool
}

func initialModel() model {
    s := spinner.New()
    s.Spinner = spinner.Dot
    return model{spinner: s, loading: true}
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    if m.loading {
        var cmd tea.Cmd
        m.spinner, cmd = m.spinner.Update(msg)
        return m, cmd
    }
    return m, nil
}

func (m model) View() string {
    if m.loading {
        return m.spinner.View() + " Loading..."
    }
    return "Done!"
}
```

## Styling with Lip Gloss

```go
import "github.com/charmbracelet/lipgloss"

var (
    titleStyle = lipgloss.NewStyle().
        Bold(true).
        Foreground(lipgloss.Color("5")).
        MarginBottom(1)

    boxStyle = lipgloss.NewStyle().
        Border(lipgloss.RoundedBorder()).
        BorderForeground(lipgloss.Color("63")).
        Padding(1, 2)

    activeStyle = lipgloss.NewStyle().
        Bold(true).
        Foreground(lipgloss.Color("10")).
        Background(lipgloss.Color("235"))
)

func (m model) View() string {
    title := titleStyle.Render("My App")
    content := boxStyle.Render("Content here")
    return lipgloss.JoinVertical(lipgloss.Left, title, content)
}
```

## Related Skills

- **bubbletea-architecture.md** - Core Bubble Tea patterns
- **tui-best-practices.md** - Design guidelines
