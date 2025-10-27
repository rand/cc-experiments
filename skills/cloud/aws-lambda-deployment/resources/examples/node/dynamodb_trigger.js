/**
 * DynamoDB Streams trigger example.
 *
 * Processes DynamoDB stream records (INSERT, MODIFY, REMOVE events).
 */

const AWS = require('aws-sdk');
const sns = new AWS.SNS();

exports.handler = async (event, context) => {
    console.log('Processing DynamoDB stream records:', JSON.stringify(event, null, 2));

    const promises = event.Records.map(async (record) => {
        try {
            await processRecord(record);
        } catch (error) {
            console.error(`Error processing record ${record.eventID}:`, error);
            throw error; // Fail the batch
        }
    });

    await Promise.all(promises);

    return {
        statusCode: 200,
        body: JSON.stringify({
            message: `Processed ${event.Records.length} records`,
        }),
    };
};

async function processRecord(record) {
    const eventName = record.eventName; // INSERT, MODIFY, REMOVE
    const tableName = record.eventSourceARN.split('/')[1];

    console.log(`Processing ${eventName} event from ${tableName}`);

    switch (eventName) {
        case 'INSERT':
            await handleInsert(record);
            break;
        case 'MODIFY':
            await handleModify(record);
            break;
        case 'REMOVE':
            await handleRemove(record);
            break;
        default:
            console.warn(`Unknown event type: ${eventName}`);
    }
}

async function handleInsert(record) {
    const newImage = record.dynamodb.NewImage;
    console.log('New item:', newImage);

    // Convert DynamoDB format to regular object
    const item = unmarshall(newImage);

    // Example: Send notification
    if (item.notify) {
        await sendNotification({
            subject: 'New Item Created',
            message: `New item created: ${JSON.stringify(item)}`,
        });
    }

    // Example: Trigger downstream processing
    // await processNewItem(item);
}

async function handleModify(record) {
    const oldImage = record.dynamodb.OldImage;
    const newImage = record.dynamodb.NewImage;

    console.log('Old item:', oldImage);
    console.log('New item:', newImage);

    const oldItem = unmarshall(oldImage);
    const newItem = unmarshall(newImage);

    // Example: Detect specific changes
    if (oldItem.status !== newItem.status) {
        console.log(`Status changed: ${oldItem.status} -> ${newItem.status}`);

        await sendNotification({
            subject: 'Item Status Changed',
            message: `Item ${newItem.id} status: ${oldItem.status} -> ${newItem.status}`,
        });
    }

    // Example: Update search index
    // await updateSearchIndex(newItem);
}

async function handleRemove(record) {
    const oldImage = record.dynamodb.OldImage;
    console.log('Deleted item:', oldImage);

    const item = unmarshall(oldImage);

    // Example: Archive deleted item
    // await archiveItem(item);

    // Example: Clean up related resources
    // await cleanupRelatedResources(item.id);
}

async function sendNotification(params) {
    const topicArn = process.env.SNS_TOPIC_ARN;

    if (!topicArn) {
        console.warn('SNS_TOPIC_ARN not configured, skipping notification');
        return;
    }

    try {
        await sns.publish({
            TopicArn: topicArn,
            Subject: params.subject,
            Message: params.message,
        }).promise();

        console.log('Notification sent');
    } catch (error) {
        console.error('Failed to send notification:', error);
        throw error;
    }
}

function unmarshall(dynamoDBItem) {
    /**
     * Convert DynamoDB AttributeValue format to regular JavaScript object.
     *
     * DynamoDB format: { "name": { "S": "John" }, "age": { "N": "30" } }
     * Regular format: { "name": "John", "age": 30 }
     */
    const result = {};

    for (const [key, value] of Object.entries(dynamoDBItem)) {
        if (value.S !== undefined) {
            result[key] = value.S;
        } else if (value.N !== undefined) {
            result[key] = Number(value.N);
        } else if (value.BOOL !== undefined) {
            result[key] = value.BOOL;
        } else if (value.NULL !== undefined) {
            result[key] = null;
        } else if (value.L !== undefined) {
            result[key] = value.L.map(item => unmarshall({ item }).item);
        } else if (value.M !== undefined) {
            result[key] = unmarshall(value.M);
        } else if (value.SS !== undefined) {
            result[key] = value.SS;
        } else if (value.NS !== undefined) {
            result[key] = value.NS.map(Number);
        } else if (value.BS !== undefined) {
            result[key] = value.BS;
        }
    }

    return result;
}
