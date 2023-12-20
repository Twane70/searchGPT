import json
from langchain.prompts import ChatPromptTemplate
from utils.prompts import auto_agent_instructions, generate_search_queries_prompt, storytelling_instructions


def choose_agent():
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                auto_agent_instructions(),
            ),
            (
                "human", 
                "topic: {question}"
            ),
        ]
    )
# Default Agent : "You are an AI critical thinker research assistant. Your sole purpose is to write well written, critically acclaimed, objective and structured reports on given text."

def queries_agent():
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                '{role}',
            ),
            (
                "human", 
                generate_search_queries_prompt(), #question
            ),
        ]
    )

def write_agent():
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                '{role}\n' + storytelling_instructions(),
            ),
            (
                "human", 
                'topic: {main_query}\n' + 'subtopics: {sub_queries}\n'+'context:\n```\n{context}\n```',
            ),
        ]
    )