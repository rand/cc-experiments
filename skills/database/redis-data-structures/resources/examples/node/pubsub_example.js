/**
 * Redis Pub/Sub Example
 *
 * Demonstrates publish/subscribe messaging patterns with Redis.
 */

const redis = require('redis');

class PubSubManager {
  /**
   * Initialize Pub/Sub manager.
   */
  constructor() {
    this.publisher = null;
    this.subscriber = null;
    this.handlers = new Map();
  }

  /**
   * Connect publisher and subscriber clients.
   */
  async connect() {
    this.publisher = redis.createClient();
    this.subscriber = redis.createClient();

    await this.publisher.connect();
    await this.subscriber.connect();

    console.log('[PubSub] Connected');
  }

  /**
   * Publish message to channel.
   *
   * @param {string} channel - Channel name
   * @param {*} message - Message to publish (will be JSON encoded)
   * @returns {number} Number of subscribers that received the message
   */
  async publish(channel, message) {
    const data = typeof message === 'string' ? message : JSON.stringify(message);
    const count = await this.publisher.publish(channel, data);
    console.log(`[Publisher] Published to ${channel}: ${count} subscribers`);
    return count;
  }

  /**
   * Subscribe to channel.
   *
   * @param {string} channel - Channel name
   * @param {Function} handler - Message handler function
   */
  async subscribe(channel, handler) {
    await this.subscriber.subscribe(channel, (message, subscribedChannel) => {
      console.log(`[Subscriber] Received on ${subscribedChannel}`);

      // Try to parse JSON, fallback to string
      let parsedMessage = message;
      try {
        parsedMessage = JSON.parse(message);
      } catch (e) {
        // Keep as string
      }

      handler(parsedMessage, subscribedChannel);
    });

    this.handlers.set(channel, handler);
    console.log(`[Subscriber] Subscribed to ${channel}`);
  }

  /**
   * Subscribe to pattern.
   *
   * @param {string} pattern - Pattern to match (e.g., "chat:*")
   * @param {Function} handler - Message handler function
   */
  async pSubscribe(pattern, handler) {
    await this.subscriber.pSubscribe(pattern, (message, channel) => {
      console.log(`[Subscriber] Received on ${channel} (pattern: ${pattern})`);

      let parsedMessage = message;
      try {
        parsedMessage = JSON.parse(message);
      } catch (e) {
        // Keep as string
      }

      handler(parsedMessage, channel);
    });

    this.handlers.set(pattern, handler);
    console.log(`[Subscriber] Subscribed to pattern ${pattern}`);
  }

  /**
   * Unsubscribe from channel.
   *
   * @param {string} channel - Channel name
   */
  async unsubscribe(channel) {
    await this.subscriber.unsubscribe(channel);
    this.handlers.delete(channel);
    console.log(`[Subscriber] Unsubscribed from ${channel}`);
  }

  /**
   * Unsubscribe from pattern.
   *
   * @param {string} pattern - Pattern to unsubscribe
   */
  async pUnsubscribe(pattern) {
    await this.subscriber.pUnsubscribe(pattern);
    this.handlers.delete(pattern);
    console.log(`[Subscriber] Unsubscribed from pattern ${pattern}`);
  }

  /**
   * Get list of active channels.
   *
   * @param {string} pattern - Optional pattern to filter
   * @returns {Array} List of channels
   */
  async getChannels(pattern = '*') {
    return await this.publisher.pubSubChannels(pattern);
  }

  /**
   * Get number of subscribers for channel.
   *
   * @param {string} channel - Channel name
   * @returns {number} Number of subscribers
   */
  async getSubscriberCount(channel) {
    const counts = await this.publisher.pubSubNumSub(channel);
    return counts[channel] || 0;
  }

  /**
   * Disconnect all clients.
   */
  async disconnect() {
    if (this.subscriber) {
      await this.subscriber.quit();
    }
    if (this.publisher) {
      await this.publisher.quit();
    }
    console.log('[PubSub] Disconnected');
  }
}

class ChatRoom {
  /**
   * Initialize chat room.
   *
   * @param {PubSubManager} pubsub - PubSubManager instance
   * @param {string} roomId - Room identifier
   */
  constructor(pubsub, roomId) {
    this.pubsub = pubsub;
    this.roomId = roomId;
    this.channel = `chat:room:${roomId}`;
  }

  /**
   * Send message to room.
   *
   * @param {string} userId - User identifier
   * @param {string} message - Message text
   */
  async sendMessage(userId, message) {
    await this.pubsub.publish(this.channel, {
      type: 'message',
      userId,
      message,
      timestamp: Date.now()
    });
  }

  /**
   * User joins room.
   *
   * @param {string} userId - User identifier
   * @param {Function} messageHandler - Handler for incoming messages
   */
  async join(userId, messageHandler) {
    // Subscribe to room
    await this.pubsub.subscribe(this.channel, messageHandler);

    // Announce join
    await this.pubsub.publish(this.channel, {
      type: 'join',
      userId,
      timestamp: Date.now()
    });

    console.log(`[ChatRoom] ${userId} joined ${this.roomId}`);
  }

