#!/bin/bash

# Load environment variables from core/.env
if [ -f core/.env ]; then
  export $(grep -v '^#' core/.env | xargs)
else
  echo "❌ Missing required file: core/.env (expected to contain ELASTIC_ENDPOINT and ELASTIC_API_KEY)"
  exit 1
fi

# Validate required environment variables
if [[ -z "$ELASTIC_ENDPOINT" || -z "$ELASTIC_API_KEY" ]]; then
  echo "❌ ELASTIC_ENDPOINT or ELASTIC_API_KEY is not set in core/.env"
  exit 1
fi

# Prompt the user only once
echo -e "\nWould you like to execute the curl requests to apply the objects to Elasticsearch (yes),"
read -p "or only preview the generated curl commands without executing them (no)? [yes/no]: " EXECUTE

# Normalize input
EXECUTE=$(echo "$EXECUTE" | tr '[:upper:]' '[:lower:]')

if [[ "$EXECUTE" != "yes" && "$EXECUTE" != "no" ]]; then
  echo "❌ Invalid input. Please enter 'yes' to execute or 'no' to preview only."
  exit 1
fi

echo "🔧 Starting object processing..."

# Root directory for Elasticsearch assets
ROOT_DIR="elasticsearch"

for OBJECT_TYPE_DIR in "$ROOT_DIR"/*; do
  OBJECT_TYPE=$(basename "$OBJECT_TYPE_DIR")

  for FILE in "$OBJECT_TYPE_DIR"/*.json; do
    [ -e "$FILE" ] || continue  # skip if no .json files
    FILE_NAME=$(basename "$FILE")
    OBJECT_NAME="${FILE_NAME%.json}"

    case "$OBJECT_TYPE" in
      index)
        URL="$ELASTIC_ENDPOINT/$OBJECT_NAME"
        ;;
      index_template)
        URL="$ELASTIC_ENDPOINT/_index_template/$OBJECT_NAME"
        ;;
      ingest_pipeline)
        URL="$ELASTIC_ENDPOINT/_ingest/pipeline/$OBJECT_NAME"
        ;;
      *)
        echo "⚠️ Skipping unknown object type: $OBJECT_TYPE"
        continue
        ;;
    esac

    echo -e "\n📄 Processing $OBJECT_TYPE: $OBJECT_NAME"
    echo "Generated curl command:"
    echo "curl -X PUT \"$URL\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -H \"Authorization: ApiKey $ELASTIC_API_KEY\" \\"
    echo "  -d @$FILE"

    if [[ "$EXECUTE" == "yes" ]]; then
      echo -n "→ Executing... "
      STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "$URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: ApiKey $ELASTIC_API_KEY" \
        -d @"$FILE")
      echo "HTTP $STATUS_CODE"
    else
      echo "→ Execution skipped (preview mode only)."
    fi
  done
done

echo -e "\n✅ Script completed."

