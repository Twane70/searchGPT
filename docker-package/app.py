from langchain.chat_models import ChatOpenAI
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
#from langchain_core.runnables import RunnablePassthrough
#from langchain.output_parsers.json import SimpleJsonOutputParser

import chainlit as cl
from operator import itemgetter
import json
from typing import Optional

from utils.agent import choose_agent, queries_agent, write_agent
from utils.researcher.scraper import get_results, get_context_by_urls
from utils.emoji import get_png_url

fast_model = ChatOpenAI(streaming=True, temperature=0.2, model_name="gpt-3.5-turbo")
smart_model = ChatOpenAI(streaming=True, temperature=0.3, model_name="gpt-4-1106-preview")

@cl.password_auth_callback
def auth_callback(username: str, password: str) -> Optional[cl.AppUser]:
  # Fetch the user matching username from your database
  # and compare the hashed password with the value stored in the database
  if (username, password) == ("admin", "admin"):
    return cl.AppUser(username="trashfr", role="ADMIN", provider="credentials", image="./public/favicon.png")
  else:
    return None

agent_chain = (
    choose_agent()
    | fast_model
    | StrOutputParser()
)

sub_queries_chain = (
    queries_agent()
    | smart_model
    | StrOutputParser()
)

write_chain = (
    write_agent()
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

@cl.author_rename
def rename(orig_author: str):
    rename_dict = {"Chatbot": "Assistant"}
    return rename_dict.get(orig_author, orig_author)

@cl.on_message
async def on_message(message: cl.Message):
    # runnable = cl.user_session.get("runnable")  # type: Runnable
    main_query = message.content

    msg_sources = cl.Message(content='', author='Search', disable_human_feedback=True)
    await msg_sources.send()

    role = agent_chain.invoke({'question': main_query})
    role = json.loads(role)

    queries = sub_queries_chain.invoke({'question': main_query, 'role': role})
    queries = json.loads(queries)

    sources = []
    for query in queries:
        source = await get_results(query)
        sources += [{'url':website['href'], 'title':website['title']} for website in source]
        msg_sources.content += f'## **{query.capitalize()}**\n'
        msg_sources.content += '\n'.join(f' - [{website["title"]}]({website["href"]})' for website in source)

        await msg_sources.update()

    await cl.Avatar(name='Web Search', url='./public/web.png').send()
    msg_chuncks = cl.Message(content='', author='Web Search', disable_human_feedback=True)
    await msg_chuncks.send()

    context_chuncks = await get_context_by_urls(', '.join(queries+[main_query]), sources)
    for id, chunk in enumerate(context_chuncks):
        name_author = f'Source {id+1}'
        await cl.Avatar(name=name_author, url='./public/web.png').send()
        msg_chuncks = cl.Message(content=chunk, author=name_author, disable_human_feedback=True)
        await msg_chuncks.send()
    context = '\n'.join(context_chuncks)

    avat = get_png_url(role[0])
    await cl.Avatar(name=role[1], url=avat).send()

    #write
    msg_write = cl.Message(content="", author=role[1], disable_human_feedback=True)
    await msg_write.send()

    async for chunk in write_chain.astream(
        {'main_query': main_query,
        'sub_queries': ', '.join(queries),
        'context': context,
        'role': role[-1]},
        #config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await msg_write.stream_token(chunk)
    await msg_write.update()
