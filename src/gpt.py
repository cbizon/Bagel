import base64
import requests
import os
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

api_key = os.environ.get("OPENAI_API_KEY")

def ask_classes_and_descriptions(text, term, termlist, out_file_path: Optional[str|Path] = None, abstract_id: Optional[int] = None):
    """Get GPT results based only on the labels of the terms."""

    # Get the Labels
    labels = defaultdict(list)
    descriptions = defaultdict(list)
    for curie, annotation in termlist.items():
        labels[(annotation["label"], annotation["biolink_type"])].append(curie)
        descriptions[(annotation["label"], annotation["biolink_type"])].append(annotation["description"])
    synonym_list = [(x[0], x[1], d) for x, d in descriptions.items()]

    # Define the Prompt
    prompt = f""" You are an expert in biomedical vocabularies and ontologies. I will provide you with the abstract to a scientific paper, as well as
    a query term: biomedical entity that occurs in that abstract.  I will also provide you a list of possible synonyms for the query term, along
    with their class as defined within their vocabulary, such as Gene or Disease.  This will help you distinguish between
    entities with the same name such as HIV, which could refer to either a particular virus (class OrganismTaxon) or a disease (class Disease). It can also
    help distinguish between a disease hyperlipidemia (class Disease) versus hyperlipidemia as a symptom of another disease (class PhenotpyicFeature).
    For some entities, I will also provide a description of the entity along with the name and class.
    Please determine whether the query term, as it is used in the abstract, is an exact synonym of any of the terms in the list.  There should be at most one
    exact synonym of the query term.  If there are no exact synonyms for the query term in the list, please look for narrow, broad, or related synonyms, 
    The synonym is narrow if the query term is a more specific form of one of the list terms. For example, the query term "Type 2 Diabetes" would be a 
    narrow synonym of "Diabetes" because it is not an exact synonym, but a more specific form. 
    The synonym is broad if the query term is a more general form of the list term.  For instance, the query term "brain injury" would be a broad synonym
    of "Cerebellar Injury" because it is more generic.
    The synonym is related if it is neither exact, narrow, or broad, but is still a similar enough term.  For instance the query term "Pain" would be
    a related synonym of "Pain Disorder".
    It is also possible that there are neither exact nor narrow synonyms of the query term in the list.
    Provide your answers in the following JSON structure:
    [
        {{ 
            "synonym": ...,
            "vocabulary class": ...,
            "synonymType": ...
        }}
    ]
    where the value for synonym is the element from the synonym list, vocabulary class is the 
    class that I input associated with that synonym, and synonymType is either "exact" or "narrow".

    abstract: {text}
    query_term: {term}
    possible_synonyms_classes_and_descriptions: {synonym_list}
    """

    results = query(prompt)
    
    if out_file_path is not None:
        temp = {}
        temp['abstract_id'] = abstract_id
        temp['term'] = term
        temp['prompt'] = prompt
        temp['output'] = results
        if os.path.isfile(out_file_path):
            with open(out_file_path, "r") as f:
                out = json.load(f)
            out.append(temp)
        else:
            out = [temp]
        with open(out_file_path, "w") as f:
            json.dump(out, f)

    for result in results:
        syn = result['synonym']
        cls = result['vocabulary class']
        syntype = result['synonymType']
        curies = labels[(syn,cls)]
        for curie in curies:
            termlist[curie]["synonym_Type"] = syntype

    grouped_by_syntype = defaultdict(list)
    for curie in termlist:
        syntype = termlist[curie].get("synonym_Type", "unrelated")
        termlist[curie]["curie"] = curie
        grouped_by_syntype[syntype].append(termlist[curie])
    return grouped_by_syntype


