/// TDD Example: Stack Implementation in Rust
///
/// Demonstrates Test-Driven Development in Rust with a classic
/// Stack data structure. Shows how TDD works with Rust's type system
/// and ownership model.
///
/// This example shows:
/// - Red-Green-Refactor cycle in Rust
/// - Using Result<T, E> for error handling
/// - Property-based testing (with proptest)
/// - Rust-specific TDD patterns

// ============================================================================
// BEFORE TDD: Implementation without tests
// ============================================================================

#[allow(dead_code)]
struct StackBeforeTDD<T> {
    items: Vec<T>,
    capacity: usize,
}

#[allow(dead_code)]
impl<T> StackBeforeTDD<T> {
    fn new(capacity: usize) -> Self {
        Self {
            items: Vec::with_capacity(capacity),
            capacity,
        }
    }

    fn push(&mut self, item: T) -> Result<(), String> {
        if self.items.len() >= self.capacity {
            return Err("Stack overflow".to_string());
        }
        self.items.push(item);
        Ok(())
    }

    fn pop(&mut self) -> Option<T> {
        self.items.pop()
    }

    fn peek(&self) -> Option<&T> {
        self.items.last()
    }
}

// ============================================================================
// AFTER TDD: Test-driven implementation
// ============================================================================

/// Stack error types
#[derive(Debug, PartialEq)]
pub enum StackError {
    Overflow,
    Underflow,
}

// ======================
// ITERATION 1: RED PHASE
// ======================
// Test: Can create an empty stack

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_stack_is_empty() {
        let stack: Stack<i32> = Stack::new(10);
        assert_eq!(stack.size(), 0);
        assert!(stack.is_empty());
    }
}

// ======================
// ITERATION 1: GREEN PHASE
// ======================

pub struct Stack<T> {
    items: Vec<T>,
    capacity: usize,
}

impl<T> Stack<T> {
    pub fn new(capacity: usize) -> Self {
        Self {
            items: Vec::with_capacity(capacity),
            capacity,
        }
    }

    pub fn size(&self) -> usize {
        0 // Fake it!
    }

    pub fn is_empty(&self) -> bool {
        true // Fake it!
    }
}

// ======================
// ITERATION 1: REFACTOR
// ======================

impl<T> Stack<T> {
    pub fn new(capacity: usize) -> Self {
        Self {
            items: Vec::with_capacity(capacity),
            capacity,
        }
    }

    pub fn size(&self) -> usize {
        self.items.len()
    }

    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }
}

// ======================
// ITERATION 2: RED PHASE
// ======================
// Test: Can push items onto stack

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_stack_is_empty() {
        let stack: Stack<i32> = Stack::new(10);
        assert_eq!(stack.size(), 0);
        assert!(stack.is_empty());
    }

    #[test]
    fn test_push_increases_size() {
        let mut stack = Stack::new(10);
        assert!(stack.push(1).is_ok());
        assert_eq!(stack.size(), 1);
        assert!(!stack.is_empty());
    }

    #[test]
    fn test_push_multiple_items() {
        let mut stack = Stack::new(10);
        assert!(stack.push(1).is_ok());
        assert!(stack.push(2).is_ok());
        assert!(stack.push(3).is_ok());
        assert_eq!(stack.size(), 3);
    }
}

// ======================
// ITERATION 2: GREEN PHASE
// ======================

impl<T> Stack<T> {
    pub fn push(&mut self, item: T) -> Result<(), StackError> {
        self.items.push(item);
        Ok(())
    }
}

// ======================
// ITERATION 3: RED PHASE
// ======================
// Test: Can pop items from stack

#[cfg(test)]
mod tests {
    use super::*;

    // ... previous tests ...

    #[test]
    fn test_pop_returns_last_item() {
        let mut stack = Stack::new(10);
        stack.push(1).unwrap();
        stack.push(2).unwrap();

        assert_eq!(stack.pop(), Ok(2));
        assert_eq!(stack.size(), 1);
    }

