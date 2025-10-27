---
name: engineering-design-patterns
description: Gang of Four design patterns, when to use each pattern, implementation examples, and anti-patterns
---

# Software Design Patterns

**Scope**: Comprehensive guide to GoF design patterns, usage scenarios, implementations, and anti-patterns
**Lines**: ~400
**Last Updated**: 2025-10-27
**Format Version**: 1.0 (Atomic)

---

## When to Use This Skill

Activate this skill when:
- Solving recurring design problems
- Improving code flexibility and extensibility
- Refactoring complex code
- Designing APIs or frameworks
- Establishing architectural patterns
- Training engineers on design principles
- Reviewing code for design improvements
- Choosing between pattern alternatives

## Core Concepts

### Concept 1: Pattern Categories

**Creational Patterns** (object creation):
- Factory Method, Abstract Factory
- Builder, Prototype, Singleton

**Structural Patterns** (object composition):
- Adapter, Bridge, Composite
- Decorator, Facade, Proxy

**Behavioral Patterns** (object interaction):
- Strategy, Observer, Command
- Template Method, Iterator, State

---

## Creational Patterns

### Pattern 1: Factory Method

**Problem**: Need flexible object creation without specifying exact class

```python
from abc import ABC, abstractmethod

# Product
class Button(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

class HTMLButton(Button):
    def render(self) -> str:
        return "<button>Click me</button>"

class SwiftButton(Button):
    def render(self) -> str:
        return "UIButton(title: 'Click me')"

# Creator
class Dialog(ABC):
    @abstractmethod
    def create_button(self) -> Button:
        pass

    def render(self) -> str:
        button = self.create_button()
        return f"Dialog with {button.render()}"

class WebDialog(Dialog):
    def create_button(self) -> Button:
        return HTMLButton()

class iOSDialog(Dialog):
    def create_button(self) -> Button:
        return SwiftButton()

# Usage
dialog = WebDialog()
print(dialog.render())
# "Dialog with <button>Click me</button>"
```

**When to Use**: When class can't anticipate type of objects to create

---

### Pattern 2: Builder

**Problem**: Construct complex objects step-by-step

```typescript
class Car {
  constructor(
    public engine: string,
    public seats: number,
    public gps: boolean,
    public tripComputer: boolean
  ) {}
}

class CarBuilder {
  private engine: string = "V4";
  private seats: number = 2;
  private gps: boolean = false;
  private tripComputer: boolean = false;

  setEngine(engine: string): this {
    this.engine = engine;
    return this;
  }

  setSeats(seats: number): this {
    this.seats = seats;
    return this;
  }

  setGPS(gps: boolean): this {
    this.gps = gps;
    return this;
  }

  setTripComputer(tripComputer: boolean): this {
    this.tripComputer = tripComputer;
    return this;
  }

  build(): Car {
    return new Car(this.engine, this.seats, this.gps, this.tripComputer);
  }
}

// Usage
const car = new CarBuilder()
  .setEngine("V8")
  .setSeats(4)
  .setGPS(true)
  .build();
```

**When to Use**: Many constructor parameters, optional configurations

---

### Pattern 3: Singleton

**Problem**: Ensure only one instance exists

```python
class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.connection = "Connected to DB"

    def query(self, sql: str):
        return f"Executing: {sql}"

# Usage
db1 = Database()
db2 = Database()
assert db1 is db2  # Same instance!
```

**When to Use**: Database connections, loggers, configuration
**Warning**: Often considered anti-pattern (use dependency injection instead)

---

## Structural Patterns

### Pattern 4: Adapter

**Problem**: Make incompatible interfaces work together

