---
name: bubbletea-architecture
description: Building terminal UIs in Go
---



# Bubble Tea Architecture (Go TUI)

**Use this skill when:**
- Building terminal UIs in Go
- Implementing Elm architecture in Go
- Creating interactive CLI applications
- Working with Charm.sh ecosystem
- Building production-ready TUIs

## Core Concepts

The Elm Architecture (Model-Update-View):
- **Model**: Application state
- **Update**: Handle messages and update state
- **View**: Render UI from state

## Basic Application

### Minimal Bubble Tea App

```go
package main

import (
    "fmt"
    "os"

    tea "github.com/charmbracelet/bubbletea"
)

// Model holds application state
type model struct {
    count int
}

// Init returns initial command
func (m model) Init() tea.Cmd {
    return nil
}

// Update handles messages and returns new model
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "ctrl+c", "q":
            return m, tea.Quit

        case "up", "k":
            m.count++

        case "down", "j":
            if m.count > 0 {
                m.count--
            }
        }
    }

    return m, nil
}

// View renders the UI
func (m model) View() string {
    return fmt.Sprintf(
        "Count: %d\n\n"+
        "Press ↑/k to increment, ↓/j to decrement\n"+
        "Press q to quit\n",
        m.count,
    )
}

func main() {
    p := tea.NewProgram(model{count: 0})
    if _, err := p.Run(); err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
}
```

## Messages and Commands

### Custom Messages

```go
type tickMsg time.Time
type fetchedDataMsg struct {
    data string
    err  error
}

// Command that sends tick message every second
func tickEvery() tea.Cmd {
    return tea.Tick(time.Second, func(t time.Time) tea.Msg {
        return tickMsg(t)
    })
}

// Command that fetches data
func fetchData() tea.Cmd {
    return func() tea.Msg {
        data, err := callAPI()
        return fetchedDataMsg{data: data, err: err}
    }
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tickMsg:
        m.lastTick = time.Time(msg)
        return m, tickEvery()

    case fetchedDataMsg:
        if msg.err != nil {
            m.error = msg.err
            return m, nil
        }
        m.data = msg.data
        return m, nil

    case tea.KeyMsg:
        if msg.String() == "r" {
            return m, fetchData()
        }
    }

    return m, nil
}
```

## State Management

### Complex State

```go
type model struct {
    // UI state
    activeTab   int
    cursor      int
    viewport    viewport.Model

    // Data state
    items       []Item
    loading     bool
    error       error

    // Sub-models
    input       textinput.Model
    list        list.Model
    spinner     spinner.Model
}

func (m model) Init() tea.Cmd {
    return tea.Batch(
        m.spinner.Tick,
        loadItems(),
    )
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    var cmds []tea.Cmd

    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "ctrl+c", "q":
            return m, tea.Quit

        case "tab":
            m.activeTab = (m.activeTab + 1) % 3

        case "enter":
            return m, submitForm(m.input.Value())
        }

    case loadedItemsMsg:
        m.items = msg.items
        m.loading = false
        return m, nil

    case spinner.TickMsg:
        var cmd tea.Cmd
        m.spinner, cmd = m.spinner.Update(msg)
        cmds = append(cmds, cmd)
    }

    // Update sub-models
    var cmd tea.Cmd
    m.input, cmd = m.input.Update(msg)
    cmds = append(cmds, cmd)

    return m, tea.Batch(cmds...)
}
```

## Layout and Rendering

### Multi-Section View

