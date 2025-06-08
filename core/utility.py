import configparser
import os, sys, time, json
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from langchain_elasticsearch import ElasticsearchRetriever
from langchain_openai import AzureChatOpenAI
from typing import Dict, TypedDict
from langgraph.graph import StateGraph, END
import pandas as pd
from typing import List

###------------------------------------------------------------------------------
###   Set Environment and Application Variables 
###------------------------------------------------------------------------------
def getEnvVariables():
    load_dotenv()
    
def getConfigData():
    config = configparser.ConfigParser()
   
    config_path = os.path.join(os.path.dirname(__file__),'config.ini')
    if not os.path.isfile(config_path): abortProcess(f"ConfigFile: {config_path} not found")
   
    config.read(config_path)
   
    global elastic_index_name
    global elastic_entity_mapping_index
    global es_client
    global elastic_model_id
    global azure_openai_model_id
    global azure_openai_api_version
    global azure_openai_temperature
    global debug_mode
    global llm
    global local_pdf_store

    try:
        elastic_entity_mapping_index = "entities"
        elastic_index_name = config.get('ELASTIC','INDEX_NAME')
        elastic_model_id = config.get('ELASTIC','MODEL_ID')
        azure_openai_model_id = config.get('AZURE_OPENAI', 'MODEL_ID')
        azure_openai_api_version = config.get('AZURE_OPENAI', 'API_VERSION')
        azure_openai_temperature = config.get('AZURE_OPENAI', 'TEMPERATURE')
        llm = AzureChatOpenAI(azure_deployment=azure_openai_model_id, api_version=azure_openai_api_version,temperature=azure_openai_temperature)
        es_client=Elasticsearch(os.environ.get("ELASTIC_ENDPOINT"), api_key=os.environ.get("ELASTIC_API_KEY"))
        local_pdf_store = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'raw_pdf_data'))
    except Exception as e:
        abortProcess(e)
    
    debug_mode = os.getenv('debug', 'False').lower() in ('true', '1', 't', 'yes')

def validateVariables():
   pass

def abortProcess(msg):
    if 'streamlit' in sys.modules:
        import streamlit as st
        st.error(f"Error: {msg}")
    else:
        print(f"Error: {msg}")
        sys.exit(1)

###----------------------------------------------
### - Default Functions
###----------------------------------------------
es_client = None
getEnvVariables()
getConfigData()
from .agentTemplates import *

###----------------------------------------------
### - Default Functions
###----------------------------------------------
def query_elasticsearch():
    query_body = {
        "aggs": {
            "NAME": {
                "terms": {
                    "field": "entity_name"
                    }
                }
            }
        }
    
        
    response = es_client.search(index=elastic_index_name, body=query_body)
    print(f"Response: {response}")
    sys.stdout.flush()

    
    # Extracting data
    #hits = response.get("aggregations", {}).get("buckets", [])
    hits = response.get("aggregations", {}).get("NAME", {}).get("buckets", [])
    data = [{"entity_name": hit["key"], "count": hit["doc_count"]} for hit in hits]
    
    return pd.DataFrame(data) if data else None

###------------------------------------------------------------------------------
###   Elastic Search 
###------------------------------------------------------------------------------
def getOrCreate_es_client() -> Elasticsearch:
    global es_client
    
    if es_client is None or not es_client.ping():
        try:
            es_client = Elasticsearch(os.environ.get("ELASTIC_ENDPOINT"),
                                      api_key=os.environ.get("ELASTIC_API_KEY"))
        except Exception as e:
            abortProcess(f"unable to establish connection to ElasticSearch : {e}")
    return es_client

def create_index_in_elastic(elastic_index_name):
    if not es_client.indices.exists(index=elastic_index_name):
        mappings = {
            "properties": {
                "content": {
                    "type": "text",
                    "copy_to": [ "semantic_data" ]
                    },
                "audio_id": { "type": "keyword"},
                "semantic_data": {
                    "type": "semantic_text",
                    "inference_id": "my-elser-model",
                    "model_settings": { "task_type": "sparse_embedding" }
                    }
                }
            }
        response=es_client.indices.create(index=elastic_index_name, mappings=mappings)
        return response.get('acknowledged')

def get_all_parent_entity_old(params: dict) -> dict:
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "semantic": {
                            "field": "shareholders_vector",
                            "query": str(params['search_query'])
                        }
                    },
                    {
                        "match": {
                            "shareholders": {
                                "query": str(params['search_query']),
                                "fuzziness": "AUTO",
                                "boost": 3.0
                            }
                        }
                    }
                ]
            }
        }, 
        "size": 0, "min_score": 15,
        "aggs": {
            "distinct_entity_names": {
                "terms": {
                    "field": "entity_name",
                    "size": 100
                }
            }
        }
    }
    
    print(f"get_all_parent_entity ---> {query}")
    return query

