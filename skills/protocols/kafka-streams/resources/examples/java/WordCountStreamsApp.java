/**
 * Kafka Streams Word Count Application
 *
 * Demonstrates stateless and stateful stream processing with Kafka Streams.
 * Reads text from input topic, counts words, outputs to result topic.
 *
 * Build:
 *   mvn clean package
 *
 * Run:
 *   java -jar target/word-count-streams-1.0.jar
 */

package com.example.kafka.streams;

import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.*;
import org.apache.kafka.streams.KeyValue;

import java.util.Arrays;
import java.util.Properties;
import java.util.concurrent.CountDownLatch;

public class WordCountStreamsApp {

    public static void main(String[] args) {
        // Configuration
        Properties props = new Properties();
        props.put(StreamsConfig.APPLICATION_ID_CONFIG, "word-count-app");
        props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
        props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());
        props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.String().getClass());

        // Exactly-once processing
        props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, StreamsConfig.EXACTLY_ONCE_V2);

        // State directory
        props.put(StreamsConfig.STATE_DIR_CONFIG, "/tmp/kafka-streams");

        // Commit interval (for changelog)
        props.put(StreamsConfig.COMMIT_INTERVAL_MS_CONFIG, 10000);

        // Build topology
        StreamsBuilder builder = new StreamsBuilder();
        buildWordCountTopology(builder);

        // Create and start streams application
        final KafkaStreams streams = new KafkaStreams(builder.build(), props);
        final CountDownLatch latch = new CountDownLatch(1);

        // Attach shutdown handler
        Runtime.getRuntime().addShutdownHook(new Thread("streams-shutdown-hook") {
            @Override
            public void run() {
                System.out.println("Shutting down Kafka Streams application...");
                streams.close();
                latch.countDown();
            }
        });

        try {
            System.out.println("Starting Kafka Streams application...");
            streams.start();
            latch.await();
        } catch (Throwable e) {
            System.err.println("Error running Kafka Streams application: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }

        System.exit(0);
    }

    /**
     * Build word count topology
     */
    public static void buildWordCountTopology(StreamsBuilder builder) {
        // Input topic: lines of text
        KStream<String, String> textLines = builder.stream("text-input");

        // Process: lowercase → split → count
        KTable<String, Long> wordCounts = textLines
            // Lowercase
            .mapValues(value -> value.toLowerCase())

            // Split lines into words
            .flatMapValues(value -> Arrays.asList(value.split("\\W+")))

            // Filter empty strings
            .filter((key, value) -> !value.isEmpty())

            // Group by word (re-key)
            .groupBy((key, word) -> word)

            // Count occurrences
            .count(Materialized.as("word-counts-store"));

        // Output to topic
        wordCounts
            .toStream()
            .to("word-count-output", Produced.with(Serdes.String(), Serdes.Long()));

        // Print to console for debugging
        wordCounts
            .toStream()
            .foreach((word, count) ->
                System.out.println("Word: " + word + ", Count: " + count)
            );
    }

    /**
     * Build advanced processing topology with windowing
     */
    public static void buildAdvancedTopology(StreamsBuilder builder) {
        // Input: page view events
        KStream<String, String> pageViews = builder.stream("page-views");

        // Example 1: Filter
        KStream<String, String> filteredViews = pageViews
            .filter((key, value) -> value.contains("product"));

        filteredViews.to("product-views");

        // Example 2: Map
        KStream<String, String> transformed = pageViews
            .map((key, value) ->
                KeyValue.pair(key.toUpperCase(), value.toUpperCase())
            );

        // Example 3: Branch (split stream)
        KStream<String, String>[] branches = pageViews.branch(
            (key, value) -> value.contains("mobile"),   // Branch 0: mobile
            (key, value) -> value.contains("desktop"),  // Branch 1: desktop
            (key, value) -> true                        // Branch 2: other
        );

        branches[0].to("mobile-views");
        branches[1].to("desktop-views");
        branches[2].to("other-views");

        // Example 4: Aggregate with windowing
        KTable<Windowed<String>, Long> windowedCounts = pageViews
            .groupByKey()
            .windowedBy(TimeWindows.of(Duration.ofMinutes(5)))
            .count();

        // Example 5: Join streams
        KStream<String, String> orders = builder.stream("orders");
        KStream<String, String> payments = builder.stream("payments");

        KStream<String, String> joined = orders.join(
            payments,
            (orderValue, paymentValue) ->
                "Order: " + orderValue + ", Payment: " + paymentValue,
            JoinWindows.of(Duration.ofHours(1))
        );

        joined.to("order-payments");
    }

    /**
     * Build stateful processing with state stores
     */
    public static void buildStatefulTopology(StreamsBuilder builder) {
        // Input: user events
        KStream<String, String> events = builder.stream("user-events");

        // Aggregate: count events per user
        KTable<String, Long> userEventCounts = events
            .groupByKey()
            .count(Materialized.as("user-event-counts"));

        // Reduce: keep latest event per user
        KTable<String, String> latestEvents = events
            .groupByKey()
            .reduce(
                (oldValue, newValue) -> newValue,
                Materialized.as("latest-events")
            );

        // Aggregate with custom logic
        KTable<String, AggregatedStats> aggregatedStats = events
            .groupByKey()
            .aggregate(
                AggregatedStats::new,  // Initializer
                (key, value, aggregate) -> {
                    // Update aggregation
                    aggregate.count++;
                    aggregate.lastValue = value;
                    return aggregate;
                },
                Materialized.as("aggregated-stats")
            );

        // Output results
        userEventCounts.toStream().to("user-event-counts-output");
        latestEvents.toStream().to("latest-events-output");
    }

    /**
     * Example aggregation class
     */
    static class AggregatedStats {
        int count = 0;
        String lastValue = "";

        @Override
        public String toString() {
            return "count=" + count + ", lastValue=" + lastValue;
        }
    }
}