    #[test]
    fn test_pop_empty_stack_returns_error() {
        let mut stack: Stack<i32> = Stack::new(10);
        assert_eq!(stack.pop(), Err(StackError::Underflow));
    }

    #[test]
    fn test_lifo_order() {
        let mut stack = Stack::new(10);
        stack.push(1).unwrap();
        stack.push(2).unwrap();
        stack.push(3).unwrap();

        assert_eq!(stack.pop(), Ok(3));
        assert_eq!(stack.pop(), Ok(2));
        assert_eq!(stack.pop(), Ok(1));
        assert_eq!(stack.pop(), Err(StackError::Underflow));
    }
}

// ======================
// ITERATION 3: GREEN PHASE
// ======================

impl<T> Stack<T> {
    pub fn pop(&mut self) -> Result<T, StackError> {
        self.items.pop().ok_or(StackError::Underflow)
    }
}

// ======================
// ITERATION 4: RED PHASE
// ======================
// Test: Peek returns reference to top without removing

#[cfg(test)]
mod tests {
    use super::*;

    // ... previous tests ...

    #[test]
    fn test_peek_returns_reference() {
        let mut stack = Stack::new(10);
        stack.push(1).unwrap();
        stack.push(2).unwrap();

        assert_eq!(stack.peek(), Some(&2));
        assert_eq!(stack.size(), 2); // Size unchanged
    }

    #[test]
    fn test_peek_empty_stack_returns_none() {
        let stack: Stack<i32> = Stack::new(10);
        assert_eq!(stack.peek(), None);
    }
}

// ======================
// ITERATION 4: GREEN PHASE
// ======================

impl<T> Stack<T> {
    pub fn peek(&self) -> Option<&T> {
        self.items.last()
    }
}

// ======================
// ITERATION 5: RED PHASE
// ======================
// Test: Stack respects capacity limit

#[cfg(test)]
mod tests {
    use super::*;

    // ... previous tests ...

    #[test]
    fn test_push_respects_capacity() {
        let mut stack = Stack::new(2);
        assert!(stack.push(1).is_ok());
        assert!(stack.push(2).is_ok());
        assert_eq!(stack.push(3), Err(StackError::Overflow));
        assert_eq!(stack.size(), 2);
    }

    #[test]
    fn test_capacity_is_enforced() {
        let mut stack = Stack::new(3);
        for i in 0..3 {
            assert!(stack.push(i).is_ok());
        }
        assert_eq!(stack.push(999), Err(StackError::Overflow));
    }
}

// ======================
// ITERATION 5: GREEN PHASE & REFACTOR
// ======================

impl<T> Stack<T> {
    pub fn push(&mut self, item: T) -> Result<(), StackError> {
        if self.is_full() {
            return Err(StackError::Overflow);
        }
        self.items.push(item);
        Ok(())
    }

    pub fn is_full(&self) -> bool {
        self.items.len() >= self.capacity
    }

    pub fn capacity(&self) -> usize {
        self.capacity
    }
}

// ============================================================================
// FINAL IMPLEMENTATION WITH COMPLETE TEST SUITE
// ============================================================================

/// A bounded stack data structure
///
/// Generic stack with fixed capacity, built using TDD.
/// Provides LIFO (Last In, First Out) semantics.
///
/// # Examples
///
/// ```
/// use stack::Stack;
///
/// let mut stack = Stack::new(10);
/// stack.push(1).unwrap();
/// stack.push(2).unwrap();
/// assert_eq!(stack.pop(), Ok(2));
/// ```
pub struct Stack<T> {
    items: Vec<T>,
    capacity: usize,
}

impl<T> Stack<T> {
    /// Create a new stack with the given capacity
    pub fn new(capacity: usize) -> Self {
        Self {
            items: Vec::with_capacity(capacity),
            capacity,
        }
    }

