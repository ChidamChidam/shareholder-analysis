#prompts={}

def pickLatestAnnualReportOnly():
    prompt="""
Extract the latest annual report URL from the following HTML data.

1. Identify the most recent year in the "Annual Report" section.
2. Extract the corresponding URL from the `<a>` tag inside that year's section.
3. Ensure the URL is **absolute** by prepending the base URL if the extracted URL is relative.
4. Verify that the extracted URL **exists exactly** as written in the HTML.
5. Return the URL **without any modifications to case, encoding, or structure**.
6. If multiple URLs match, return the one with the most recent year.
7. Output **only** the exact URL without additional text.

Here is the HTML data:  
{soup-data}
    """
    return prompt

def getCompanyName():    
    prompt="""
From the HTML data provided, get the company name only with no white space and no special characters, strickly nothing else
{soup-data}
    """
    return prompt

def routerPrompt():
   prompt="""
   You are an AI query classifier for a shareholder information system.
   Your task is to analyze the user's question and classify it into one of the following categories:

   'Tree' → If the query asks for a shareholder ownership structure, hierarchy, or relationship in a tree format.
   'General' → If the query is about shareholder details, ownership percentages, or entity-related facts but does not require a tree.
   Respond with only one of these words: 'Tree' or 'General'. No additional text.
   
   Question : {input}
   Do not attempt to answer questions outside of these rules.
   """
   return prompt

def getEntityName():
   prompt="""
   Return only the entity name from the question.
Example:
Question: but tree for hong leon
Response: hong leon
Do not include any additional text or explanations.
Question : {question}
   """
   return prompt

def ragTreePrompt():
   prompt="""
Create a comprehensive nested hierarchical structure representing the shareholder distribution of [Entity Name] based on the available context.
Incorporate all shareholders from the provided data, even if the information is scattered across different sections.
Do not exclude any shareholder—ensure every available shareholder is captured and categorized correctly.
Structure the data hierarchically, grouping shareholders under relevant sections while preserving relationships.
Common sections may include but are not limited to:
Major Shareholders (or Substantial Shareholders)
Directors and Their Shareholdings
Top Holders of Fully Paid Ordinary Shares
Any other relevant sections present in the context
For each shareholder in any section, include:
Shareholder Name
Number of Shares Held
Percentage of Total Shares Held
If a section is not explicitly mentioned but can be inferred, include it to ensure completeness.
Strictly use only the data provided in the context. If a section or shareholder is missing from the data, do not invent information—simply omit it.
Ensure clarity in hierarchy and accuracy in representation, even if the data is dispersed.

Expected Output Format:
Parent Entity
├── Shareholder 1 - X shares (Y%)
│   ├── Sub-Shareholder 1.1 - A shares (B%)
│   │   ├── Sub-Shareholder 1.1.1 - C shares (D%)
│   │   └── Sub-Shareholder 1.1.2 - E shares (F%)
│   └── Sub-Shareholder 1.2 - M shares (N%)
├── Shareholder 2 - P shares (Q%)
│   ├── Sub-Shareholder 2.1 - R shares (S%)
│   │   ├── Sub-Shareholder 2.1.1 - T shares (U%)
│   │   └── Sub-Shareholder 2.1.2 - V shares (W%)
│   ├── Sub-Shareholder 2.2 - Z shares (AA%)
└── Shareholder 3 - BB shares (CC%)

{context}
"""
   return prompt


def ragTreeGlueNodePrompt():
   prompt="""
Use the provided context to construct a hierarchical tree structure by inserting the child nodes into the root node at the appropriate locations while preserving all content.
1. Ensure that similar entities with minor naming variations are properly merged.
2. Maintain the structure's consistency and wrap the output in backticks (`).
Stricktly use only the data provided in the context
{context}
Please ensure the output is wrapped in backticks and maintains a consistent structure.
   """
   return prompt

def ragPrompt():
   prompt="""
      you are a intelligent AI, refer to the context provided and find specific detail of the shareholder (or) provide the list of all shareholders based on the question
      {context}
      Question: {question}
      """
   return prompt