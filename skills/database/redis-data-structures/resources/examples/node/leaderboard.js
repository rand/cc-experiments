/**
 * Redis Leaderboard Example
 *
 * Demonstrates leaderboard implementation using Redis Sorted Sets.
 */

const redis = require('redis');

class Leaderboard {
  /**
   * Initialize leaderboard.
   *
   * @param {Object} redisClient - Redis client
   * @param {string} name - Leaderboard name
   */
  constructor(redisClient, name = 'leaderboard') {
    this.redis = redisClient;
    this.key = `leaderboard:${name}`;
  }

  /**
   * Add or update player score.
   *
   * @param {string} playerId - Player identifier
   * @param {number} score - Player score
   */
  async addScore(playerId, score) {
    await this.redis.zAdd(this.key, { score, value: playerId });
    console.log(`[Leaderboard] Added ${playerId} with score ${score}`);
  }

  /**
   * Increment player score.
   *
   * @param {string} playerId - Player identifier
   * @param {number} increment - Score increment
   * @returns {number} New score
   */
  async incrementScore(playerId, increment) {
    const newScore = await this.redis.zIncrBy(this.key, increment, playerId);
    console.log(`[Leaderboard] Incremented ${playerId} by ${increment} (new: ${newScore})`);
    return parseFloat(newScore);
  }

  /**
   * Get player score.
   *
   * @param {string} playerId - Player identifier
   * @returns {number|null} Player score or null if not found
   */
  async getScore(playerId) {
    const score = await this.redis.zScore(this.key, playerId);
    return score ? parseFloat(score) : null;
  }

  /**
   * Get player rank (0-based, 0 is best).
   *
   * @param {string} playerId - Player identifier
   * @returns {number|null} Player rank or null if not found
   */
  async getRank(playerId) {
    const rank = await this.redis.zRevRank(this.key, playerId);
    return rank;
  }

  /**
   * Get top N players.
   *
   * @param {number} count - Number of players to retrieve
   * @returns {Array} Array of {player, score, rank}
   */
  async getTop(count = 10) {
    const results = await this.redis.zRangeWithScores(this.key, 0, count - 1, {
      REV: true
    });

    return results.map((item, index) => ({
      player: item.value,
      score: item.score,
      rank: index
    }));
  }

  /**
   * Get players around a specific player.
   *
   * @param {string} playerId - Player identifier
   * @param {number} range - Number of players above and below (default: 2)
   * @returns {Array} Array of {player, score, rank}
   */
  async getPlayersAround(playerId, range = 2) {
    const rank = await this.redis.zRevRank(this.key, playerId);

    if (rank === null) {
      return [];
    }

    const start = Math.max(0, rank - range);
    const end = rank + range;

    const results = await this.redis.zRangeWithScores(this.key, start, end, {
      REV: true
    });

    return results.map((item, index) => ({
      player: item.value,
      score: item.score,
      rank: start + index
    }));
  }

  /**
   * Get players in score range.
   *
   * @param {number} minScore - Minimum score
   * @param {number} maxScore - Maximum score
   * @returns {Array} Array of {player, score}
   */
  async getByScoreRange(minScore, maxScore) {
    const results = await this.redis.zRangeByScoreWithScores(
      this.key,
      minScore,
      maxScore
    );

    return results.map(item => ({
      player: item.value,
      score: item.score
    }));
  }

  /**
   * Remove player from leaderboard.
   *
   * @param {string} playerId - Player identifier
   */
  async removePlayer(playerId) {
    await this.redis.zRem(this.key, playerId);
    console.log(`[Leaderboard] Removed ${playerId}`);
  }

  /**
   * Get total player count.
   *
   * @returns {number} Number of players
   */
  async getPlayerCount() {
    return await this.redis.zCard(this.key);
  }

  /**
   * Clear leaderboard.
   */
  async clear() {
    await this.redis.del(this.key);
    console.log(`[Leaderboard] Cleared`);
  }
}

class TimeBasedLeaderboard extends Leaderboard {
  /**
   * Initialize time-based leaderboard (e.g., daily, weekly).
   *
   * @param {Object} redisClient - Redis client
   * @param {string} name - Leaderboard name
   * @param {string} period - Time period (daily, weekly, monthly)
   */
  constructor(redisClient, name = 'leaderboard', period = 'daily') {
    const timestamp = TimeBasedLeaderboard.getCurrentPeriod(period);
    super(redisClient, `${name}:${period}:${timestamp}`);
    this.period = period;
    this.baseName = name;
  }

