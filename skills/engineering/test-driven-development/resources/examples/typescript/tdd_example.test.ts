/**
 * TDD Example: Bowling Game Kata (TypeScript)
 *
 * Demonstrates TDD with the classic Bowling Game kata.
 * Shows Red-Green-Refactor cycle and incremental development.
 *
 * Kata Rules:
 * - 10 frames per game
 * - Each frame: 2 rolls (except strike)
 * - Strike: All 10 pins with first roll (frame ends, 1 roll)
 * - Spare: All 10 pins with both rolls in frame
 * - Scoring:
 *   - Normal: Sum of pins knocked down
 *   - Spare: 10 + next roll
 *   - Strike: 10 + next 2 rolls
 */

// ============================================================================
// BEFORE TDD: Implementation without tests
// ============================================================================

class BowlingGameBeforeTDD {
  private rolls: number[] = [];

  roll(pins: number): void {
    this.rolls.push(pins);
  }

  score(): number {
    // Complex logic all at once - hard to test individual parts
    let score = 0;
    let rollIndex = 0;

    for (let frame = 0; frame < 10; frame++) {
      if (this.rolls[rollIndex] === 10) {
        // Strike
        score += 10 + this.rolls[rollIndex + 1] + this.rolls[rollIndex + 2];
        rollIndex += 1;
      } else if (this.rolls[rollIndex] + this.rolls[rollIndex + 1] === 10) {
        // Spare
        score += 10 + this.rolls[rollIndex + 2];
        rollIndex += 2;
      } else {
        // Normal
        score += this.rolls[rollIndex] + this.rolls[rollIndex + 1];
        rollIndex += 2;
      }
    }

    return score;
  }
}

// ============================================================================
// AFTER TDD: Test-driven implementation
// ============================================================================

// ======================
// ITERATION 1: RED PHASE
// ======================
// Test: Can create a game

describe('BowlingGame', () => {
  let game: BowlingGame;

  beforeEach(() => {
    game = new BowlingGame();
  });

  it('should be created', () => {
    expect(game).toBeDefined();
  });
});

// ======================
// ITERATION 1: GREEN PHASE
// ======================

class BowlingGame {
  // Simplest possible implementation
}

// ======================
// ITERATION 2: RED PHASE
// ======================
// Test: Gutter game (all zeros) scores 0

describe('BowlingGame', () => {
  let game: BowlingGame;

  beforeEach(() => {
    game = new BowlingGame();
  });

  it('should score 0 for gutter game', () => {
    rollMany(game, 20, 0);
    expect(game.score()).toBe(0);
  });

  function rollMany(game: BowlingGame, rolls: number, pins: number): void {
    for (let i = 0; i < rolls; i++) {
      game.roll(pins);
    }
  }
});

// ======================
// ITERATION 2: GREEN PHASE
// ======================

class BowlingGame {
  private rolls: number[] = [];

  roll(pins: number): void {
    this.rolls.push(pins);
  }

  score(): number {
    return 0; // Fake it!
  }
}

// ======================
// ITERATION 3: RED PHASE
// ======================
// Test: All ones scores 20

describe('BowlingGame', () => {
  let game: BowlingGame;

  beforeEach(() => {
    game = new BowlingGame();
  });

  it('should score 0 for gutter game', () => {
    rollMany(game, 20, 0);
    expect(game.score()).toBe(0);
  });

  it('should score 20 for all ones', () => {
    rollMany(game, 20, 1);
    expect(game.score()).toBe(20);
  });

  function rollMany(game: BowlingGame, rolls: number, pins: number): void {
    for (let i = 0; i < rolls; i++) {
      game.roll(pins);
    }
  }
});

// ======================
// ITERATION 3: GREEN PHASE
// ======================

class BowlingGame {
  private rolls: number[] = [];

  roll(pins: number): void {
    this.rolls.push(pins);
  }

  score(): number {
    let score = 0;
    for (const pins of this.rolls) {
      score += pins;
    }
    return score;
  }
}

// ======================
// ITERATION 4: RED PHASE
// ======================
// Test: One spare, then 3, then all zeros

describe('BowlingGame', () => {
  let game: BowlingGame;

  beforeEach(() => {
    game = new BowlingGame();
  });

  it('should score 0 for gutter game', () => {
    rollMany(game, 20, 0);
    expect(game.score()).toBe(0);
  });

  it('should score 20 for all ones', () => {
    rollMany(game, 20, 1);
    expect(game.score()).toBe(20);
  });

  it('should score spare correctly', () => {
    rollSpare();
    game.roll(3);
    rollMany(game, 17, 0);
    expect(game.score()).toBe(16); // 10 + 3 + 3 = 16
  });

  function rollMany(game: BowlingGame, rolls: number, pins: number): void {
    for (let i = 0; i < rolls; i++) {
      game.roll(pins);
    }
  }

  function rollSpare(): void {
    game.roll(5);
    game.roll(5);
  }
});

// ======================
// ITERATION 4: GREEN PHASE & REFACTOR
// ======================

