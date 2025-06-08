import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
from langchain.prompts import PromptTemplate
from .utility import *
from .promptTemplates import *
import logging
logging.basicConfig(level=logging.DEBUG)

def callLLM(prompt_func, input):
    prompt = PromptTemplate.from_template(prompt_func())
    chain = prompt | llm
    response = chain.invoke(input)
    print(response)
    output = response.content.strip()
    return output

def scrapWebPage(web_url):
    # Send GET request to the webpage
    try:
        response = requests.get(web_url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return

    # Parse HTML content
    soup = BeautifulSoup(response.text, 'html.parser')
    
    target_pdf_name=callLLM(getCompanyName, {"soup-data": soup})
    print(f"Target PDF Name: {target_pdf_name}")
    
    pdf_url=callLLM(pickLatestAnnualReportOnly, {"soup-data": soup})
    print(f"PDF URL : {pdf_url}")
    
    return(web_url, pdf_url, target_pdf_name)

def downloadPdf(web_url, pdf_url, target_pdf_name, download_folder=local_pdf_store):

    # Create download folder if it doesn't exist
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)#

    if target_pdf_name:
        pdf_name = f"{target_pdf_name}.pdf"
    else:
        print("ERROR: target_pdf_name not found")
        return None
            
    try:
        pdf_path = os.path.join(download_folder, pdf_name)
        
        print(f"PDF : {pdf_path}")
        pdf_response = requests.get(pdf_url)
        pdf_response.raise_for_status()
            
        with open(pdf_path, 'wb') as f:
            f.write(pdf_response.content)
            print(f"Successfully downloaded: {pdf_name}")
            
    except requests.RequestException as e:
        print(f"Error downloading {pdf_url}: {e}")
    except Exception as e:
        print(f"Error saving {pdf_name}: {e}")
    
    return web_url, pdf_url, pdf_path