```go
// Target interface (what client expects)
type MediaPlayer interface {
    Play(audioType string, fileName string)
}

// Adaptee (existing incompatible class)
type VLCPlayer struct{}

func (v *VLCPlayer) PlayVLC(fileName string) {
    fmt.Printf("Playing VLC file: %s\n", fileName)
}

// Adapter
type MediaAdapter struct {
    vlcPlayer *VLCPlayer
}

func (a *MediaAdapter) Play(audioType string, fileName string) {
    if audioType == "vlc" {
        a.vlcPlayer.PlayVLC(fileName)
    }
}

// Client
type AudioPlayer struct {
    adapter *MediaAdapter
}

func (a *AudioPlayer) Play(audioType string, fileName string) {
    if audioType == "mp3" {
        fmt.Printf("Playing MP3 file: %s\n", fileName)
    } else if audioType == "vlc" {
        a.adapter.Play(audioType, fileName)
    }
}
```

**When to Use**: Integrate third-party libraries, legacy code

---

### Pattern 5: Decorator

**Problem**: Add behavior to objects dynamically

```python
# Component
class Coffee:
    def cost(self) -> float:
        return 2.0

    def description(self) -> str:
        return "Coffee"

# Decorators
class MilkDecorator:
    def __init__(self, coffee: Coffee):
        self._coffee = coffee

    def cost(self) -> float:
        return self._coffee.cost() + 0.5

    def description(self) -> str:
        return self._coffee.description() + ", Milk"

class SugarDecorator:
    def __init__(self, coffee: Coffee):
        self._coffee = coffee

    def cost(self) -> float:
        return self._coffee.cost() + 0.2

    def description(self) -> str:
        return self._coffee.description() + ", Sugar"

# Usage
coffee = Coffee()
coffee = MilkDecorator(coffee)
coffee = SugarDecorator(coffee)

print(coffee.description())  # "Coffee, Milk, Sugar"
print(coffee.cost())  # 2.7
```

**When to Use**: Add responsibilities without subclassing

---

### Pattern 6: Facade

**Problem**: Simplify complex subsystem interface

```typescript
// Complex subsystem
class CPU {
  freeze() { console.log("CPU: Freeze"); }
  jump(position: number) { console.log(`CPU: Jump to ${position}`); }
  execute() { console.log("CPU: Execute"); }
}

class Memory {
  load(position: number, data: string) {
    console.log(`Memory: Load ${data} at ${position}`);
  }
}

class HardDrive {
  read(sector: number, size: number): string {
    console.log(`HardDrive: Read sector ${sector}`);
    return "boot data";
  }
}

// Facade: Simple interface
class ComputerFacade {
  private cpu = new CPU();
  private memory = new Memory();
  private hardDrive = new HardDrive();

  start() {
    this.cpu.freeze();
    this.memory.load(0, this.hardDrive.read(0, 1024));
    this.cpu.jump(0);
    this.cpu.execute();
  }
}

// Usage: Simple!
const computer = new ComputerFacade();
computer.start();
```

**When to Use**: Simplify complex APIs, provide unified interface

---

## Behavioral Patterns

### Pattern 7: Strategy

**Problem**: Select algorithm at runtime

```python
from abc import ABC, abstractmethod

# Strategy interface
class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: float) -> None:
        pass

# Concrete strategies
class CreditCardPayment(PaymentStrategy):
    def __init__(self, card_number: str):
        self.card_number = card_number

    def pay(self, amount: float) -> None:
        print(f"Paid ${amount} with credit card {self.card_number}")

class PayPalPayment(PaymentStrategy):
    def __init__(self, email: str):
        self.email = email

    def pay(self, amount: float) -> None:
        print(f"Paid ${amount} via PayPal ({self.email})")

class CryptoPayment(PaymentStrategy):
    def __init__(self, wallet: str):
        self.wallet = wallet

    def pay(self, amount: float) -> None:
        print(f"Paid ${amount} via crypto wallet {self.wallet}")

# Context
class ShoppingCart:
    def __init__(self, payment_strategy: PaymentStrategy):
        self.payment_strategy = payment_strategy
        self.items = []

    def add_item(self, item: str, price: float):
        self.items.append((item, price))

    def checkout(self):
        total = sum(price for _, price in self.items)
        self.payment_strategy.pay(total)

# Usage
cart = ShoppingCart(CreditCardPayment("1234-5678-9012-3456"))
cart.add_item("Book", 29.99)
cart.add_item("Pen", 5.99)
cart.checkout()
# "Paid $35.98 with credit card 1234-5678-9012-3456"
```