  /**
   * User leaves room.
   *
   * @param {string} userId - User identifier
   */
  async leave(userId) {
    // Announce leave
    await this.pubsub.publish(this.channel, {
      type: 'leave',
      userId,
      timestamp: Date.now()
    });

    // Unsubscribe
    await this.pubsub.unsubscribe(this.channel);

    console.log(`[ChatRoom] ${userId} left ${this.roomId}`);
  }
}

class NotificationSystem {
  /**
   * Initialize notification system.
   *
   * @param {PubSubManager} pubsub - PubSubManager instance
   */
  constructor(pubsub) {
    this.pubsub = pubsub;
  }

  /**
   * Send notification.
   *
   * @param {string} type - Notification type
   * @param {string} userId - Target user ID
   * @param {Object} data - Notification data
   */
  async sendNotification(type, userId, data) {
    const channel = `notifications:user:${userId}`;
    await this.pubsub.publish(channel, {
      type,
      data,
      timestamp: Date.now()
    });
  }

  /**
   * Subscribe to user notifications.
   *
   * @param {string} userId - User identifier
   * @param {Function} handler - Notification handler
   */
  async subscribeUser(userId, handler) {
    const channel = `notifications:user:${userId}`;
    await this.pubsub.subscribe(channel, handler);
  }

  /**
   * Broadcast notification to all users.
   *
   * @param {string} type - Notification type
   * @param {Object} data - Notification data
   */
  async broadcast(type, data) {
    await this.pubsub.publish('notifications:broadcast', {
      type,
      data,
      timestamp: Date.now()
    });
  }

  /**
   * Subscribe to broadcast notifications.
   *
   * @param {Function} handler - Notification handler
   */
  async subscribeBroadcast(handler) {
    await this.pubsub.subscribe('notifications:broadcast', handler);
  }
}

// Demo functions

async function demoBasicPubSub() {
  console.log('\n' + '='.repeat(60));
  console.log('Basic Pub/Sub Demo');
  console.log('='.repeat(60));

  const pubsub = new PubSubManager();
  await pubsub.connect();

  // Subscribe to channel
  console.log('\n--- Subscribe to Channel ---');
  await pubsub.subscribe('news', (message) => {
    console.log(`  [Handler] Received: ${message}`);
  });

  // Publish messages
  console.log('\n--- Publish Messages ---');
  await new Promise(resolve => setTimeout(resolve, 100)); // Wait for subscription

  await pubsub.publish('news', 'Breaking news: Redis is awesome!');
  await pubsub.publish('news', 'Update: Pub/Sub working perfectly');

  await new Promise(resolve => setTimeout(resolve, 100)); // Wait for messages

  // Unsubscribe
  console.log('\n--- Unsubscribe ---');
  await pubsub.unsubscribe('news');

  await pubsub.disconnect();
}

async function demoPatternSubscription() {
  console.log('\n' + '='.repeat(60));
  console.log('Pattern Subscription Demo');
  console.log('='.repeat(60));

  const pubsub = new PubSubManager();
  await pubsub.connect();

  // Subscribe to pattern
  console.log('\n--- Subscribe to Pattern "user:*" ---');
  await pubsub.pSubscribe('user:*', (message, channel) => {
    console.log(`  [Handler] Channel: ${channel}, Message: ${JSON.stringify(message)}`);
  });

  await new Promise(resolve => setTimeout(resolve, 100));

  // Publish to matching channels
  console.log('\n--- Publish to Matching Channels ---');
  await pubsub.publish('user:1000', { action: 'login' });
  await pubsub.publish('user:1001', { action: 'logout' });
  await pubsub.publish('user:1002', { action: 'update_profile' });

  await new Promise(resolve => setTimeout(resolve, 100));

  await pubsub.pUnsubscribe('user:*');
  await pubsub.disconnect();
}

async function demoChatRoom() {
  console.log('\n' + '='.repeat(60));
  console.log('Chat Room Demo');
  console.log('='.repeat(60));

  const pubsub = new PubSubManager();
  await pubsub.connect();

  const room = new ChatRoom(pubsub, 'general');

  // User joins and sets up message handler
  console.log('\n--- User Joins Room ---');
  await room.join('alice', (message) => {
    if (message.type === 'message') {
      console.log(`  [Chat] ${message.userId}: ${message.message}`);
    } else if (message.type === 'join') {
      console.log(`  [Chat] ${message.userId} joined the room`);
    } else if (message.type === 'leave') {
      console.log(`  [Chat] ${message.userId} left the room`);
    }
  });

  await new Promise(resolve => setTimeout(resolve, 100));

  // Send messages
  console.log('\n--- Send Messages ---');
  await room.sendMessage('alice', 'Hello everyone!');
  await room.sendMessage('alice', 'How is everyone doing?');

  await new Promise(resolve => setTimeout(resolve, 100));

  // Leave room
  console.log('\n--- User Leaves Room ---');
  await room.leave('alice');

  await new Promise(resolve => setTimeout(resolve, 100));

  await pubsub.disconnect();
}

