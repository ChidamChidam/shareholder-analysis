# Shareholdings Analysis: Multi-Agent RAG Workflow

## Prerequisites

1. [Elastic Cloud](https://cloud.elastic.co/registration?elektra=en-ess-sign-up-page)
    1. Create a [Hosted Deployment](https://www.elastic.co/guide/en/cloud/current/ec-create-deployment.html) (or) a [Serverless Project](https://www.elastic.co/docs/current/serverless/general/sign-up-trial)
    2. Create [ElasticSearch Cluster API KEY](https://www.elastic.co/guide/en/kibana/current/api-keys.html)
    3. Create [ELSER inference endpoint](https://www.elastic.co/guide/en/elasticsearch/reference/current/infer-service-elser.html)
2. [Azure OpenAI LLM](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/create-resource?pivots=web-portal) - EndPoint, Region, API Key, Version, ModelID
3. Python 3.12.6 or later

## Installation Steps

1. Clone this repo

2. Set the Python Environment
    ```bash
    python3 -m venv shareholdings-analyst
    source shareholdings-analyst/bin/activate
    pip install -r requirements.txt
    ```
3. create "./core/.env" file and populate. you can use './core/.env.sample' as a example file
    ```bash
    ELASTIC_ENDPOINT="<Elastic Cloud EndPoint of your Deployment">
    ELASTIC_API_KEY="<ElasticSearch Cluster API Key that you created in your Deployment>"
    ```

4. Export AZURE_OPENAI variables
    ```bash
    # Export these variables in the current shell (or) put them in a shell script and source it in the current shell

    AZURE_OPENAI_API_KEY="<Azure OpenAI API Key>"
    AZURE_OPENAI_REGION="<Azure OpenAI Region>"
    AZURE_OPENAI_ENDPOINT="<Azure OpenAI Model Deployment Endpoint>"
    ```
5. Create Elastic Inference Enpoint for ELSER and put that name in core/config.ini

6. Create Elastic Inference Enpoint for AZURE OpenAI - 
    ```bash
    # Ensure the name of the inference endpoint is azure_openai_gpt4omini_completion

    PUT _inference/completion/azure_openai_gpt4omini_completion
    {
        "service": "azureopenai",
        "service_settings": {
            "api_key": "<Azure OpenAI API Key>",
            "resource_name": "<Azure OpenAI Resource Name>",
            "deployment_id": "gpt-4o-mini",
            "api_version": "2023-06-01-preview"
        }
    }
    ```

7. Populate config.ini, you can also opt to go with the default config.ini settings
    ```bash
    [ELASTIC]
    INDEX_NAME="<Elastic Index Name>"
    MODEL_ID="<Elastic ELSER Inference ID>"

    [AZURE_OPENAI]
    MODEL_ID="<Azure OpenAI Model that you have deployed'>"
    API_VERSION="<Azure OpenAI Model version>"
    TEMPERATURE=0
    ```

8. Run ./prerequisite_check.sh to ensure all prerequist actions are done 

    ```bash
    # Sample run log
    (shareholdings-analyst) CC-MacBook:ShareHoldingsAnalyst:$ ./prerequisite_check.sh 
    
    🔍 Step 1: Checking if Python virtual environment 'shareholdings-analyst' is active...
    ✅ Virtual environment 'shareholdings-analyst' is active.

    🔍 Step 2: Check ElasticSearch connection using the variables from core/.env ...
    ✅ Successfully connected to ElasticSearch.

    🔍 Step 3: Checking Azure OpenAI environment variables...
    ✅ All Azure OpenAI environment variables are set.

    🔍 Step 4: Checking if ELSER inference ENDPOINT is active and responding...
    ➡️ Testing ELSER model: my-elser-model
    ✅ ELSER model is active and responded successfully.

    🔍 Step 5: Checking if Elastic inference endpoint 'azure_openai_gpt4omini_completion' is active and responding...
    ✅ Inference endpoint 'azure_openai_gpt4omini_completion' is active and returned a successful response.

    🔍 Step 6: Verifying presence of required index, index template, and ingest pipeline in Elasticsearch...
    ✅ Index 'entities' exists
    ✅ Index template 'raw-annual-report' exists
    ✅ Ingest pipeline 'extract-shareholding-data' exists
    
    (shareholdings-analyst) CC-MacBook:ShareHoldingsAnalyst:$
    ```
## Running the Application

There are two ways to access the app
1. Start the Streamlit WebApp
    ```bash
    # Start the Streamlit App
    streamlit run main.py
    ```

2. On another terminal run the following 
    ```bash
    # Set the Python virtual environment
    source shareholdings-analyst/bin/activate
    
    # To kickstart a http server - for accessing local documents
    python -m http.server 8000
    ```