    /// Push an item onto the stack
    ///
    /// # Errors
    ///
    /// Returns `StackError::Overflow` if stack is at capacity
    pub fn push(&mut self, item: T) -> Result<(), StackError> {
        if self.is_full() {
            return Err(StackError::Overflow);
        }
        self.items.push(item);
        Ok(())
    }

    /// Pop an item from the stack
    ///
    /// # Errors
    ///
    /// Returns `StackError::Underflow` if stack is empty
    pub fn pop(&mut self) -> Result<T, StackError> {
        self.items.pop().ok_or(StackError::Underflow)
    }

    /// Peek at the top item without removing it
    pub fn peek(&self) -> Option<&T> {
        self.items.last()
    }

    /// Get the current size of the stack
    pub fn size(&self) -> usize {
        self.items.len()
    }

    /// Check if the stack is empty
    pub fn is_empty(&self) -> bool {
        self.items.is_empty()
    }

    /// Check if the stack is full
    pub fn is_full(&self) -> bool {
        self.items.len() >= self.capacity
    }

    /// Get the capacity of the stack
    pub fn capacity(&self) -> usize {
        self.capacity
    }

    /// Clear all items from the stack
    pub fn clear(&mut self) {
        self.items.clear();
    }
}

// Complete test suite
#[cfg(test)]
mod complete_tests {
    use super::*;

    mod creation {
        use super::*;

        #[test]
        fn new_stack_is_empty() {
            let stack: Stack<i32> = Stack::new(10);
            assert_eq!(stack.size(), 0);
            assert!(stack.is_empty());
            assert!(!stack.is_full());
        }

        #[test]
        fn new_stack_has_capacity() {
            let stack: Stack<i32> = Stack::new(5);
            assert_eq!(stack.capacity(), 5);
        }
    }

    mod pushing {
        use super::*;

        #[test]
        fn push_increases_size() {
            let mut stack = Stack::new(10);
            assert!(stack.push(1).is_ok());
            assert_eq!(stack.size(), 1);
        }

        #[test]
        fn push_multiple_items() {
            let mut stack = Stack::new(10);
            for i in 0..5 {
                assert!(stack.push(i).is_ok());
            }
            assert_eq!(stack.size(), 5);
        }

        #[test]
        fn push_respects_capacity() {
            let mut stack = Stack::new(2);
            assert!(stack.push(1).is_ok());
            assert!(stack.push(2).is_ok());
            assert_eq!(stack.push(3), Err(StackError::Overflow));
        }

        #[test]
        fn push_to_full_stack_fails() {
            let mut stack = Stack::new(1);
            stack.push(1).unwrap();
            assert!(stack.is_full());
            assert_eq!(stack.push(2), Err(StackError::Overflow));
        }
    }

    mod popping {
        use super::*;

        #[test]
        fn pop_returns_last_item() {
            let mut stack = Stack::new(10);
            stack.push(1).unwrap();
            stack.push(2).unwrap();
            assert_eq!(stack.pop(), Ok(2));
        }

        #[test]
        fn pop_decreases_size() {
            let mut stack = Stack::new(10);
            stack.push(1).unwrap();
            stack.push(2).unwrap();
            stack.pop().unwrap();
            assert_eq!(stack.size(), 1);
        }

        #[test]
        fn pop_empty_stack_returns_error() {
            let mut stack: Stack<i32> = Stack::new(10);
            assert_eq!(stack.pop(), Err(StackError::Underflow));
        }

        #[test]
        fn lifo_order() {
            let mut stack = Stack::new(10);
            stack.push(1).unwrap();
            stack.push(2).unwrap();
            stack.push(3).unwrap();

            assert_eq!(stack.pop(), Ok(3));
            assert_eq!(stack.pop(), Ok(2));
            assert_eq!(stack.pop(), Ok(1));
        }
    }

    mod peeking {
        use super::*;