  /**
   * Get current period timestamp.
   *
   * @param {string} period - Time period
   * @returns {string} Period identifier
   */
  static getCurrentPeriod(period) {
    const now = new Date();

    switch (period) {
      case 'daily':
        return now.toISOString().split('T')[0]; // YYYY-MM-DD
      case 'weekly': {
        const week = TimeBasedLeaderboard.getWeekNumber(now);
        return `${now.getFullYear()}-W${week}`;
      }
      case 'monthly':
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
      default:
        return now.toISOString().split('T')[0];
    }
  }

  /**
   * Get ISO week number.
   *
   * @param {Date} date - Date object
   * @returns {number} Week number
   */
  static getWeekNumber(date) {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  }

  /**
   * Set expiration for time-based leaderboard.
   *
   * @param {number} days - Days until expiration
   */
  async setExpiration(days) {
    await this.redis.expire(this.key, days * 24 * 60 * 60);
    console.log(`[Leaderboard] Set expiration: ${days} days`);
  }
}

// Demo functions

async function demoBasicLeaderboard() {
  console.log('\n' + '='.repeat(60));
  console.log('Basic Leaderboard Demo');
  console.log('='.repeat(60));

  const client = redis.createClient();
  await client.connect();

  const leaderboard = new Leaderboard(client, 'game1');

  // Add players
  console.log('\n--- Add Players ---');
  await leaderboard.addScore('player1', 1000);
  await leaderboard.addScore('player2', 1500);
  await leaderboard.addScore('player3', 800);
  await leaderboard.addScore('player4', 2000);
  await leaderboard.addScore('player5', 1200);

  // Get top 3
  console.log('\n--- Top 3 Players ---');
  const top3 = await leaderboard.getTop(3);
  top3.forEach(p => {
    console.log(`${p.rank + 1}. ${p.player}: ${p.score}`);
  });

  // Get player rank
  console.log('\n--- Player Ranks ---');
  for (const player of ['player1', 'player2', 'player3']) {
    const rank = await leaderboard.getRank(player);
    const score = await leaderboard.getScore(player);
    console.log(`${player}: Rank ${rank + 1}, Score ${score}`);
  }

  // Increment score
  console.log('\n--- Increment Score ---');
  await leaderboard.incrementScore('player3', 500);
  const newRank = await leaderboard.getRank('player3');
  const newScore = await leaderboard.getScore('player3');
  console.log(`player3: New Rank ${newRank + 1}, New Score ${newScore}`);

  // Get players around player3
  console.log('\n--- Players Around player3 ---');
  const around = await leaderboard.getPlayersAround('player3', 2);
  around.forEach(p => {
    const marker = p.player === 'player3' ? ' <--' : '';
    console.log(`${p.rank + 1}. ${p.player}: ${p.score}${marker}`);
  });

  // Total players
  console.log('\n--- Statistics ---');
  const count = await leaderboard.getPlayerCount();
  console.log(`Total players: ${count}`);

  // Cleanup
  await leaderboard.clear();
  await client.quit();
}

async function demoTimeBasedLeaderboard() {
  console.log('\n' + '='.repeat(60));
  console.log('Time-Based Leaderboard Demo');
  console.log('='.repeat(60));

  const client = redis.createClient();
  await client.connect();

  // Daily leaderboard
  console.log('\n--- Daily Leaderboard ---');
  const daily = new TimeBasedLeaderboard(client, 'game', 'daily');
  console.log(`Key: ${daily.key}`);

  await daily.addScore('player1', 500);
  await daily.addScore('player2', 750);
  await daily.addScore('player3', 600);

  const dailyTop = await daily.getTop(3);
  console.log('Daily Top 3:');
  dailyTop.forEach(p => {
    console.log(`  ${p.rank + 1}. ${p.player}: ${p.score}`);
  });

  // Set expiration (7 days)
  await daily.setExpiration(7);

  // Weekly leaderboard
  console.log('\n--- Weekly Leaderboard ---');
  const weekly = new TimeBasedLeaderboard(client, 'game', 'weekly');
  console.log(`Key: ${weekly.key}`);

  await weekly.addScore('player1', 5000);
  await weekly.addScore('player2', 7500);
  await weekly.addScore('player3', 6000);

  const weeklyTop = await weekly.getTop(3);
  console.log('Weekly Top 3:');
  weeklyTop.forEach(p => {
    console.log(`  ${p.rank + 1}. ${p.player}: ${p.score}`);
  });

  // Cleanup
  await daily.clear();
  await weekly.clear();
  await client.quit();
}