def ask_classes(text, term, termlist, out_file_path: Optional[str|Path] = None, abstract_id: Optional[int] = None):
    """Get GPT results based only on the labels of the terms."""

    # Get the Labels
    labels = defaultdict(list)
    for curie, annotation in termlist.items():
        labels[(annotation["label"], annotation["biolink_type"])].append(curie)
    synonym_list = list(labels.keys())

    # Define the Prompt
    prompt = f""" You are an expert in biomedical vocabularies and ontologies. I will provide you with the abstract to a scientific paper, as well as
    a query term: biomedical entity that occurs in that abstract.  I will also provide you a list of possible synonyms for the query term, along
    with their class as defined within their vocabulary, such as Gene or Disease.  This will help you distinguish between
    entities with the same name such as HIV, which could refer to either a particular virus (class OrganismTaxon) or a disease (class Disease). It can also
    help distinguish between a disease hyperlipidemia (class Disease) versus hyperlipidemia as a symptom of another disease (class PhenotpyicFeature).
    Please determine whether the query term, as it is used in the abstract, is an exact synonym of any of the terms in the list.  There should be at most one
    exact synonym of the query term.  If there are no exact synonyms for the query term in the list, please look for narrow, broad, or related synonyms, 
    The synonym is narrow if the query term is a more specific form of one of the list terms. For example, the query term "Type 2 Diabetes" would be a 
    narrow synonym of "Diabetes" because it is not an exact synonym, but a more specific form. 
    The synonym is broad if the query term is a more general form of the list term.  For instance, the query term "brain injury" would be a broad synonym
    of "Cerebellar Injury" because it is more generic.
    The synonym is related if it is neither exact, narrow, or broad, but is still a similar enough term.  For instance the query term "Pain" would be
    a related synonym of "Pain Disorder".
    It is also possible that there are neither exact nor narrow synonyms of the query term in the list.
    Provide your answers in the following JSON structure:
    [
        {{ 
            "synonym": ...,
            "vocabulary class": ...,
            "synonymType": ...
        }}
    ]
    where the value for synonym is the element from the synonym list, vocabulary class is the 
    class that I input associated with that synonym, and synonymType is either "exact" or "narrow".

    abstract: {text}
    query_term: {term}
    possible_synonyms_and_classes: {synonym_list}
    """

    results = query(prompt)
    
    if out_file_path is not None:
        temp = {}
        temp['abstract_id'] = abstract_id
        temp['term'] = term
        temp['prompt'] = prompt
        temp['output'] = results
        if os.path.isfile(out_file_path):
            with open(out_file_path, "r") as f:
                out = json.load(f)
            out.append(temp)
        else:
            out = [temp]
        with open(out_file_path, "w") as f:
            json.dump(out, f)

    for result in results:
        syn = result['synonym']
        cls = result['vocabulary class']
        syntype = result['synonymType']
        curies = labels[(syn,cls)]
        for curie in curies:
            termlist[curie]["synonym_Type"] = syntype

    grouped_by_syntype = defaultdict(list)
    for curie in termlist:
        syntype = termlist[curie].get("synonym_Type", "unrelated")
        termlist[curie]["curie"] = curie
        grouped_by_syntype[syntype].append(termlist[curie])
    return grouped_by_syntype


def ask_labels(text, term, termlist, out_file_path: Optional[str|Path] = None, abstract_id: Optional[int] = None):
    """Get GPT results based only on the labels of the terms."""

    # Get the Labels
    labels = defaultdict(list)
    for curie, annotation in termlist.items():
        labels[annotation["label"]].append(curie)
    synonym_list = list(labels.keys())

    # Define the Prompt
    prompt = f""" You are an expert in biomedical vocabularies and ontologies. I will provide you with the abstract to a scientific paper, as well as
    a query term: biomedical entity that occurs in that abstract.  I will also provide you a list of possible synonyms for the query term.  Please
    determine whether the query term, as it is used in the abstract, is an exact synonym of any of the terms in the list.  There should be at most one
    exact synonym of the query term.  If there are no exact synonyms for the query term in the list, please look for narrow, broad, or related synonyms, 
    The synonym is narrow if the query term is a more specific form of one of the list terms. For example, the query term "Type 2 Diabetes" would be a 
    narrow synonym of "Diabetes" because it is not an exact synonym, but a more specific form. 
    The synonym is broad if the query term is a more general form of the list term.  For instance, the query term "brain injury" would be a broad synonym
    of "Cerebellar Injury" because it is more generic.
    The synonym is related if it is neither exact, narrow, or broad, but is still a similar enough term.  For instance the query term "Pain" would be
    a related synonym of "Pain Disorder".
    It is also possible that there are neither exact nor narrow synonyms of the query term in the list.
    Provide your answers in the following JSON structure:
    [
        {{ 
            "synonym": ...,
            "synonymType": ...
        }}
    ]
    where the value for synonym is the element from the synonym list, and synonymType is either "exact" or "narrow".
                        
    abstract: {text}
    query_term: {term}
    possible_synonyms: {synonym_list}
    """

    results = query(prompt)
    
    if out_file_path is not None:
        temp = {}
        temp['abstract_id'] = abstract_id
        temp['term'] = term
        temp['prompt'] = prompt
        temp['output'] = results
        if os.path.isfile(out_file_path):
            with open(out_file_path, "r") as f:
                out = json.load(f)
            out.append(temp)
        else:
            out = [temp]
        with open(out_file_path, "w") as f:
            json.dump(out, f)

    for result in results:
        syn = result['synonym']
        syntype = result['synonymType']
        curies = labels[syn]
        for curie in curies:
            termlist[curie]["synonym_Type"] = syntype

    grouped_by_syntype = defaultdict(list)
    for curie in termlist:
        syntype = termlist[curie].get("synonym_Type","unrelated")
        termlist[curie]["curie"] = curie
        grouped_by_syntype[syntype].append(termlist[curie])
    return grouped_by_syntype, (prompt, result)

def query(prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": "gpt-4-0125-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    content = response.json()["choices"][0]["message"]["content"]
    chunk = content[content.index("["):(content.rindex("]")+1)]
    output = json.loads(chunk)
    return output
