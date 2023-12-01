import autogen
import pytest
import sys
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.skipif(
    skip or not sys.version.startswith("3.10"),
    reason="do not run if openai is not installed or py!=3.10",
)
def test_function_call_groupchat():
    import random

    def get_random_number():
        return random.randint(0, 100)

    config_list_gpt4 = autogen.config_list_from_json(
        OAI_CONFIG_LIST,
        filter_dict={
            "model": ["gpt-4", "gpt-4-0314", "gpt4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
        },
        file_location=KEY_LOC,
    )
    llm_config = {
        "config_list": config_list_gpt4,
        "cache_seed": 42,
        "functions": [
            {
                "name": "get_random_number",
                "description": "Get a random number between 0 and 100",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        ],
    }
    user_proxy = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="A human admin that will execute function_calls.",
        function_map={"get_random_number": get_random_number},
        human_input_mode="NEVER",
    )
    coder = autogen.AssistantAgent(
        name="Player",
        system_message="You will can function `get_random_number` to get a random number. Stop only when you get at least 1 even number and 1 odd number. Reply TERMINATE to stop.",
        llm_config=llm_config,
    )
    groupchat = autogen.GroupChat(agents=[user_proxy, coder], messages=[], max_round=7)
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    user_proxy.initiate_chat(manager, message="Let's start the game!")


@pytest.mark.skipif(
    skip or not sys.version.startswith("3.10"),
    reason="do not run if openai is not installed or py!=3.10",
)
def test_update_function():
    config_list_gpt4 = autogen.config_list_from_json(
        "OAI_CONFIG_LIST",
        filter_dict={
            "model": ["gpt-4", "gpt-4-0314", "gpt4", "gpt-4-32k", "gpt-4-32k-0314", "gpt-4-32k-v0314"],
        },
    )
    llm_config = {
        "config_list": config_list_gpt4,
        "seed": 42,
        "functions": [],
    }

    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        is_termination_msg=lambda x: True if "TERMINATE" in x.get("content") else False,
    )
    assistant = autogen.AssistantAgent(name="test", llm_config=llm_config)

    # Define a new function *after* the assistant has been created
    assistant.update_function_signature(
        {
            "name": "greet_user",
            "description": "Greets the user.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        is_remove=False,
    )
    user_proxy.initiate_chat(
        assistant,
        message="What functions do you know about in the context of this conversation? End your response with 'TERMINATE'.",
    )
    messages1 = assistant.chat_messages[user_proxy][-1]["content"]
    print(messages1)

    assistant.update_function_signature("greet_user", is_remove=True)
    user_proxy.initiate_chat(
        assistant,
        message="What functions do you know about in the context of this conversation? End your response with 'TERMINATE'.",
    )
    messages2 = assistant.chat_messages[user_proxy][-1]["content"]
    print(messages2)
    # The model should know about the function in the context of the conversation
    assert "greet_user" in messages1
    assert "greet_user" not in messages2


if __name__ == "__main__":
    test_function_call_groupchat()
    test_update_function()