**When to Use**: Multiple algorithms, switch behavior at runtime

---

### Pattern 8: Observer

**Problem**: Notify multiple objects of state changes

```typescript
interface Observer {
  update(temperature: number): void;
}

class WeatherStation {
  private observers: Observer[] = [];
  private temperature: number = 0;

  attach(observer: Observer): void {
    this.observers.push(observer);
  }

  detach(observer: Observer): void {
    this.observers = this.observers.filter(o => o !== observer);
  }

  setTemperature(temp: number): void {
    this.temperature = temp;
    this.notify();
  }

  private notify(): void {
    for (const observer of this.observers) {
      observer.update(this.temperature);
    }
  }
}

class PhoneDisplay implements Observer {
  update(temperature: number): void {
    console.log(`Phone: Temperature is ${temperature}°F`);
  }
}

class WebDisplay implements Observer {
  update(temperature: number): void {
    console.log(`Web: Temperature is ${temperature}°F`);
  }
}

// Usage
const station = new WeatherStation();
const phone = new PhoneDisplay();
const web = new WebDisplay();

station.attach(phone);
station.attach(web);
station.setTemperature(75);
// Phone: Temperature is 75°F
// Web: Temperature is 75°F
```

**When to Use**: Publish-subscribe, event handling, reactive systems

---

### Pattern 9: Command

**Problem**: Encapsulate requests as objects

```go
// Command interface
type Command interface {
    Execute()
    Undo()
}

// Receiver
type Light struct {
    isOn bool
}

func (l *Light) TurnOn() {
    l.isOn = true
    fmt.Println("Light is ON")
}

func (l *Light) TurnOff() {
    l.isOn = false
    fmt.Println("Light is OFF")
}

// Concrete commands
type LightOnCommand struct {
    light *Light
}

func (c *LightOnCommand) Execute() {
    c.light.TurnOn()
}

func (c *LightOnCommand) Undo() {
    c.light.TurnOff()
}

// Invoker
type RemoteControl struct {
    history []Command
}

func (r *RemoteControl) Submit(cmd Command) {
    cmd.Execute()
    r.history = append(r.history, cmd)
}

func (r *RemoteControl) Undo() {
    if len(r.history) > 0 {
        last := r.history[len(r.history)-1]
        last.Undo()
        r.history = r.history[:len(r.history)-1]
    }
}

// Usage
light := &Light{}
onCmd := &LightOnCommand{light: light}

remote := &RemoteControl{}
remote.Submit(onCmd)  // Light is ON
remote.Undo()         // Light is OFF
```

**When to Use**: Undo/redo, queuing operations, transactions

---

### Pattern 10: Template Method

**Problem**: Define algorithm skeleton, defer steps to subclasses

```python
from abc import ABC, abstractmethod

class DataMiner(ABC):
    def mine(self, path: str) -> None:
        """Template method"""
        file = self.open_file(path)
        data = self.extract_data(file)
        parsed = self.parse_data(data)
        analysis = self.analyze_data(parsed)
        self.send_report(analysis)
        self.close_file(file)

    def open_file(self, path: str) -> str:
        return f"Opened {path}"

    @abstractmethod
    def extract_data(self, file: str) -> str:
        pass

    @abstractmethod
    def parse_data(self, data: str) -> dict:
        pass

    def analyze_data(self, data: dict) -> str:
        return "Analysis complete"

    def send_report(self, analysis: str) -> None:
        print(f"Report: {analysis}")

    def close_file(self, file: str) -> None:
        print(f"Closed {file}")

class PDFDataMiner(DataMiner):
    def extract_data(self, file: str) -> str:
        return "PDF data extracted"

    def parse_data(self, data: str) -> dict:
        return {"type": "PDF", "data": data}

class CSVDataMiner(DataMiner):
    def extract_data(self, file: str) -> str:
        return "CSV data extracted"

    def parse_data(self, data: str) -> dict:
        return {"type": "CSV", "data": data}

# Usage
miner = PDFDataMiner()
miner.mine("report.pdf")
```

