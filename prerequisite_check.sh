#!/bin/bash

set -e

echo -e "\n🔍 Step 1: Checking if Python virtual environment 'shareholdings-analyst' is active..."

if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "❌ No Python virtual environment is currently active."
    echo "➡️ Please activate the virtual environment: source venvs/shareholdings-analyst/bin/activate"
    exit 1
fi

# Extract just the environment name from path
ENV_NAME=$(basename "$VIRTUAL_ENV")

if [[ "$ENV_NAME" != "shareholdings-analyst" ]]; then
    echo "❌ A virtual environment is active, but it's '$ENV_NAME', not 'shareholdings-analyst'."
    echo "➡️ Please activate the correct environment: source venvs/shareholdings-analyst/bin/activate"
    exit 1
fi

echo "✅ Virtual environment 'shareholdings-analyst' is active."


echo -e "\n🔍 Step 2: Check ElasticSearch connection using the variables from core/.env ..."

# Load environment variables from core/.env
if [ ! -f "core/.env" ]; then
    echo "❌ core/.env file not found."
    exit 1
fi

# Export variables from .env file
export $(grep -E '^ELASTIC_ENDPOINT=|^ELASTIC_API_KEY=' core/.env | xargs)

# Check if both variables are set
if [[ -z "$ELASTIC_ENDPOINT" || -z "$ELASTIC_API_KEY" ]]; then
    echo "❌ ELASTIC_ENDPOINT or ELASTIC_API_KEY is not set in core/.env"
    exit 1
fi

response=$(curl -s -w "\n%{http_code}" -H "Authorization: ApiKey $ELASTIC_API_KEY" "$ELASTIC_ENDPOINT")

# Split response and status code
http_body=$(echo "$response" | head -n 1)
http_code=$(echo "$response" | tail -n 1)

if [[ "$http_code" -ne 200 ]]; then
    echo "❌ Failed to connect to ElasticSearch with:"
    echo "    ELASTIC_ENDPOINT: $ELASTIC_ENDPOINT"
    echo "    ELASTIC_API_KEY : $ELASTIC_API_KEY"
    echo "📄 Error response:"
    echo "$http_body"
    exit 1
fi

echo "✅ Successfully connected to ElasticSearch."

# Proceed to Step 3
echo -e "\n🔍 Step 3: Checking Azure OpenAI environment variables..."

# List of required Azure variables
vars=("AZURE_OPENAI_API_KEY" "AZURE_OPENAI_REGION" "AZURE_OPENAI_ENDPOINT")
missing_vars=()

for var in "${vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Missing the following required Azure OpenAI environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    exit 1
fi

echo "✅ All Azure OpenAI environment variables are set."

echo -e "\n🔍 Step 4: Checking if ELSER inference ENDPOINT is active and responding..."

# Read MODEL_ID from core/config.ini under [ELASTIC] section
MODEL_ID=$(awk -F "=" '/^\[ELASTIC\]/{a=1} a==1 && $1~"MODEL_ID"{gsub(/ /,"",$2); print $2; exit}' core/config.ini)

if [[ -z "$MODEL_ID" ]]; then
    echo "❌ MODEL_ID not found in core/config.ini under [ELASTIC] section"
    exit 1
fi

echo "➡️ Testing ELSER model: $MODEL_ID"

elser_response=$(curl -s -w "\n%{http_code}" -X POST "$ELASTIC_ENDPOINT/_inference/sparse_embedding/$MODEL_ID" \
    -H "Authorization: ApiKey $ELASTIC_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"input": "test"}')

elser_body=$(echo "$elser_response" | head -n 1)
elser_code=$(echo "$elser_response" | tail -n 1)

if [[ "$elser_code" -ne 200 ]]; then
    echo "❌ Failed to connect to ELSER model with:"
    echo "    MODEL_ID: $MODEL_ID"
    echo "📄 Error response:"
    echo "$elser_body"
    exit 1
fi

echo "✅ ELSER model is active and responded successfully."

echo -e "\n🔍 Step 5: Checking if Elastic inference endpoint 'azure_openai_gpt4omini_completion' is active and responding..."

INFERENCE_ID="azure_openai_gpt4omini_completion"

# Send a test request to the inference endpoint
gpt_response=$(curl -s -w "\n%{http_code}" -X POST "$ELASTIC_ENDPOINT/_inference/completion/$INFERENCE_ID" \
    -H "Authorization: ApiKey $ELASTIC_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"input": "test"}')

gpt_body=$(echo "$gpt_response" | head -n 1)
gpt_code=$(echo "$gpt_response" | tail -n 1)

if [[ "$gpt_code" -ne 200 ]]; then
    echo "❌ Failed to reach Elastic inference endpoint:"
    echo "    ID: $INFERENCE_ID"
    echo "📄 Error response:"
    echo "$gpt_body"
    exit 1
fi

echo "✅ Inference endpoint '$INFERENCE_ID' is active and returned a successful response."

echo -e "\n🔍 Step 6: Verifying presence of required index, index template, and ingest pipeline in Elasticsearch..."

# Define expected object names
INDEX_NAME="entities"
TEMPLATE_NAME="raw-annual-report"
PIPELINE_NAME="extract-shareholding-data"

missing_objects=()

# Check if index exists
index_status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: ApiKey $ELASTIC_API_KEY" "$ELASTIC_ENDPOINT/$INDEX_NAME")
if [[ "$index_status" -ne 200 ]]; then
    echo "❌ Index '$INDEX_NAME' does not exist"
    missing_objects+=("index")
else
    echo "✅ Index '$INDEX_NAME' exists"
fi

# Check if index template exists
template_status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: ApiKey $ELASTIC_API_KEY" "$ELASTIC_ENDPOINT/_index_template/$TEMPLATE_NAME")
if [[ "$template_status" -ne 200 ]]; then
    echo "❌ Index template '$TEMPLATE_NAME' does not exist"
    missing_objects+=("index_template")
else
    echo "✅ Index template '$TEMPLATE_NAME' exists"
fi

# Check if ingest pipeline exists
pipeline_status=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: ApiKey $ELASTIC_API_KEY" "$ELASTIC_ENDPOINT/_ingest/pipeline/$PIPELINE_NAME")
if [[ "$pipeline_status" -ne 200 ]]; then
    echo "❌ Ingest pipeline '$PIPELINE_NAME' does not exist"
    missing_objects+=("ingest_pipeline")
else
    echo "✅ Ingest pipeline '$PIPELINE_NAME' exists"
fi

# If any are missing, prompt the user
if [[ ${#missing_objects[@]} -gt 0 ]]; then
    echo -e "\n⚠️ One or more required Elasticsearch objects are missing: ${missing_objects[*]}"
    echo "➡️ Please run: ./create_elasticsearch_objects.sh"
    exit 1
fi

echo -e "\n"