async function demoNotificationSystem() {
  console.log('\n' + '='.repeat(60));
  console.log('Notification System Demo');
  console.log('='.repeat(60));

  const pubsub = new PubSubManager();
  await pubsub.connect();

  const notifications = new NotificationSystem(pubsub);

  // Subscribe to user notifications
  console.log('\n--- Subscribe to User Notifications ---');
  await notifications.subscribeUser('user:1000', (notification) => {
    console.log(`  [Notification] ${notification.type}:`, notification.data);
  });

  // Subscribe to broadcasts
  await notifications.subscribeBroadcast((notification) => {
    console.log(`  [Broadcast] ${notification.type}:`, notification.data);
  });

  await new Promise(resolve => setTimeout(resolve, 100));

  // Send notifications
  console.log('\n--- Send Notifications ---');
  await notifications.sendNotification('order', 'user:1000', {
    orderId: '12345',
    status: 'shipped'
  });

  await notifications.sendNotification('message', 'user:1000', {
    from: 'user:1001',
    text: 'Hello!'
  });

  // Broadcast
  console.log('\n--- Send Broadcast ---');
  await notifications.broadcast('maintenance', {
    message: 'System maintenance in 1 hour',
    duration: '30 minutes'
  });

  await new Promise(resolve => setTimeout(resolve, 100));

  await pubsub.disconnect();
}

async function demoMultipleSubscribers() {
  console.log('\n' + '='.repeat(60));
  console.log('Multiple Subscribers Demo');
  console.log('='.repeat(60));

  // Create multiple pub/sub instances (simulating different services)
  const pubsub1 = new PubSubManager();
  const pubsub2 = new PubSubManager();
  const pubsub3 = new PubSubManager();

  await pubsub1.connect();
  await pubsub2.connect();
  await pubsub3.connect();

  const channel = 'events:global';

  // Subscribe all
  console.log('\n--- Multiple Subscribers ---');
  await pubsub1.subscribe(channel, (message) => {
    console.log(`  [Service 1] Received: ${JSON.stringify(message)}`);
  });

  await pubsub2.subscribe(channel, (message) => {
    console.log(`  [Service 2] Received: ${JSON.stringify(message)}`);
  });

  await pubsub3.subscribe(channel, (message) => {
    console.log(`  [Service 3] Received: ${JSON.stringify(message)}`);
  });

  await new Promise(resolve => setTimeout(resolve, 100));

  // Check subscriber count
  console.log('\n--- Subscriber Count ---');
  const count = await pubsub1.getSubscriberCount(channel);
  console.log(`  Subscribers on ${channel}: ${count}`);

  // Publish event
  console.log('\n--- Publish Event ---');
  await pubsub1.publish(channel, {
    event: 'user_signup',
    userId: 'user:5000'
  });

  await new Promise(resolve => setTimeout(resolve, 100));

  // Disconnect all
  await pubsub1.disconnect();
  await pubsub2.disconnect();
  await pubsub3.disconnect();
}

async function demoCacheInvalidation() {
  console.log('\n' + '='.repeat(60));
  console.log('Cache Invalidation Demo');
  console.log('='.repeat(60));

  const pubsub = new PubSubManager();
  await pubsub.connect();

  // Cache service subscribes to invalidation events
  console.log('\n--- Cache Service Subscribes ---');
  const cache = new Map();

  await pubsub.pSubscribe('cache:invalidate:*', (message, channel) => {
    const key = channel.split(':').slice(2).join(':');
    if (cache.has(key)) {
      cache.delete(key);
      console.log(`  [Cache] Invalidated: ${key}`);
    }
  });

  await new Promise(resolve => setTimeout(resolve, 100));

  // Populate cache
  console.log('\n--- Populate Cache ---');
  cache.set('user:1000', { name: 'Alice', email: 'alice@example.com' });
  cache.set('user:1001', { name: 'Bob', email: 'bob@example.com' });
  console.log(`  [Cache] Size: ${cache.size}`);

  // Data update triggers invalidation
  console.log('\n--- Data Updated (Trigger Invalidation) ---');
  await pubsub.publish('cache:invalidate:user:1000', { reason: 'user_updated' });

  await new Promise(resolve => setTimeout(resolve, 100));

  console.log(`  [Cache] Size after invalidation: ${cache.size}`);

  await pubsub.disconnect();
}

// Main execution
async function main() {
  try {
    await demoBasicPubSub();
    await demoPatternSubscription();
    await demoChatRoom();
    await demoNotificationSystem();
    await demoMultipleSubscribers();
    await demoCacheInvalidation();

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

module.exports = { PubSubManager, ChatRoom, NotificationSystem };