        #[test]
        fn peek_returns_reference() {
            let mut stack = Stack::new(10);
            stack.push(42).unwrap();
            assert_eq!(stack.peek(), Some(&42));
        }

        #[test]
        fn peek_does_not_remove_item() {
            let mut stack = Stack::new(10);
            stack.push(1).unwrap();
            stack.peek();
            assert_eq!(stack.size(), 1);
        }

        #[test]
        fn peek_empty_stack_returns_none() {
            let stack: Stack<i32> = Stack::new(10);
            assert_eq!(stack.peek(), None);
        }
    }

    mod clearing {
        use super::*;

        #[test]
        fn clear_empties_stack() {
            let mut stack = Stack::new(10);
            stack.push(1).unwrap();
            stack.push(2).unwrap();
            stack.clear();
            assert!(stack.is_empty());
            assert_eq!(stack.size(), 0);
        }
    }

    mod with_strings {
        use super::*;

        #[test]
        fn works_with_strings() {
            let mut stack = Stack::new(3);
            stack.push("hello".to_string()).unwrap();
            stack.push("world".to_string()).unwrap();
            assert_eq!(stack.pop(), Ok("world".to_string()));
            assert_eq!(stack.pop(), Ok("hello".to_string()));
        }
    }

    // Property-based tests (requires proptest crate)
    // Uncomment to use:
    //
    // use proptest::prelude::*;
    //
    // proptest! {
    //     #[test]
    //     fn push_pop_roundtrip(value: i32) {
    //         let mut stack = Stack::new(1);
    //         stack.push(value).unwrap();
    //         assert_eq!(stack.pop(), Ok(value));
    //     }
    //
    //     #[test]
    //     fn size_never_exceeds_capacity(values in prop::collection::vec(any::<i32>(), 0..100)) {
    //         let mut stack = Stack::new(10);
    //         for value in values {
    //             let _ = stack.push(value);
    //             assert!(stack.size() <= stack.capacity());
    //         }
    //     }
    // }
}

// ============================================================================
// KEY TAKEAWAYS
// ============================================================================

/*
TDD in Rust - Lessons Learned:

1. TYPE SYSTEM AS ALLY
   - Result<T, E> makes error handling explicit
   - Tests caught missing error cases early
   - Compiler ensures exhaustive matching

2. OWNERSHIP AND BORROWING
   - peek() returns &T, pop() returns T
   - Design emerged from thinking about ownership
   - Tests verify behavior, compiler verifies safety

3. RED-GREEN-REFACTOR IN RUST
   - Start with failing test
   - Make it compile (may need to add types)
   - Make it pass
   - Refactor (compiler ensures safety)

4. TESTING PATTERNS
   - Organize tests in nested modules
   - Use Result assertions (is_ok, is_err)
   - Test with different types (generics)
   - Property-based testing for invariants

5. TDD BENEFITS IN RUST
   - API design: Tests drove generic interface
   - Error handling: Forced to think about edge cases
   - Documentation: Tests as examples
   - Confidence: Tests + compiler = high confidence

6. RUST-SPECIFIC CONSIDERATIONS
   - Test modules with #[cfg(test)]
   - Use assert_eq! for better error messages
   - Consider property-based tests for invariants
   - Test with different types to verify generics

DEVELOPMENT TIMELINE:
1. Empty stack test → 2 min
2. Push functionality → 5 min
3. Pop functionality → 5 min
4. Peek functionality → 3 min
5. Capacity enforcement → 5 min
6. Refactoring → 5 min
Total: ~25 minutes for fully tested, production-ready stack

WITHOUT TDD:
- Write full implementation → 15 min
- Discover bugs in integration → 30 min
- Write tests retroactively → 20 min
- Fix bugs found by tests → 15 min
Total: ~80 minutes, less confidence

TDD WINS:
- Less total time
- Higher confidence
- Better design
- No retroactive test writing
*/
