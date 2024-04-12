from __future__ import annotations

import json
from typing import Literal, Tuple, Optional, Union, Any, List, Dict

import pytest
from typing_extensions import Annotated

import autogen
import autogen.agentchat.contrib.nexusravenv2_local_function_calling as Nexus
from autogen import UserProxyAgent, Agent


network_address = "192.168.0.115"

# LOCAL LOCAL
llm_config = {
    "config_list": [
        {"model": "litellmnotneeded", "api_key": "NotRequired", "base_url": f"http://{network_address}:8801"}
    ],
    "cache_seed": None,
}  ## CRITICAL - ENSURE THERE'S NO CACHING FOR TESTING


def fake_receive(
    self,
    message: Union,
    sender: Agent,
    request_reply: Optional = None,
    silent: Optional = False,
):
    self._process_received_message(message, sender, silent)
    if request_reply is False or request_reply is None and self.reply_at_receive[sender] is False:
        return
    reply = self.generate_reply(messages=self.chat_messages[sender], sender=sender)
    function_name, args_map, thought_part = Nexus.NexusFunctionCallingAssistant.parse_function_details(reply)
    formatted_reply = {
        "content": thought_part,
        "function_call": None,
        "role": "assistant",
        "tool_calls": [
            {
                "id": 43,  # TODO fix this as response id , was generate_oai_reply
                "function": {"arguments": json.dumps(args_map), "name": function_name},
                "type": "function",
            }
        ],
    }
    if formatted_reply is not None:
        self.send(formatted_reply, sender, silent=silent)


def create_fake_send(user_proxy, mocker):
    def fake_send(msg2send, recipient, silent=False):
        print(f"Recipient: {recipient}")
        print(f"Messages: {msg2send}")
        print(f"Sender: {silent}")
        #mocker.patch.object(recipient, "receive", fake_receive)
        recipient.receive( message=msg2send, sender=user_proxy, request_reply=True)

    return fake_send


def get_reply_from_nexus(self, all_messages, cache, llm_client) -> str:
    return  "Call: random_word_generator(seed=42, prefix='chase')<bot_end> \nThought: functioncaller.random_word_generator().then(randomWord => mistral.speak(`Using the randomly generated word \"${randomWord},\" I will now solve this logic problem.`));", 43



@pytest.fixture
def chatbot(mocker):
    agent = Nexus.NexusFunctionCallingAssistant(
        name="chatbot",
        system_message="""For currency exchange tasks,
        only use the functions you have been provided with.
        Output 'BAZINGA!' when an answer has been provided.
        Do not include the function name or result in the JSON.
        Example of the return JSON is:
        {
            "parameter_1_name": 100.00,
            "parameter_2_name": "ABC",
            "parameter_3_name": "DEF",
        }.
        Another example of the return JSON is:
        {
            "parameter_1_name": "GHI",
            "parameter_2_name": "ABC",
            "parameter_3_name": "DEF",
            "parameter_4_name": 123.00,
        }. """,  # MS - this was needed to ensure the function name was returned
        llm_config=llm_config,
    )

    find_generate_oai_functions = [
        f["reply_func"] for f in agent._reply_func_list if f["reply_func"].__name__ == "generate_oai_reply"
    ]

    agent.get_reply_from_nexus = lambda all_msgs, cache, llmc:  get_reply_from_nexus(agent,  all_msgs, cache, llmc)

    return agent


@pytest.fixture
def user_proxy(mocker):
    agent = autogen.UserProxyAgent(
        name="user_proxy",
        # MS updated to search for BAZINGA! to terminate
        is_termination_msg=lambda x: x.get("content", "") and "BAZINGA!" in x.get("content", ""),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=4,
        code_execution_config={"work_dir": "/tmp/coding", "use_docker": False},
    )
    mocker.patch.object(agent, "send", create_fake_send(agent, mocker))
    return agent


def check_tool_call(tc):
    tool_name = tc.get("function", dict())
    arguments = json.loads(tool_name.get("arguments", "{}"))
    not_found = "not found"
    return (
        tool_name.get("name", not_found) == "random_word_generator"
        and arguments.get("seed", not_found) == 42
        and arguments.get("prefix", not_found) == "chase"
    )


def check_tool_response(response):
    content = response.get("content", "")
    role = response.get("role", "")
    check_responses = [
        tool_response
        for tool_response in response.get("tool_responses", [])
        if tool_response.get("role") == "tool"
        and tool_response.get("content", "").endswith("_not_random_actually_but_this_is_a_test")
    ]
    # 'tool_responses': [{'tool_call_id': 43, 'role': 'tool', 'content': 'chase_not_random_actually_but_this_is_a_test'}], 'role': 'tool'}
    return content.endswith("_not_random_actually_but_this_is_a_test") and len(check_responses) and role == "tool"


def test_should_respond_with_a_function_call(user_proxy: UserProxyAgent, chatbot: Nexus.NexusFunctionCallingAssistant):
    @user_proxy.register_for_execution()
    @chatbot.register_for_llm(description="A Random Word Generator")
    def random_word_generator(
        seed: Annotated[int, "Randomizing Seed for the word generation"] = 42,
        prefix: Annotated[str, "Prefix to Append to the Word that was generated."] = "USD",
    ) -> str:
        return f"{prefix}_not_random_actually_but_this_is_a_test"

    # Test that the function map is the function
    assert user_proxy.function_map["random_word_generator"]._origin == random_word_generator

    result = user_proxy.initiate_chat(
        chatbot,
        message="Generate a Random Word Please",
        summary_method="last_msg",
        clear_history=True,
        cache=None,
    )
    #analyse response hostory
    tools_calls = [
        tool_calls.get("function", dict())
        for response in result.chat_history
        for tool_calls in response.get("tool_calls", dict())
        if check_tool_call(tool_calls)
    ]
    assert len(tools_calls) > 0

    tool_responses = [
        response
        for agent, responses in chatbot.chat_messages.items()
        for response in responses
        if check_tool_response(response)
    ]
    assert len(tool_responses) > 0