def get_all_parent_entity(params: dict) -> dict:
    query = {
        "query": {
            "bool": {
                "must": [
                    {
                        "semantic": {
                            "field": "shareholders_vector",
                            "query": str(params['search_query'])
                        }
                    },
                    {
                        "match": {
                            "shareholders": {
                                "query": str(params['search_query'])
                                #,"boost": 5.0
                            }
                        }
                    },
                    {
                        "match": {
                            "shareholders": {
                                "query": str(params['search_query']),
                                "fuzziness": "AUTO"
                            }
                        }
                    }
                ]
            }
        }, 
        "size": 0, "min_score": 10,
        "aggs": {
            "distinct_entity_names": {
                "terms": {
                    "field": "entity_name",
                    "size": 100
                }
            }
        }
    }
    
    print(f"get_all_parent_entity ---> {query}")
    return query

def query_pdf_pages(params: dict) -> Dict:
    child_entities = params.get("child_entities")
    query = { 
    "query": { 
        "terms": { "entity_name": child_entities }
    },
    "_source": ["entity_name", "pdf_url", "document_name", "page_number"]
    }
    
    response = es_client.search(index=elastic_index_name, body=query)
    
    # Base URL replacement
    new_base_url = "http://localhost:8000/"

    # Extract and transform the data
    results = [
        {
            "document_name": new_base_url + "raw_pdf_data/" + hit["_source"]["document_name"].split("raw_pdf_data/")[-1],
            "page_number": hit["_source"]["page_number"]
        }
        for hit in response["hits"]["hits"]
    ]

    # Sort by document_name and page_number
    results.sort(key=lambda x: (x["document_name"], x["page_number"]))

    formatted_links = [
        f"[{item['document_name'].split('/')[-1]}-{item['page_number']}]({item['document_name']}#page={item['page_number']})"
        for item in results
    ]
    
    return formatted_links

def fetch_all_child_entities(parent_entity: str) -> List[str]:
    """Fetch all child entities for a given parent entity using a wildcard search."""
    query = {
        "query": {
            "wildcard": {
                "parent_entity": {
                    "value": f"*{parent_entity}*",
                    "case_insensitive": True
                }
            }
        },
        "_source": ["parent_entity", "child_entity"]
    }
    
    print(f"parent_entity retrieval query: {query}")
    
    response = es_client.search(index=elastic_entity_mapping_index, body=query)
    
    child_entities = [hit["_source"]["child_entity"] for hit in response.get("hits", {}).get("hits", [])]
    parent_entity = [hit["_source"]["child_entity"] for hit in response.get("hits", {}).get("hits", [])]

    print(f"parent_entity: {parent_entity[0]}")
    print(f"child_entities: {child_entities}")
    
    return parent_entity[0], child_entities

def get_all_shareholders(params: dict) -> Dict:
    """Fetch all shareholders for a given parent entity by first retrieving child entities."""
    parent_entity = params.get("parent_entity")
    
    print(f"parent_entity_query: {parent_entity}")
    
    if not parent_entity:
        return {"error": "parent_entity is required"}
    
    child_entities = fetch_all_child_entities(parent_entity)
    
    if not child_entities:
        return {"error": "No child entities found for the given parent entity"}

    print(f"child_entity_query: {child_entities}")
   
    query = { 
        "query": { 
            "terms": { "entity_name": child_entities }
        },
        #"_source": ["web_url", "pdf_url", "entity_name", "shareholders"]
        "_source": ["entity_name", "shareholders"],
        "sort": [{"page_number": {"order": "asc"}}]
    }

    if debug_mode: 
        print(query)

    return query


def semanting_search_on_shareholders(params: dict) -> Dict:
    query = {
        "retriever": {
            "rrf": {
                "retrievers": [
                    {
                    "standard": {
                        "query": {
                            "match": {"shareholders": params['search_query']}
                            }
                        }
                    },
                    {
                    "standard": {
                        "query": {
                            "semantic": {
                                "field": "shareholders_vector",
                                "query": params['search_query']
                                }
                            }
                        }
                    }],
                "rank_window_size": 50,
                "rank_constant": 20
                }
            },
        "_source": ["shareholders"],
        "size": params['size']
    }
    if debug_mode: print(query)
    return query

def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])

def getOrCreate_retriever(es_query_function):
    print(f"Index Name : {elastic_index_name}")
    retriever = ElasticsearchRetriever(
        es_client=getOrCreate_es_client(),
        index_name=elastic_index_name,
        content_field="shareholders",
        body_func=es_query_function,
        )
    return retriever

def ingest_into_elastic(audio_in, transcribe_pipe, forced_decoder_ids):
    es_client=getOrCreate_es_client()
    
    ### Speech2Text
    speech2text_start_time = time.time()
    textContent=transcribe_pipe(audio_in, generate_kwargs={"forced_decoder_ids": forced_decoder_ids})['text']
    print(f"Feed: {audio_in}, Speech2Text ElaspedTime: {round(time.time() - speech2text_start_time)} seconds\nContent: {textContent}")

    ### Ingesting data into ElasticSearch
    ingest_start_time = time.time()
    doc = {'audio_id': os.path.basename(audio_in),
           'content': textContent
           }
    resp=es_client.index(index=elastic_index_name, body=json.dumps(doc))
    print(f"doc {resp['result']} in elastic, ElaspedTime: {round(time.time() - ingest_start_time)} seconds")
    
def getIndexStructure():
    es_client=getOrCreate_es_client()
    es_client.search
    try:
        return es_client.indices.get_mapping(index=elastic_index_name)
    except Exception as e:
        print(f"Error fetching mapping: {e}")
    