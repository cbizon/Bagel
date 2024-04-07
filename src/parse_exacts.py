#ChatGPT wrote this

import json
import csv
from collections import defaultdict

def transform_documents(documents):
    transformed_data = []
    header = ['Abstract ID', 'Term', 'Curie', 'Label', 'Label_SourceRank', 'Class_SourceRank', 'ClassDescription_SourceRank']

    for doc in documents:
        abstract_id = doc['abstract_id']
        bagel_results = doc.get('bagel_results', {})

        for term, results in bagel_results.items():
            curie_label_pairs = defaultdict(lambda: {'label': '', 'label_sources': [], 'class_sources': [], 'class_description_sources': []})

            for method, match_description in results.items():
                exact_matches = match_description.get('exact', [])
                for match in exact_matches:
                    curie = match.get('curie', '')
                    label = match.get('label', '')
                    return_parameters = match.get('return_parameters', [])
                    for return_param in return_parameters:
                        source = return_param.get('source', '')
                        rank = return_param.get('rank', '')
                        curie_label_pairs[curie]['label'] = label
                        if method == 'label':
                            curie_label_pairs[curie]['label_sources'].append(f"{source}_{rank}")
                        elif method == 'class':
                            curie_label_pairs[curie]['class_sources'].append(f"{source}_{rank}")
                        elif method == 'class_description':
                            curie_label_pairs[curie]['class_description_sources'].append(f"{source}_{rank}")

            for curie, data in curie_label_pairs.items():
                transformed_data.append([
                    abstract_id,
                    term,
                    curie,
                    data['label'],
                    ','.join(data['label_sources']),
                    ','.join(data['class_sources']),
                    ','.join(data['class_description_sources'])
                ])

    return transformed_data, header

def write_to_file(data, header, filename):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter='\t')
        writer.writerow(header)
        for row in data:
            writer.writerow(row)

def load_docs():
    docs = []
    for infilename in ["bagel_synonyms_1.jsonl", "bagel_synonyms.jsonl"]:
        with open("bagel_synonyms_1.jsonl") as inf:
            for line in inf:
                docs.append(json.loads(line.strip()))
    return docs

def go():
    documents = load_docs()
    transformed_data, header = transform_documents(documents)
    write_to_file(transformed_data, header, 'transformed_data.tsv')

if __name__ == '__main__':
    go()
