"""The entrypoint for the server app."""
import string
import random
import time
from functools import wraps

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langchain.vectorstores import VectorStore
import chromadb
from chromadb.config import Settings

from log_configs import log

app = FastAPI(title="Assistant.Bible  APIs", version="0.0.1-alpha.1",
    description="The server application that provides APIs to interact \
with the Assistant.Bible Chatbot App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_COLLECTION = None

@app.on_event("startup")
async def startup_event():
    '''Set up ChromaDB connection'''
    log.info("Connecting to vector DB...")
    # Option 1
    # This method connects to the DB that get stored on the server itself where the app is running
    chroma_client = chromadb.Client(Settings(
        chroma_db_impl='duckdb+parquet',
        persist_directory="../chromadb"))

    # Option 2
    # This method requires us to run the chroma DB as a separate service (say in docker-compose).
    # In future this would allow us to keep multiple options for DB connection,
    # letting different users set up and host their own chroma DBs where ever they please 
    # and just use the correct host and port.
    # chroma_client = chromadb.Client(Settings(chroma_api_impl="rest",
    #         chroma_server_host="localhost",
    #         chroma_server_http_port="8000"
    #     ))
    # Also need to sort out the following 
    # * how authentication for chorma DB access will work in that case
    # * how the connection can be handled like session that is started upon each user's API request
    #   to let each user connect to the DB that he prefers and has rights for

    collection = chroma_client.get_or_create_collection(
        name="adotb_collection",
        # avoid having to create embeddings in two steps before storing and querying
        # embedding_function=custom_openai_emb_fn,
        )
    DB_COLLECTION = collection

@app.middleware("http")
async def log_requests(request: Request, call_next):
    '''Place to define common logging for all API calls'''
    idem = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    log.info(f"rid={idem} start request: {request.method} {request.url.path}")
    start_time = time.time()
    log.debug(f"rid={idem} request headers: {request.headers}")
    log.debug(f"rid={idem} request parameters: {request.path_params} {request.query_params} ")

    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = '{0:.2f}'.format(process_time)
    log.info(f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}")

    return response


def auth_check_decorator(func):
    '''checks a predefined token in request header'''
    @wraps(func)
    async def wrapper(*args, **kwargs):    
        # To be implemented.
        # Uses Supabase, gets user roles 
        # Verify the DB requesting to connect to and sources listed for querying are permissible 
        # Raises 403 error for unauthorized access
        # Passes the list of accessible sources to the calling function
        return await func(*args, **kwargs)
    return wrapper

@app.get("/")
async def get_root():
    '''Landing page with basic info about the App'''
    log.info("In root endpoint")
    return {"message": "App is up and running"}

