from elasticsearch import helpers
import PyPDF2, datetime, sys
import traceback
import concurrent.futures
from .utility import *
import logging
logging.basicConfig(level=logging.DEBUG)
    
def extract_entity_name(pages_text, llm):
    """Extract the full company name from the first few pages using LLM, and skip short names."""
    first_pages_text = "\n".join(pages_text[:3])  # Combine first 10 pages' text
    prompt = f"Extract the full company name (not short form) from the following text. Provide only the name, nothing else:\n\n{first_pages_text}"
    
    response = llm.invoke(prompt)
    entity_name = response.content.strip()

    # Check if the company name is less than 5 letters
    if len(entity_name) < 5:
        # If it's short, proceed to the next page (i.e., use the next set of pages)
        next_pages_text = "\n".join(pages_text[3:6])  # Adjust as needed (next set of pages)
        prompt = f"Extract the full company name (not short form) from the following text. Provide only the name, nothing else:\n\n{next_pages_text}"
        response = llm.invoke(prompt)
        entity_name = response.content.strip()

    if entity_name:
        return entity_name
    else:
        return None

def process_page(page_num, page_text):
    print(f"Processing Page {page_num}")
    if not page_text or page_text.strip() == "" or "\n" not in page_text:
        return (page_num, 'no')

    prompt_text = f"Check if the text lists shareholders along with their holding amounts. Return only Yes or No. Strictly do not say anything else.\n\n{page_text}"
    response = llm.invoke(prompt_text)
    
    if response.content.lower() == 'yes' : print(f"Shareholder Information exists in Page : {page_num}")
    return (page_num, response.content.lower())

def parse_pdf_load_to_es(web_url, pdf_url, pdf_input):
    #index_name=f"raw_annual_report_data"
    print(elastic_index_name)
    
    # Check if the input is an uploaded file (Streamlit's UploadedFile)
    if hasattr(pdf_input, 'read'):
        # It's an UploadedFile (Streamlit object)
        try:
            # Read the uploaded file directly as a file-like object
            pdf_reader = PyPDF2.PdfReader(pdf_input)
            pages_text = [page.extract_text() for page in pdf_reader.pages]
        except Exception as e:
            print(f"Error reading PDF: {str(e)}")
            return None
    elif isinstance(pdf_input, str) and os.path.exists(pdf_input):
        # It's a file path, ensure the file exists
        try:
            # Open the file path provided
            with open(pdf_input, 'rb') as file:
                # Create PDF reader object
                pdf_reader = PyPDF2.PdfReader(file)
                pages_text = [page.extract_text() for page in pdf_reader.pages]
        except Exception as e:
            print(f"Error reading PDF: {str(e)}")
            return None

    entity_name = extract_entity_name(pages_text, llm)
    print(f"Company Name is : {entity_name}")
    
    if entity_name is None:
        #print(f"ERROR: Unable to retrieve company Name from the PDF, process failed to parse the PDF")
        #sys.exit()
        raise Exception("Unable to retrieve company name from the PDF. Parsing failed.")

    
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_page = {executor.submit(process_page, i, pages_text[i]): i for i in range(len(pages_text))}

        for future in concurrent.futures.as_completed(future_to_page):
            page_num = future_to_page[future]
            try:
                result = future.result()
                if result:  # Ignore None values (empty pages)
                    results[result[0]] = result[1]
            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
    
    # Create document for each page where shareholder information exists
    documents = []
    for page_num, answer in results.items():
        if answer == "yes":
            doc = {
            'entity_name': entity_name,
            'body': pages_text[page_num],  # Use extracted text
            'web_url': web_url,
            'pdf_url': pdf_url,
            'document_name': pdf_input,
            'page_number': page_num + 1,  # Convert 0-based to 1-based
            'total_pages': len(pages_text),
            'timestamp': datetime.datetime.now().isoformat()
            }
            documents.append(doc)
    print(f"Documents sent to ES : {len(documents)}")
    bulk_upload_to_elastic(documents, es_client, elastic_index_name)
    

def bulk_upload_to_elastic(documents, es, index_name):
    """Bulk upload documents to Elasticsearch"""
    try:
        # Prepare actions for bulk upload
        actions = [
            {
                "_index": index_name,
                "_source": doc,
                "pipeline": 'extract-shareholding-data'
            }
            for doc in documents
        ]
        
        es = es.options(request_timeout=120)
        # Perform bulk upload
        try:
            success, failed = helpers.bulk(es, actions)
            print(f"Successfully uploaded {success} documents")
            
            # Get the company shareholder relation aligned 
            
            # Convert the set to a list before passing it to the query
            #unique_entity_name = list({doc['entity_name'] for doc in documents})
            
            unique_entity_name = documents[0]["entity_name"] if documents else None
            print(f"Unique_entity_name: {unique_entity_name}")
            
            response = es_client.search(index=elastic_index_name, body=json.dumps(get_all_parent_entity({"search_query": str(unique_entity_name)})))
            print(f"Insert this mapping: {response}")
            
            actions = []
            
            actions = [
                {
                "_index": elastic_entity_mapping_index,
                "_id": f"{bucket['key']}_{unique_entity_name}",  # Unique ID to prevent duplicates
                "_op_type": "update",  # Use update instead of create/index
                "doc": {"parent_entity": bucket["key"], "child_entity": unique_entity_name},
                "doc_as_upsert": True  # Insert if not exists, update if exists
                }
                for bucket in response["aggregations"]["distinct_entity_names"]["buckets"]
            ]
            
            actions.append({
                "_index": elastic_entity_mapping_index,
                "_id": f"{unique_entity_name}_{unique_entity_name}",  # Unique ID to prevent duplicates
                "_op_type": "update",
                "doc": {"parent_entity": unique_entity_name, "child_entity": unique_entity_name},
                "doc_as_upsert": True
            })
            
            success, failed = helpers.bulk(es, actions)
            print(f"Successfully uploaded {success} documents to {elastic_entity_mapping_index}")
            
            if failed:
                # print(f"Failed to upload {len(failed)} documents")
                # for i, error in enumerate(failed[:3]):  # Show only the first 3 failures
                #     print(f"\nFailure {i+1}:")
                #     print(json.dumps(error, indent=2))
                raise Exception(f"{failed} documents failed to index in ES.")
        except Exception as e:
            print(e)
    except Exception as e:
        print(traceback.format_exc())