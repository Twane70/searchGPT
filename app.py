from langchain.chat_models import ChatOpenAI
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
#from langchain_core.runnables import RunnablePassthrough
#from langchain.output_parsers.json import SimpleJsonOutputParser

import chainlit as cl
from operator import itemgetter
import json

from utils.agent import choose_agent, queries_agent
from utils.researcher.scraper import get_results, get_context_by_urls

fast_model = ChatOpenAI(streaming=True, temperature=0.0, model_name="gpt-3.5-turbo")
smart_model = ChatOpenAI(streaming=True, temperature=0.0, model_name="gpt-4-1106-preview")

agent_chain = (
    choose_agent()
    | fast_model
    | StrOutputParser()
)

text_chain = (
    choose_agent()
    | smart_model
    | StrOutputParser()
)

def _sanitize(rep: str):
    context = json.loads(rep)
    return context

@cl.on_chat_start
async def on_chat_start():
    runnable = (
        {'question': itemgetter('question'),
         'role': agent_chain}
        | queries_agent()
        | fast_model
        | StrOutputParser()
        #| _sanitize
    )
    cl.user_session.set("runnable", runnable)


@cl.on_message
async def on_message(message: cl.Message):
    runnable = cl.user_session.get("runnable")  # type: Runnable
    main_query = message.content

    msg = cl.Message(content="", disable_human_feedback=True)

    async for chunk in runnable.astream(
        {"question": main_query},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await msg.stream_token(chunk)

    queries = json.loads(msg.content.replace("\n", ""))
    msg.content = ''
    #msg.content = '\n'.join([f'**{query}**\n'+' - \n'*4 for query in queries])
    await msg.update()

    sources = []
    msg = cl.Message(content='', disable_human_feedback=True)
    await msg.send()
    for query in queries:
        source = await get_results(query)
        sources += [{'url':website['href'], 'title':website['title']} for website in source]
        msg.content += f'## **{query}**\n'+'\n'.join(f' - [{website['title']}]({website['href']})' + '\n\n' for website in source)
        await msg.update()
    msg_chuncks = cl.Message(content='', disable_human_feedback=True)
    await msg_chuncks.send()
    content = await get_context_by_urls(' '.join(queries+[main_query]), sources)
    msg_chuncks.content = content
    await msg_chuncks.update()