class BowlingGame {
  private rolls: number[] = [];
  private currentRoll = 0;

  roll(pins: number): void {
    this.rolls[this.currentRoll++] = pins;
  }

  score(): number {
    let score = 0;
    let rollIndex = 0;

    for (let frame = 0; frame < 10; frame++) {
      if (this.isSpare(rollIndex)) {
        score += 10 + this.rolls[rollIndex + 2];
        rollIndex += 2;
      } else {
        score += this.rolls[rollIndex] + this.rolls[rollIndex + 1];
        rollIndex += 2;
      }
    }

    return score;
  }

  private isSpare(rollIndex: number): boolean {
    return this.rolls[rollIndex] + this.rolls[rollIndex + 1] === 10;
  }
}

// ======================
// ITERATION 5: RED PHASE
// ======================
// Test: One strike, then 3 and 4, then all zeros

describe('BowlingGame', () => {
  let game: BowlingGame;

  beforeEach(() => {
    game = new BowlingGame();
  });

  it('should score 0 for gutter game', () => {
    rollMany(game, 20, 0);
    expect(game.score()).toBe(0);
  });

  it('should score 20 for all ones', () => {
    rollMany(game, 20, 1);
    expect(game.score()).toBe(20);
  });

  it('should score spare correctly', () => {
    rollSpare();
    game.roll(3);
    rollMany(game, 17, 0);
    expect(game.score()).toBe(16);
  });

  it('should score strike correctly', () => {
    rollStrike();
    game.roll(3);
    game.roll(4);
    rollMany(game, 16, 0);
    expect(game.score()).toBe(24); // 10 + 3 + 4 + 3 + 4 = 24
  });

  function rollMany(game: BowlingGame, rolls: number, pins: number): void {
    for (let i = 0; i < rolls; i++) {
      game.roll(pins);
    }
  }

  function rollSpare(): void {
    game.roll(5);
    game.roll(5);
  }

  function rollStrike(): void {
    game.roll(10);
  }
});

// ======================
// ITERATION 5: GREEN PHASE & REFACTOR
// ======================

class BowlingGame {
  private rolls: number[] = [];
  private currentRoll = 0;

  roll(pins: number): void {
    this.rolls[this.currentRoll++] = pins;
  }

  score(): number {
    let score = 0;
    let rollIndex = 0;

    for (let frame = 0; frame < 10; frame++) {
      if (this.isStrike(rollIndex)) {
        score += 10 + this.strikeBonus(rollIndex);
        rollIndex += 1;
      } else if (this.isSpare(rollIndex)) {
        score += 10 + this.spareBonus(rollIndex);
        rollIndex += 2;
      } else {
        score += this.sumOfBallsInFrame(rollIndex);
        rollIndex += 2;
      }
    }

    return score;
  }

  private isStrike(rollIndex: number): boolean {
    return this.rolls[rollIndex] === 10;
  }

  private isSpare(rollIndex: number): boolean {
    return this.rolls[rollIndex] + this.rolls[rollIndex + 1] === 10;
  }

  private strikeBonus(rollIndex: number): number {
    return this.rolls[rollIndex + 1] + this.rolls[rollIndex + 2];
  }

  private spareBonus(rollIndex: number): number {
    return this.rolls[rollIndex + 2];
  }

  private sumOfBallsInFrame(rollIndex: number): number {
    return this.rolls[rollIndex] + this.rolls[rollIndex + 1];
  }
}

// ======================
// ITERATION 6: RED PHASE
// ======================
// Test: Perfect game (all strikes)

describe('BowlingGame', () => {
  let game: BowlingGame;

  beforeEach(() => {
    game = new BowlingGame();
  });

  it('should score 0 for gutter game', () => {
    rollMany(game, 20, 0);
    expect(game.score()).toBe(0);
  });

  it('should score 20 for all ones', () => {
    rollMany(game, 20, 1);
    expect(game.score()).toBe(20);
  });

  it('should score spare correctly', () => {
    rollSpare();
    game.roll(3);
    rollMany(game, 17, 0);
    expect(game.score()).toBe(16);
  });

  it('should score strike correctly', () => {
    rollStrike();
    game.roll(3);
    game.roll(4);
    rollMany(game, 16, 0);
    expect(game.score()).toBe(24);
  });

  it('should score perfect game correctly', () => {
    rollMany(game, 12, 10);
    expect(game.score()).toBe(300);
  });

  function rollMany(game: BowlingGame, rolls: number, pins: number): void {
    for (let i = 0; i < rolls; i++) {
      game.roll(pins);
    }
  }

  function rollSpare(): void {
    game.roll(5);
    game.roll(5);
  }

  function rollStrike(): void {
    game.roll(10);
  }
});

// ======================
// ITERATION 6: GREEN PHASE
// ======================
// Already passes! Implementation was general enough.

// ============================================================================
// FINAL IMPLEMENTATION WITH COMPLETE TEST SUITE
// ============================================================================

