import os
import json
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from openai import AzureOpenAI

DOC_INT_ENDPOINT = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
DOC_INT_KEY = os.getenv("AZURE_FORM_RECOGNIZER_KEY")

OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

def extract_certificate_details(file_bytes: bytes, filename: str) -> dict:
    if not DOC_INT_ENDPOINT or not DOC_INT_KEY:
        print("Missing Document Intelligence credentials.")
        return {}
        
    try:
        client = DocumentIntelligenceClient(
            endpoint=DOC_INT_ENDPOINT, credential=AzureKeyCredential(DOC_INT_KEY)
        )
        
        print(f"Analyzing document: {filename}...")
        poller = client.begin_analyze_document(
            "prebuilt-layout", 
            body=file_bytes,
            content_type="application/octet-stream"
        )
        result = poller.result()
        extracted_text = result.content
        print("Text extraction complete.")
        
    except Exception as e:
        print(f"Document Intelligence Error: {e}")
        return {}

    if not OPENAI_ENDPOINT or not OPENAI_KEY:
        print("Missing OpenAI credentials.")
        return {}
        
    try:
        print("Sending to Azure OpenAI for parsing...")
        ai_client = AzureOpenAI(
            azure_endpoint=OPENAI_ENDPOINT,
            api_key=OPENAI_KEY,
            api_version=OPENAI_API_VERSION
        )
        
        prompt = f"""
        Extract the following details from this certificate text.
        Text:
        '''
        {extracted_text}
        '''
        
        Respond STRICTLY in JSON format with exactly these keys, no markdown blocks, no extra text:
        {{
            "certification_name": "The full official name of the certification (e.g. 'SnowPro Core Certified', 'Power BI Data Analyst Associate', 'Databricks Certified Data Engineer Associate', 'AWS Certified Solutions Architect'). This is the specific credential title, not just the platform name. Leave blank if not found.",
            "issuer": "The specific issuer or organization (e.g. Snowflake, Microsoft, Databricks, AWS), leave blank if not found",
            "valid_from": "Start date in YYYY-MM-DD format, or null if not found",
            "valid_to": "Expiration date in YYYY-MM-DD format, or null if not found",
            "certificate_id": "The certificate ID or credential ID if present, else null"
        }}
        """
        
        response = ai_client.chat.completions.create(
            model=OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        parsed_data = json.loads(content.strip())
        print(f"Extracted details: {parsed_data}")
        return parsed_data
        
    except Exception as e:
        print(f"OpenAI Parse Error: {e}")
        return {}
