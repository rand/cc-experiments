/**
 * Node.js Consumer with Retry Logic
 *
 * Robust consumer with connection recovery, error handling, and retry logic.
 *
 * Usage:
 *   npm install amqplib
 *   node consumer_with_retry.js
 */

const amqp = require('amqplib');

class ResilientConsumer {
  constructor(url, queueName) {
    this.url = url || 'amqp://localhost';
    this.queueName = queueName || 'tasks';
    this.connection = null;
    this.channel = null;
    this.isConsuming = false;
  }

  async connect() {
    try {
      console.log('Connecting to RabbitMQ...');
      this.connection = await amqp.connect(this.url);

      // Handle connection errors
      this.connection.on('error', (err) => {
        console.error('Connection error:', err);
        this.reconnect();
      });

      this.connection.on('close', () => {
        console.log('Connection closed. Reconnecting...');
        this.reconnect();
      });

      this.channel = await this.connection.createChannel();

      // Handle channel errors
      this.channel.on('error', (err) => {
        console.error('Channel error:', err);
      });

      this.channel.on('close', () => {
        console.log('Channel closed');
      });

      console.log('Connected successfully');
    } catch (err) {
      console.error('Connection failed:', err);
      throw err;
    }
  }

  async reconnect() {
    if (this.isConsuming) {
      console.log('Attempting to reconnect in 5 seconds...');
      setTimeout(async () => {
        try {
          await this.connect();
          await this.setupQueue();
          await this.consume();
        } catch (err) {
          console.error('Reconnection failed:', err);
          this.reconnect();
        }
      }, 5000);
    }
  }

  async setupQueue() {
    console.log('Setting up queue...');

    // Main queue with DLX
    await this.channel.assertQueue(this.queueName, {
      durable: true,
      arguments: {
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'failed.' + this.queueName
      }
    });

    // Dead letter exchange
    await this.channel.assertExchange('dlx', 'direct', { durable: true });

    // Failed messages queue
    await this.channel.assertQueue('failed.' + this.queueName, { durable: true });
    await this.channel.bindQueue('failed.' + this.queueName, 'dlx', 'failed.' + this.queueName);

    // Fair dispatch
    await this.channel.prefetch(1);

    console.log('Queue setup complete');
  }

  async processMessage(msg) {
    const content = msg.content.toString();
    console.log('\nReceived:', content);

    try {
      // Parse message
      const data = JSON.parse(content);
      const retryCount = data.retry_count || 0;
      const maxRetries = 3;

      console.log(`Attempt ${retryCount + 1}/${maxRetries + 1}`);

      // Simulate processing (30% failure rate)
      await new Promise((resolve) => setTimeout(resolve, 1000));

      if (Math.random() < 0.3) {
        throw new Error('Random processing failure');
      }

      console.log('✓ Processing successful');
      this.channel.ack(msg);

    } catch (err) {
      console.error('✗ Processing failed:', err.message);

      const data = JSON.parse(content);
      const retryCount = data.retry_count || 0;
      const maxRetries = 3;

      if (retryCount < maxRetries) {
        // Retry: increment count and requeue
        data.retry_count = retryCount + 1;

        console.log(`Retrying (attempt ${retryCount + 1}/${maxRetries})...`);

        await this.channel.sendToQueue(
          this.queueName,
          Buffer.from(JSON.stringify(data)),
          { persistent: true }
        );

        this.channel.ack(msg);
      } else {
        // Max retries: reject and send to DLX
        console.log('Max retries exceeded. Sending to DLX.');
        this.channel.nack(msg, false, false);
      }
    }
  }

  async consume() {
    console.log(`\nConsuming from queue: ${this.queueName}`);
    console.log('Press CTRL+C to exit\n');

    this.isConsuming = true;

    await this.channel.consume(
      this.queueName,
      (msg) => {
        if (msg) {
          this.processMessage(msg);
        }
      },
      { noAck: false }
    );
  }

  async close() {
    this.isConsuming = false;
    console.log('\nClosing connection...');
    if (this.channel) await this.channel.close();
    if (this.connection) await this.connection.close();
    console.log('Connection closed');
  }
}

// Main
async function main() {
  const consumer = new ResilientConsumer(
    process.env.AMQP_URL || 'amqp://localhost',
    process.env.QUEUE_NAME || 'tasks'
  );

  try {
    await consumer.connect();
    await consumer.setupQueue();
    await consumer.consume();

    // Graceful shutdown
    process.on('SIGINT', async () => {
      await consumer.close();
      process.exit(0);
    });

  } catch (err) {
    console.error('Fatal error:', err);
    process.exit(1);
  }
}

main();