```go
func (m model) View() string {
    var s strings.Builder

    // Header
    s.WriteString(headerStyle.Render("My Application"))
    s.WriteString("\n\n")

    // Tabs
    s.WriteString(m.renderTabs())
    s.WriteString("\n\n")

    // Content based on active tab
    switch m.activeTab {
    case 0:
        s.WriteString(m.renderHomeTab())
    case 1:
        s.WriteString(m.renderSearchTab())
    case 2:
        s.WriteString(m.renderSettingsTab())
    }

    // Footer
    s.WriteString("\n\n")
    s.WriteString(footerStyle.Render("Press q to quit"))

    return s.String()
}

func (m model) renderTabs() string {
    tabs := []string{"Home", "Search", "Settings"}
    var renderedTabs []string

    for i, tab := range tabs {
        if i == m.activeTab {
            renderedTabs = append(renderedTabs, activeTabStyle.Render(tab))
        } else {
            renderedTabs = append(renderedTabs, inactiveTabStyle.Render(tab))
        }
    }

    return lipgloss.JoinHorizontal(lipgloss.Top, renderedTabs...)
}
```

## Async Operations

### Loading Data

```go
type loadingMsg struct{}
type loadedMsg struct {
    items []Item
}
type errorMsg struct {
    err error
}

func loadItems() tea.Cmd {
    return func() tea.Msg {
        items, err := fetchItemsFromAPI()
        if err != nil {
            return errorMsg{err: err}
        }
        return loadedMsg{items: items}
    }
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        if msg.String() == "r" {
            m.loading = true
            return m, loadItems()
        }

    case loadedMsg:
        m.items = msg.items
        m.loading = false
        return m, nil

    case errorMsg:
        m.error = msg.err
        m.loading = false
        return m, nil
    }

    return m, nil
}

func (m model) View() string {
    if m.loading {
        return m.spinner.View() + " Loading..."
    }

    if m.error != nil {
        return errorStyle.Render(fmt.Sprintf("Error: %v", m.error))
    }

    return m.renderItems()
}
```

## Navigation

### Multi-Page Navigation

```go
type page int

const (
    listPage page = iota
    detailPage
    editPage
)

type model struct {
    currentPage page
    pageStack   []page
    selectedID  int
}

func (m model) navigateTo(p page) (model, tea.Cmd) {
    m.pageStack = append(m.pageStack, m.currentPage)
    m.currentPage = p
    return m, nil
}

func (m model) navigateBack() (model, tea.Cmd) {
    if len(m.pageStack) == 0 {
        return m, tea.Quit
    }

    m.currentPage = m.pageStack[len(m.pageStack)-1]
    m.pageStack = m.pageStack[:len(m.pageStack)-1]
    return m, nil
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "esc":
            return m.navigateBack()

        case "enter":
            if m.currentPage == listPage {
                return m.navigateTo(detailPage)
            }
        }
    }

    return m, nil
}

func (m model) View() string {
    switch m.currentPage {
    case listPage:
        return m.renderList()
    case detailPage:
        return m.renderDetail()
    case editPage:
        return m.renderEdit()
    default:
        return "Unknown page"
    }
}
```

## Testing

### Test Update Function

```go
func TestUpdate(t *testing.T) {
    m := model{count: 5}

    // Test increment
    m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'k'}})

    if m.(model).count != 6 {
        t.Errorf("Expected count 6, got %d", m.(model).count)
    }

    // Test decrement
    m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'j'}})

    if m.(model).count != 5 {
        t.Errorf("Expected count 5, got %d", m.(model).count)
    }
}
```

## Anti-Patterns to Avoid

**DON'T mutate model directly in View:**
```go
// ❌ BAD
func (m model) View() string {
    m.count++  // Never mutate in View!
    return fmt.Sprintf("Count: %d", m.count)
}

// ✅ GOOD
func (m model) View() string {
    return fmt.Sprintf("Count: %d", m.count)
}
```

**DON'T block in Update:**
```go
// ❌ BAD
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    time.Sleep(5 * time.Second)  // Blocks UI!
    return m, nil
}

// ✅ GOOD
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    return m, doAsyncWork()  // Return command instead
}

func doAsyncWork() tea.Cmd {
    return func() tea.Msg {
        time.Sleep(5 * time.Second)
        return workCompleteMsg{}
    }
}
```

## Related Skills

- **bubbletea-components.md** - Pre-built Bubbles components
- **tui-best-practices.md** - TUI design patterns
