from __future__ import annotations

from autogen.logger.logger_factory import LoggerFactory
import sqlite3
from typing import Dict, TYPE_CHECKING, Union
import uuid

from openai import OpenAI, AzureOpenAI
from openai.types.chat import ChatCompletion

if TYPE_CHECKING:
    from autogen import ConversableAgent, OpenAIWrapper

autogen_logger = None

def start_logging(logger_type:str = "sqlite", config: Dict={}) -> str:
    global autogen_logger
    if autogen_logger is None:
        autogen_logger = LoggerFactory.get_logger(logger_type=logger_type, config=config)
    return autogen_logger.start_logging()


def log_chat_completion(
    invocation_id: uuid.UUID,
    client_id: int,
    wrapper_id: int,
    request: Dict,
    response: Union[str, ChatCompletion],
    is_cached: int,
    cost: float,
    start_time: str,
) -> None:
    autogen_logger.log_chat_completion(
        invocation_id,
        client_id,
        wrapper_id,
        request,
        response,
        is_cached,
        cost,
        start_time
    )


def log_new_agent(agent: ConversableAgent, init_args: Dict) -> None:
    autogen_logger.log_new_agent(agent, init_args)

def log_new_wrapper(wrapper: OpenAIWrapper, init_args: Dict) -> None:
    autogen_logger.log_new_wrapper(wrapper, init_args)

def log_new_client(client: Union[AzureOpenAI, OpenAI], wrapper: OpenAIWrapper, init_args: Dict) -> None:
    autogen_logger.log_new_client(client, wrapper, init_args)

def stop_logging() -> None:
    autogen_logger.stop_logging()

def get_connection() -> Union[sqlite3.Connection]:
    return autogen_logger.get_connection()