async function demoScoreRanges() {
  console.log('\n' + '='.repeat(60));
  console.log('Score Range Query Demo');
  console.log('='.repeat(60));

  const client = redis.createClient();
  await client.connect();

  const leaderboard = new Leaderboard(client, 'ranges');

  // Add players with various scores
  console.log('\n--- Add Players ---');
  for (let i = 1; i <= 20; i++) {
    await leaderboard.addScore(`player${i}`, i * 100);
  }

  // Get players in score range
  console.log('\n--- Players with Score 500-1000 ---');
  const range = await leaderboard.getByScoreRange(500, 1000);
  range.forEach(p => {
    console.log(`  ${p.player}: ${p.score}`);
  });

  // Get high scorers (> 1500)
  console.log('\n--- High Scorers (> 1500) ---');
  const highScorers = await leaderboard.getByScoreRange(1500, '+inf');
  console.log(`Found ${highScorers.length} high scorers`);
  highScorers.forEach(p => {
    console.log(`  ${p.player}: ${p.score}`);
  });

  // Cleanup
  await leaderboard.clear();
  await client.quit();
}

async function demoMultipleLeaderboards() {
  console.log('\n' + '='.repeat(60));
  console.log('Multiple Leaderboards Demo');
  console.log('='.repeat(60));

  const client = redis.createClient();
  await client.connect();

  // Different game modes
  const casual = new Leaderboard(client, 'casual');
  const ranked = new Leaderboard(client, 'ranked');
  const tournament = new Leaderboard(client, 'tournament');

  console.log('\n--- Add Scores to Different Leaderboards ---');

  // Casual mode
  await casual.addScore('player1', 100);
  await casual.addScore('player2', 150);

  // Ranked mode
  await ranked.addScore('player1', 2500);
  await ranked.addScore('player2', 2750);
  await ranked.addScore('player3', 2600);

  // Tournament mode
  await tournament.addScore('player1', 5000);
  await tournament.addScore('player2', 5500);
  await tournament.addScore('player3', 4800);
  await tournament.addScore('player4', 5200);

  // Show rankings in each mode
  console.log('\n--- Casual Rankings ---');
  const casualTop = await casual.getTop(5);
  casualTop.forEach(p => {
    console.log(`  ${p.rank + 1}. ${p.player}: ${p.score}`);
  });

  console.log('\n--- Ranked Rankings ---');
  const rankedTop = await ranked.getTop(5);
  rankedTop.forEach(p => {
    console.log(`  ${p.rank + 1}. ${p.player}: ${p.score}`);
  });

  console.log('\n--- Tournament Rankings ---');
  const tournamentTop = await tournament.getTop(5);
  tournamentTop.forEach(p => {
    console.log(`  ${p.rank + 1}. ${p.player}: ${p.score}`);
  });

  // Player stats across leaderboards
  console.log('\n--- player1 Stats Across All Modes ---');
  console.log(`  Casual: ${await casual.getScore('player1')} (Rank ${await casual.getRank('player1') + 1})`);
  console.log(`  Ranked: ${await ranked.getScore('player1')} (Rank ${await ranked.getRank('player1') + 1})`);
  console.log(`  Tournament: ${await tournament.getScore('player1')} (Rank ${await tournament.getRank('player1') + 1})`);

  // Cleanup
  await casual.clear();
  await ranked.clear();
  await tournament.clear();
  await client.quit();
}

// Main execution
async function main() {
  try {
    await demoBasicLeaderboard();
    await demoTimeBasedLeaderboard();
    await demoScoreRanges();
    await demoMultipleLeaderboards();

    console.log('\n' + '='.repeat(60));
    console.log('All demos completed!');
    console.log('='.repeat(60));
  } catch (error) {
    if (error.code === 'ECONNREFUSED') {
      console.error('Error: Cannot connect to Redis. Make sure Redis is running.');
      console.error('Start Redis with: redis-server');
    } else {
      console.error('Error:', error);
    }
  }
}

// Run if executed directly
if (require.main === module) {
  main();
}

module.exports = { Leaderboard, TimeBasedLeaderboard };
