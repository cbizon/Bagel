import json
import requests
from requests.adapters import HTTPAdapter, Retry
from collections import defaultdict

from comparator.engines.nameres import NameResNEREngine
from comparator.engines.sapbert import SAPBERTNEREngine

from src.gpt import ask_labels, ask_classes, ask_classes_and_descriptions

import random

def parse_gpt():
    with open("gpt4_parsed.jsonl","w") as outf:
        indir = "../../gpt_output/"
        for input_file in ["abstracts_CompAndHeal_gpt4_20240320_test.json", "abstracts_CompAndHeal_gpt4_20240320_train.json"]:
            fname = indir + input_file
            with open(fname, "r") as file:
                data = json.loads(file.read())
            for datum in data:
                outthing = {}
                lines = datum["prompt"].split("\n")
                for line in lines:
                    if line.startswith("Title: "):
                        outthing["title"] = line[len("Title: "):]
                    if line.startswith("Abstract: "):
                        outthing["abstract"] = line[len("Abstract: "):]
                outthing["abstract_id"] = datum["abstract_id"]
                output = datum["output"]
                intrips = False
                lines = output.split("\n")
                outthing["entities"] = []
                for line in lines:
                    if intrips:
                        try:
                            start = line.index("{")
                            end = line.rindex("}")
                        except:
                            continue
                        jblob = line[start:end+1]
                        triple = json.loads(jblob)
                        outthing["entities"].append({"entity": triple["subject"], "qualifier": triple["subject_qualifier"] })
                        outthing["entities"].append({"entity": triple["object"], "qualifier": triple["object_qualifier"] })
                    elif line.startswith("Core Triples"):
                        intrips = True
                outf.write(json.dumps(outthing)+"\n")

def go():
    session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[ 500, 502, 503, 504, 403 ]
                    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    nameres = NameResNEREngine(session)
    sapbert = SAPBERTNEREngine(session)
    with open("gpt4_parsed.jsonl", "r") as inf:
        lines = inf.readlines()
    random.shuffle(lines)
    taxon_id_to_name = {}
    with open("bagel_synonyms.jsonl","w") as outf:
        for line in lines[:100]:
            paper = json.loads(line)
            abstract = paper["abstract"]
            entities = list(set([e["entity"] for e in paper["entities"]]))
            output_paper = {"abstract": abstract, "abstract_id": paper["abstract_id"], "bagel_results": defaultdict(dict)}
            for term in entities:
                nr_results = nameres.annotate(term, props={}, limit=10)
                sb_results = sapbert.annotate(term, props={}, limit=10)
                # We have results from both nr and sb. But we want to fill those out with consistent information that may
                # or may not be returned from each source
                # First merge the results by identifier (not label)
                terms = defaultdict(lambda: {"return_parameters": []})
                update_by_id(terms, nr_results, "NameRes")
                update_by_id(terms, sb_results, "SAPBert")
                augment_results(terms, nameres, taxon_id_to_name)
                gpt_class_desc_response = ask_classes_and_descriptions(abstract, term, terms)
                gpt_label_response = ask_labels(abstract, term, terms)
                gpt_class_response = ask_classes(abstract, term, terms)
                output_paper["bagel_results"][term]["label"] = gpt_label_response
                output_paper["bagel_results"][term]["class"] = gpt_class_response
                output_paper["bagel_results"][term]["class_description"] = gpt_class_desc_response
            outf.write(json.dumps(output_paper)+"\n")

def augment_results(terms, nameres,taxes):
    """Given a dict where the key is a curie, and the value are data about the match, augment the value with
    results from nameres's reverse lookup.
    For cases where we get back a taxa, add the taxa name to the label of the item."""
    curies = list(terms.keys())
    augs = nameres.reverse_lookup(curies)
    for curie in augs:
        terms[curie].update(augs[curie])
        resp = requests.get("https://nodenormalization-sri.renci.org/get_normalized_nodes?curie="+curie+"&conflate=true&drug_chemical_conflate=true&description=true")
        if resp.status_code == 200:
            result = resp.json()
            try:
                terms[curie]["description"] = result[curie]["id"].get("description","")
            except:
                print("No curie?",curie)
                terms[curie]["description"] = ""
    for curie, annotation in terms.items():
        if len(annotation["taxa"]) > 0:
            tax_id = annotation["taxa"][0]
            if tax_id not in taxes:
                resp = requests.get("https://nodenormalization-sri.renci.org/get_normalized_nodes?curie="+tax_id)
                if resp.status_code == 200:
                    result = resp.json()
                    tax_name = result[tax_id]["id"]["label"]
                    taxes[tax_id] = tax_name
            tax_name = taxes[tax_id]
            annotation["label"] = f"{annotation['label']} ({tax_name})"

def update_by_id(terms, results, source):
    for i,result in enumerate(results):
        r = {}
        #r["label"] = result["label"]
        r["source"] = source
        r["score"] = result["score"]
        r["rank"] = i+1
        identifier = result["id"]
        terms[identifier]["return_parameters"].append(r)
        terms[identifier]["label"] = result["label"]


def update_by_label(terms, results, source):
    for i,result in enumerate(results):
        r = {}
        label = result["label"]
        r["source"] = source
        r["score"] = result["score"]
        r["rank"] = i+1
        r["identifier"] = result["id"]
        terms[label].append(r)

def bagel_it(term):
    session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[ 500, 502, 503, 504, 403 ]
                    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    nameres = NameResNEREngine(session)
    sapbert = SAPBERTNEREngine(session)
    nr_results = nameres.annotate(term, props={}, limit=10)
    sb_results = sapbert.annotate(term, props={}, limit=10)
    terms = defaultdict(list)
    update_by_label(terms, nr_results, "NameRes")
    update_by_label(terms, sb_results, "Sapbert")

if __name__ == "__main__":
    #parse_gpt()
    go()
    #bagel_it("amygdala")