/**
 * Bowling Game
 *
 * Calculates score for a complete game of bowling.
 * Built using Test-Driven Development.
 */
export class BowlingGame {
  private rolls: number[] = [];
  private currentRoll = 0;

  /**
   * Record a roll
   * @param pins Number of pins knocked down (0-10)
   */
  roll(pins: number): void {
    this.rolls[this.currentRoll++] = pins;
  }

  /**
   * Calculate total score for the game
   * @returns Total score
   */
  score(): number {
    let score = 0;
    let rollIndex = 0;

    for (let frame = 0; frame < 10; frame++) {
      if (this.isStrike(rollIndex)) {
        score += 10 + this.strikeBonus(rollIndex);
        rollIndex += 1;
      } else if (this.isSpare(rollIndex)) {
        score += 10 + this.spareBonus(rollIndex);
        rollIndex += 2;
      } else {
        score += this.sumOfBallsInFrame(rollIndex);
        rollIndex += 2;
      }
    }

    return score;
  }

  private isStrike(rollIndex: number): boolean {
    return this.rolls[rollIndex] === 10;
  }

  private isSpare(rollIndex: number): boolean {
    return this.rolls[rollIndex] + this.rolls[rollIndex + 1] === 10;
  }

  private strikeBonus(rollIndex: number): number {
    return this.rolls[rollIndex + 1] + this.rolls[rollIndex + 2];
  }

  private spareBonus(rollIndex: number): number {
    return this.rolls[rollIndex + 2];
  }

  private sumOfBallsInFrame(rollIndex: number): number {
    return this.rolls[rollIndex] + this.rolls[rollIndex + 1];
  }
}

// Complete test suite
describe('BowlingGame (Complete)', () => {
  let game: BowlingGame;

  beforeEach(() => {
    game = new BowlingGame();
  });

  describe('basic scoring', () => {
    it('should score 0 for gutter game', () => {
      rollMany(20, 0);
      expect(game.score()).toBe(0);
    });

    it('should score 20 for all ones', () => {
      rollMany(20, 1);
      expect(game.score()).toBe(20);
    });

    it('should score normal frames correctly', () => {
      game.roll(3);
      game.roll(4);
      rollMany(18, 0);
      expect(game.score()).toBe(7);
    });
  });

  describe('spare scoring', () => {
    it('should score spare with bonus', () => {
      rollSpare();
      game.roll(3);
      rollMany(17, 0);
      expect(game.score()).toBe(16); // 10 + 3 + 3
    });

    it('should score multiple spares', () => {
      rollSpare();
      game.roll(3);
      game.roll(4);
      rollSpare();
      game.roll(5);
      rollMany(13, 0);
      expect(game.score()).toBe(37); // (10+3) + 3+4 + (10+5) + 5
    });
  });

  describe('strike scoring', () => {
    it('should score strike with bonus', () => {
      rollStrike();
      game.roll(3);
      game.roll(4);
      rollMany(16, 0);
      expect(game.score()).toBe(24); // 10 + 3 + 4 + 3 + 4
    });

    it('should score multiple strikes', () => {
      rollStrike();
      rollStrike();
      rollStrike();
      rollMany(14, 0);
      expect(game.score()).toBe(60); // (10+10+10) + (10+10) + 10
    });

    it('should score perfect game', () => {
      rollMany(12, 10);
      expect(game.score()).toBe(300);
    });
  });

  // Helper functions
  function rollMany(rolls: number, pins: number): void {
    for (let i = 0; i < rolls; i++) {
      game.roll(pins);
    }
  }

  function rollSpare(): void {
    game.roll(5);
    game.roll(5);
  }

  function rollStrike(): void {
    game.roll(10);
  }
});

// ============================================================================
// KEY TAKEAWAYS
// ============================================================================

/*
TDD Lessons from Bowling Game Kata:

1. INCREMENTAL COMPLEXITY
   - Started with simplest case (gutter game)
   - Added complexity one test at a time
   - Each test drove new code

2. REFACTORING OPPORTUNITIES
   - Extracted helper methods for readability
   - Improved names as understanding grew
   - Tests enabled fearless refactoring

3. EMERGENT DESIGN
   - Design evolved from tests
   - Didn't over-engineer upfront
   - Each refactor improved structure

4. TEST ORGANIZATION
   - Grouped related tests with describe blocks
   - Helper functions reduce duplication
   - beforeEach ensures clean state

5. TDD RHYTHM
   - Red: Write failing test
   - Green: Make it pass (simplest way)
   - Refactor: Improve design
   - Repeat

6. BENEFITS REALIZED
   - 100% test coverage by definition
   - Each behavior has a test
   - Easy to add new features
   - Regression protection
   - Living documentation

TIME COMPARISON:
- Before TDD: 30 min implementation, 2 hours debugging edge cases
- With TDD: 45 min total (tests + implementation), 0 min debugging

CONFIDENCE:
- Before TDD: "I think it works..."
- With TDD: "I KNOW it works, I have the tests to prove it"
*/