**When to Use**: Shared algorithm with varying steps

---

## Advanced Patterns

### Pattern 11: Chain of Responsibility

```typescript
abstract class Handler {
  private next: Handler | null = null;

  setNext(handler: Handler): Handler {
    this.next = handler;
    return handler;
  }

  handle(request: string): string | null {
    if (this.next) {
      return this.next.handle(request);
    }
    return null;
  }
}

class AuthHandler extends Handler {
  handle(request: string): string | null {
    if (request.includes("authenticated")) {
      console.log("Auth: Passed");
      return super.handle(request);
    }
    return "Auth failed";
  }
}

class ValidationHandler extends Handler {
  handle(request: string): string | null {
    if (request.includes("valid")) {
      console.log("Validation: Passed");
      return super.handle(request);
    }
    return "Validation failed";
  }
}

// Usage
const auth = new AuthHandler();
const validation = new ValidationHandler();
auth.setNext(validation);

console.log(auth.handle("authenticated valid request"));
// Auth: Passed
// Validation: Passed
```

---

## Anti-Patterns

### Common Pattern Misuses

```
❌ Pattern for Pattern's Sake
→ Don't force patterns - use when beneficial
✅ Identify problem first, then apply pattern

❌ Singleton Everywhere
→ Creates hidden dependencies, hard to test
✅ Use dependency injection instead

❌ Over-Engineering with Patterns
→ Simple problem doesn't need complex pattern
✅ Start simple, refactor to pattern if needed

❌ Ignoring Context
→ Pattern appropriate in one language/context, not another
✅ Consider language idioms and ecosystem

❌ Mixing Patterns Poorly
→ Too many patterns create complexity
✅ Use minimal patterns to solve problem
```

---

## Pattern Selection Guide

| Problem | Pattern |
|---------|---------|
| Too many constructor params | Builder |
| Need single instance | Singleton (or DI) |
| Incompatible interfaces | Adapter |
| Add behavior dynamically | Decorator |
| Complex subsystem | Facade |
| Select algorithm at runtime | Strategy |
| Notify many objects | Observer |
| Undo/redo operations | Command |
| Shared algorithm, varying steps | Template Method |
| Chain of handlers | Chain of Responsibility |

---

## Best Practices

### Using Patterns Effectively

**Do's**:
- Understand the problem before choosing pattern
- Use patterns to communicate intent
- Refactor to patterns incrementally
- Combine patterns when appropriate
- Document why pattern was chosen

**Don'ts**:
- Don't memorize patterns without understanding
- Don't apply patterns prematurely
- Don't use patterns to show off knowledge
- Don't ignore language-specific idioms
- Don't overcomplicate simple problems

---

## Related Skills

- **engineering-code-quality**: Patterns improve quality
- **engineering-refactoring-patterns**: Refactoring to patterns
- **engineering-domain-driven-design**: DDD uses patterns
- **engineering-test-driven-development**: TDD with patterns
- **engineering-functional-programming**: FP alternatives to patterns

---

## References

- [Design Patterns: Elements of Reusable Object-Oriented Software (GoF)](https://www.amazon.com/Design-Patterns-Elements-Reusable-Object-Oriented/dp/0201633612)
- [Head First Design Patterns](https://www.amazon.com/Head-First-Design-Patterns-Brain-Friendly/dp/0596007124)
- [Refactoring to Patterns by Joshua Kerievsky](https://www.amazon.com/Refactoring-Patterns-Joshua-Kerievsky/dp/0321213351)
- [Refactoring.Guru - Design Patterns](https://refactoring.guru/design-patterns)
