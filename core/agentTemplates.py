import os, re
from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate
from .utility import *
from .promptTemplates import *
from langchain_core.runnables import RunnableLambda
from typing import TypedDict
from langgraph.graph import StateGraph, END

llm = AzureChatOpenAI(azure_deployment=azure_openai_model_id, api_version=azure_openai_api_version,temperature=azure_openai_temperature)

###----------------------------------------------
### - ProcessFlow Graph
###----------------------------------------------
class agent_dataType(TypedDict):
    input: str
    output: str
    pdf_pages: str

def create_processflow_graph():
    workflow = StateGraph(agent_dataType)

    workflow.add_node("router", routerAgent)
    workflow.add_node("ragTree", ragTreeAgent)
    workflow.add_node("rag", ragAgent)
    
    
    workflow.add_conditional_edges(
        "router",
        lambda x: x["output"].split(",")[0].strip().lower(),
        {
            "tree": "ragTree",
            "general": "rag"
        }
    )

    workflow.set_entry_point("router")
    workflow.add_edge("ragTree", END)
    workflow.add_edge("rag", END)

    return workflow.compile()

def processflow_graph_invoke(question):
    processflow_graph = create_processflow_graph()
    return processflow_graph.invoke({"input": question})

###----------------------------------------------
### - Agent Template
###----------------------------------------------
def routerAgent(state):
    prompt = PromptTemplate.from_template(routerPrompt())
    chain = prompt | llm
    response = chain.invoke({"input": state["input"]})
    output = response.content.strip().lower()
    print(f"Router decision: {output}")
    return {"input": state["input"], "output": output}

def ragTreeAgent(state):
    
    # Get Entity Name from the User Input
    prompt = PromptTemplate.from_template(getEntityName())
    
    chain = (
        {"question": RunnableLambda(lambda x: state["input"])}
        | prompt
        | RunnableLambda(lambda x: (print(f"Prompt passed to LLM: {x}") if debug_mode else None) or x)
        | llm  
        )
    if debug_mode: print(f'Fetch Entity Name: {state["input"]}')
    
    parent_entity_response = chain.invoke({"question": state["input"]})
    
    print(f"parent_entity_response : {parent_entity_response.content}")
   
    # Fetch child entities for the Parent and Recursively loop the entities to get individual entity shareholder tree
    parent_entity, child_entities = fetch_all_child_entities(parent_entity_response.content)
    
    treePrompt = PromptTemplate.from_template(ragTreePrompt())
    
    treeContext=""
    for entity_name in child_entities:
        def query_func(params: dict) -> Dict:
            entity_name = params.get("entity_name")
            query = { 
            "query": { 
                "term": { "entity_name": entity_name }
            },
            #"_source": ["web_url", "pdf_url", "entity_name", "shareholders"],
            "_source": ["entity_name", "shareholders"],
            "sort": [{"page_number": {"order": "asc"}}]
            }
            return query
        
        chain = (
            {"context": getOrCreate_retriever(query_func)}
            | treePrompt
            | RunnableLambda(lambda x: (print(f"Prompt passed to LLM: {x}") if debug_mode else None) or x)
            | llm  
            )
        entity_response = chain.invoke({"entity_name" : entity_name})
        
        print(f"LLM Response: {entity_response.content}")
        
        if parent_entity==entity_name:
            print(f"Parent Entity Root Node")
            treeContext += "Root Node:\n" + entity_response.content
        else:
            print(f"Child Entity Child Node")
            treeContext += "\nChild Node:\n" + entity_response.content            
            
    print(f"treeContext: {treeContext}")
    
    # glue all the Tree using LLM
    treePrompt = PromptTemplate.from_template(ragTreeGlueNodePrompt())
    chain = (
        RunnableLambda(lambda _: {"context": treeContext}) 
        | treePrompt
        | RunnableLambda(lambda x: (print(f"Prompt passed to LLM: {x}") if debug_mode else None) or x)
        | llm  
        )
    
    response = chain.invoke({})
    if debug_mode: print(f"ragAgent Output: {response}")
    
    ### Fetch - PDF Pages
    pdf_pages = query_pdf_pages({'child_entities': child_entities})
    print(f"PDF-Pages: {pdf_pages}")

    output_content = response.content if hasattr(response, 'content') else response
    return {
        "output": output_content,  # Main response from LLM
        "pdf_pages": pdf_pages     # Separate response for PDF pages
    }


def ragAgent(state):
    prompt = PromptTemplate.from_template(ragPrompt())
    chain = (
        {"context": getOrCreate_retriever(semanting_search_on_shareholders) | format_docs,
         "question": RunnableLambda(lambda x: state["input"])}
        | prompt
        | RunnableLambda(lambda x: (print(f"Prompt passed to LLM: {x}") if debug_mode else None) or x)
        | llm  
        )
    if debug_mode: print(f'Rag input: {state["output"]}')
    response = chain.invoke({"search_query" : state["input"], "size" : 10})
    if debug_mode: print(f"ragAgent Output: {response}")
    output_content = response.content if hasattr(response, 'content') else response
    return {"output": output_content}