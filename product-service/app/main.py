# main.py
from contextlib import asynccontextmanager
from typing import Optional, Annotated
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence
from fastapi import FastAPI, Depends, HTTPException
from typing import AsyncGenerator
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
import json

from app import settings
from app.db_engine import engine
from app.models.product_model import Product
from app.crud.product_crud import add_new_product, get_all_products
from app.deps import get_session, get_kafka_producer

def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


async def consume_messages(topic, bootstrap_servers):
    # Create a consumer instance.
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="my-prodocct-consumer-group",
        # auto_offset_reset="earliest",
    )

    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print("RAW")
            print(f"Received message on topic {message.topic}")

            product_data = json.loads(message.value.decode())
            print("TYPE", (type(product_data)))
            print(f"Product Data {product_data}")

            with next(get_session()) as session:
                print("SAVING DATA TO DATABSE")
                db_insert_product = add_new_product(
                    product_data=Product(**product_data), session=session)
                print("DB_INSERT_PRODUCT", db_insert_product)

            # Here you can add code to process each message.
            # Example: parse the message, store it in a database, etc.
    finally:
        # Ensure to close the consumer when done.
        await consumer.stop()


# The first part of the function, before the yield, will
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    print("Creating table!")

    task = asyncio.create_task(consume_messages(
        settings.KAFKA_PRODUCT_TOPIC, 'broker:19092'))
    create_db_and_tables()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Hello World API with Kafka DB",
    version="0.0.1",
)


def get_session():
    with Session(engine) as session:
        yield session


@app.get("/")
def read_root():
    return {"Hello": "Product Service"}

# Kafka Producer as a dependency


async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()


@app.post("/manage-products/", response_model=Product)
async def create_new_product(product: Product, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    product_dict = {field: getattr(product, field) for field in product.dict()}
    product_json = json.dumps(product_dict).encode("utf-8")
    print("product_JSON:", product_json)
    # Produce message
    await producer.send_and_wait(settings.KAFKA_PRODUCT_TOPIC, product_json)
    # new_product = add_new_product(product, session)
    return product

@app.get("/manage-products/all", response_model=list[Product])
def get_all_product(session: Annotated[Session, Depends(get_session)]):
    """get all product by data-base """
    return get_all_products(session)

@app.get("/manage-products/{product_id}", response_model=list[Product])
def get_single_product(product_id:int, session: Annotated[Session, Depends(get_session)]):
    """get a single product by id """
    try:
        return get_products_by_id(product_id=product_id, session=session)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, details=str(e))