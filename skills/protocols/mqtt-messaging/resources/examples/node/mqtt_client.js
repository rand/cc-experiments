#!/usr/bin/env node
/**
 * MQTT Node.js Client Example
 *
 * Production-ready MQTT client using mqtt.js
 *
 * Install: npm install mqtt
 * Usage: node mqtt_client.js --broker mqtt://localhost:1883 --topic test/topic
 */

const mqtt = require('mqtt');

class MQTTClient {
  constructor(brokerUrl, options = {}) {
    this.brokerUrl = brokerUrl;
    this.options = {
      clientId: options.clientId || `mqtt_client_${Math.random().toString(16).slice(2, 10)}`,
      clean: options.clean !== undefined ? options.clean : true,
      reconnectPeriod: options.reconnectPeriod || 1000,
      connectTimeout: options.connectTimeout || 30000,
      keepalive: options.keepalive || 60,
      username: options.username,
      password: options.password,
      will: options.will
    };

    this.messageHandlers = new Map();
    this.client = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.client = mqtt.connect(this.brokerUrl, this.options);

      this.client.on('connect', (connack) => {
        console.log(`✓ Connected to ${this.brokerUrl}`);
        console.log(`  Session present: ${connack.sessionPresent}`);

        // Resubscribe if needed
        if (!connack.sessionPresent && this.messageHandlers.size > 0) {
          this.resubscribe();
        }

        resolve();
      });

      this.client.on('error', (error) => {
        console.error(`✗ Connection error: ${error.message}`);
        reject(error);
      });

      this.client.on('disconnect', () => {
        console.log('✗ Disconnected');
      });

      this.client.on('offline', () => {
        console.log('⚠ Client offline, reconnecting...');
      });

      this.client.on('reconnect', () => {
        console.log('⚠ Reconnecting...');
      });

      this.client.on('message', (topic, payload, packet) => {
        const message = payload.toString();
        const qos = packet.qos;
        const retain = packet.retain;

        console.log(`📥 [${topic}] (QoS ${qos}, retain=${retain}): ${message.substring(0, 100)}`);

        // Call handlers
        for (const [pattern, handler] of this.messageHandlers.entries()) {
          if (this.topicMatches(topic, pattern)) {
            handler(topic, message, qos, retain);
          }
        }
      });
    });
  }

  subscribe(topic, qos = 0, handler = null) {
    return new Promise((resolve, reject) => {
      this.client.subscribe(topic, { qos }, (err, granted) => {
        if (err) {
          console.error(`✗ Subscribe failed: ${err.message}`);
          reject(err);
        } else {
          console.log(`✓ Subscribed to ${topic} (granted QoS: ${granted[0].qos})`);
          if (handler) {
            this.messageHandlers.set(topic, handler);
          }
          resolve(granted);
        }
      });
    });
  }

  publish(topic, payload, qos = 0, retain = false) {
    return new Promise((resolve, reject) => {
      if (typeof payload === 'object') {
        payload = JSON.stringify(payload);
      }

      this.client.publish(topic, payload, { qos, retain }, (err) => {
        if (err) {
          console.error(`✗ Publish failed: ${err.message}`);
          reject(err);
        } else {
          console.log(`✓ Published to ${topic}`);
          resolve();
        }
      });
    });
  }

  disconnect() {
    return new Promise((resolve) => {
      this.client.end(false, () => {
        console.log('✓ Disconnected gracefully');
        resolve();
      });
    });
  }

  resubscribe() {
    for (const topic of this.messageHandlers.keys()) {
      this.subscribe(topic, 1);
    }
  }

  topicMatches(topic, pattern) {
    const topicParts = topic.split('/');
    const patternParts = pattern.split('/');

    for (let i = 0; i < patternParts.length; i++) {
      if (patternParts[i] === '#') {
        return true;
      }
      if (patternParts[i] !== '+' && patternParts[i] !== topicParts[i]) {
        return false;
      }
    }

    return topicParts.length === patternParts.length;
  }
}

// CLI
async function main() {
  const args = require('minimist')(process.argv.slice(2));

  if (!args.broker || !args.topic) {
    console.error('Usage: node mqtt_client.js --broker mqtt://localhost --topic test/topic [--message "hello"]');
    process.exit(1);
  }

  const client = new MQTTClient(args.broker, {
    username: args.username,
    password: args.password,
    will: {
      topic: 'clients/nodejs/status',
      payload: 'offline',
      qos: 1,
      retain: true
    }
  });

  try {
    await client.connect();

    // Publish online status
    await client.publish('clients/nodejs/status', 'online', 1, true);

    // Subscribe
    await client.subscribe(args.topic, 1, (topic, payload) => {
      console.log(`Handler: ${topic} -> ${payload}`);
    });

    // Publish message if provided
    if (args.message) {
      await client.publish(args.topic, args.message, 1);
    }

    // Keep running
    process.on('SIGINT', async () => {
      console.log('\nShutting down...');
      await client.publish('clients/nodejs/status', 'offline', 1, true);
      await client.disconnect();
      process.exit(0);
    });

    console.log('Listening... (Ctrl+C to exit)');

  } catch (error) {
    console.error('Fatal error:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = MQTTClient;
