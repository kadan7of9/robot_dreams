# Import necessary libraries
import pandas as pd
import os
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid
from pymongo.database import Database, Collection
import logging
from datetime import datetime, timedelta
import time
from collections import deque
from datetime import timedelta

# turn logging on
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_HOST = os.getenv("MONGO_HOST", "localhost")  # Default to localhost if not set
MONGO_PORT = 27017  # Default MongoDB port
MONGO_DB = os.getenv("MONGO_DB", "crack_meter-db")  # Default to test_db if not set


def connect_to_mongodb():
    try:
        client = MongoClient(
            f"mongodb://{MONGO_HOST}:{MONGO_PORT}/", serverSelectionTimeoutMS=5000
        )
        client.server_info()
        db: Database = client[MONGO_DB]
        logger.info(f"Connected to MongoDB at {MONGO_HOST}:{MONGO_PORT}")
        return client, db
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        return None, None


def create_collection(db: Database, collection_name: str) -> Collection:
    time_series_options = {
        "timeField": "timestamp",
        "metaField": "metadata",
    }
    try:
        collection: Collection = db.create_collection(
            collection_name, timeseries=time_series_options
        )
    except CollectionInvalid:
        logger.warning(
            f"Collection {collection_name} already exists. Using existing collection."
        )
        collection = db[collection_name]
    logger.info(f"Using collection: {collection_name}")
    return collection


def insert_data_in_batches(
    collection: Collection,
    data: pd.DataFrame,
    batch_size: int = 10,
    delay_seconds: float = 0.1,
):
    """
    Insert DataFrame data into MongoDB in batches with delays between batches.

    Args:
        collection: MongoDB collection to insert data into
        data: pandas DataFrame containing the data to insert
        batch_size: Number of records to insert in each batch
        delay_seconds: Delay in seconds between batches
    """
    # Convert DataFrame to list of dictionaries
    records = data.to_dict(orient="records")
    total_records = len(records)

    logger.info(
        f"Starting batch insertion: {total_records} records, batch size: {batch_size}, delay: {delay_seconds}s"
    )

    # Insert data in batches
    for i in range(0, total_records, batch_size):
        batch_end = min(i + batch_size, total_records)
        batch = records[i:batch_end]

        try:
            # Insert current batch
            result = collection.insert_many(batch)
            batch_num = (i // batch_size) + 1
            total_batches = (total_records + batch_size - 1) // batch_size

            logger.info(
                f"Batch {batch_num}/{total_batches}: Inserted {len(result.inserted_ids)} records (records {i+1}-{batch_end})"
            )

            # Add delay between batches (except for the last batch)
            if batch_end < total_records:
                logger.info(f"Waiting {delay_seconds} seconds before next batch...")
                time.sleep(delay_seconds)

        except Exception as e:
            logger.error(f"Error inserting batch {batch_num}: {e}")
            raise


def main():
    path = "datasets/crack_meter/CalibData-30kHz-0-12--.csv"
    logger.info("Reading CSV data from %s", path)
    try:
        data = pd.read_csv(path, delimiter=";")
        logger.info("CSV data read successfully.")
        # Add dummy timestamp field, because it is missing in the CSV
        base_time = datetime.now()  # get actual time
        data["timestamp"] = [base_time + timedelta(seconds=i) for i in range(len(data))]
        # Print first few rows of read data
        print(data.head())
    except Exception as e:
        logger.error("Error reading CSV data: %s", e)
        return
    client, db = connect_to_mongodb()
    if not client:
        return
    db: Database = client[MONGO_DB]
    collection: Collection = create_collection(db, "crack_data")

    # Insert data in batches with delays
    try:
        insert_data_in_batches(collection, data, batch_size=100, delay_seconds=0.1)
        logger.info("All data inserted into MongoDB successfully.")
    except Exception as e:
        logger.error("Error inserting data into MongoDB: %s", e)
    finally:
        client.close()


if __name__ == "__main__":
    main()
