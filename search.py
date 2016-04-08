import sys
import getopt
import nltk
import math
import xml.etree.ElementTree as ET
import cPickle as pickle

"""
Loads the postings file by byte pointer linked with the given term in dictionary

Pre-condition: term in dictionary == True

get_postings_list_by_term(str, dict<str:int>, file) -> [(int, float), ...]
"""
def load_postings_by_term(term, dictionary, postings_reader):
    postings_reader.seek(dictionary[term][1])
    return pickle.load(postings_reader)

"""
Given raw query is tokenized and each term's frequency is calculated.
Returns a dictionary that maps each term with its term frequency.
The tokenization involves case-folding and stemming with PorterStemmer object.

tokenize_query -> dict<term:term frequency, ...>
"""
def tokenize_query(raw_query):
    temp = []
    tokenized_query = {}
    stemmer = nltk.stem.porter.PorterStemmer()
    for word in nltk.word_tokenize(raw_query):
        temp.append(str(stemmer.stem(word.lower())))
    temp.sort()
    for term in temp:
        if term in tokenized_query:
            tokenized_query[term] += 1
        else:
            tokenized_query[term] = 1
    return tokenized_query


def vector_length(vector):
    temp = 0
    for term, tf_idf_w in vector:
        temp += pow(tf_idf_w, 2)
    return pow(temp, 1/2)


"""
Processes the raw string query and retrieves at most 10 documents by its ID for the query
that are the most relevant to the query. The returned string is a space-delimitered doc IDs
in the order of relevance from highest to the lowest.

The relevance is determined by the accumulated score of each document's cosine similarity
between its document vector and the query vector. The ranking scheme for the algorithm is
lnc.ltc in SMART notation.

search(dict<str:int>, file, str) -> str
"""
def search_query(title_dictionary, abstract_dictionary, postings_reader, query_file):
    query = ET.parse(query_file).getroot()
    query_title = query.find('title').text
    query_description = query.find('description').text

    # If title is missing, return empty string
    if query_title.strip() == '':
        return ''
    # If description is missing, still query but description is None
    if query_description.strip() == '':
        query_description = None
    score = {}
    query_title_weighted_tf_idf_table_for_title = {}
    query_title_weighted_tf_idf_table_for_abstract = {}
    query_description_weighted_tf_idf_table_for_title = {}
    query_description_weighted_tf_idf_table_for_abstract = {}
    title_doc_length_table = load_postings_by_term("TITLE DOC LENGTH TABLE", title_dictionary, postings_reader)
    abstract_doc_length_table = load_postings_by_term("ABSTRACT DOC LENGTH TABLE", abstract_dictionary, postings_reader)

    query_title_tokens = tokenize_query(query_title)
    query_description_tokens = tokenize_query(query_description)

    # calculating each term's weighted tf-idf in query
    for title_term, qt_frequency in query_title_tokens.iteritems():
        # only calculating score if term is indexed
        tf_w = 1 + math.log(qt_frequency, 10)

        if title_term in title_dictionary:
            idf_in_title = math.log(len(title_doc_length_table) / (title_dictionary[title_term][0] * 1.0), 10)
            query_title_weighted_tf_idf_table_for_title[title_term] = tf_w * idf_in_title

        if title_term in abstract_dictionary:
            idf_in_abstract = math.log(len(abstract_doc_length_table) / (abstract_dictionary[title_term][0] * 1.0), 10)
            query_title_weighted_tf_idf_table_for_abstract[title_term] = tf_w * idf_in_abstract

    for description_term, qd_frequency in query_description_tokens.iteritems():
        # only calculating score if term is indexed
        tf_w = 1 + math.log(qd_frequency, 10)

        if description_term in title_dictionary:
            idf_in_title = math.log(len(title_doc_length_table) / (title_dictionary[description_term][0] * 1.0), 10)
            query_description_weighted_tf_idf_table_for_title[description_term] = tf_w * idf_in_title

        if description_term in abstract_dictionary:
            idf_in_abstract = math.log(len(abstract_doc_length_table) / (abstract_dictionary[description_term][0] * 1.0), 10)
            query_description_weighted_tf_idf_table_for_abstract[description_term] = tf_w * idf_in_abstract

    # calculating query length
    query_title_length_for_title = vector_length(query_title_weighted_tf_idf_table_for_title.iteritems())
    query_title_length_for_abstract = vector_length(query_title_weighted_tf_idf_table_for_abstract.iteritems())
    query_description_length_for_title = vector_length(query_description_weighted_tf_idf_table_for_title.iteritems())
    query_description_length_for_abstract = vector_length(query_description_weighted_tf_idf_table_for_abstract.iteritems())

    # calculating cosine angle between two vectors
    # between tilte query and docs' titles
    title_to_title_matched_ids = set()
    for term, tf_idf_w in query_title_weighted_tf_idf_table_for_title.iteritems():
        title_postings = load_postings_by_term(term, title_dictionary, postings_reader)

        for doc_id, d_tf_w in title_postings:
            if doc_id not in score:
                score[doc_id] = 0
            score[doc_id] += d_tf_w * tf_idf_w / (query_title_length_for_title * title_doc_length_table[doc_id]) * 0.8
            title_to_title_matched_ids.add(doc_id)

    # between tilte query and docs' abstracts
    for term, tf_idf_w in query_title_weighted_tf_idf_table_for_abstract.iteritems():
        abstract_postings = load_postings_by_term(term, abstract_dictionary, postings_reader)

        for doc_id, d_tf_w in abstract_postings:
            if doc_id in title_to_title_matched_ids:
                continue
            if doc_id not in score:
                score[doc_id] = 0
            score[doc_id] += d_tf_w * tf_idf_w / (query_title_length_for_abstract * abstract_doc_length_table[doc_id]) * 0.2

    # between tilte description and docs' abstracts
    description_to_abstracts_matched_ids = set()
    for term, tf_idf_w in query_description_weighted_tf_idf_table_for_abstract.iteritems():
        abstract_postings = load_postings_by_term(term, abstract_dictionary, postings_reader)

        for doc_id, d_tf_w in abstract_postings:
            if doc_id not in score:
                score[doc_id] = 0
            score[doc_id] += d_tf_w * tf_idf_w / (query_description_length_for_abstract * abstract_doc_length_table[doc_id]) * 0.8
            description_to_abstracts_matched_ids.add(doc_id)

    # between tilte description and docs' title
    for term, tf_idf_w in query_description_weighted_tf_idf_table_for_title.iteritems():
        title_postings = load_postings_by_term(term, title_dictionary, postings_reader)

        for doc_id, d_tf_w in title_postings:
            if doc_id in description_to_abstracts_matched_ids:
                continue
            if doc_id not in score:
                score[doc_id] = 0
            score[doc_id] += d_tf_w * tf_idf_w / (query_description_length_for_title * title_doc_length_table[doc_id]) * 0.2

    # sorting by score from most to the least
    result = score.items()
    result.sort(key=lambda docId_score_pair: docId_score_pair[1], reverse=True)

    # TODO: MUST RETURN NULL IF NO PATENTS ARE RELEVANT
    return str(result).strip('[]').replace(',', '')


def main(dictionary_file, postings_file, query_file, output_file):
    (title_dictionary, abstract_dictionary) = pickle.load(open(dictionary_file, "rb"))
    postings_reader = open(postings_file, "rb")
    output = open(output_file, "w")
    result = search_query(title_dictionary, abstract_dictionary, postings_reader, query_file)
    output.write(result)
    output.write('\n')

def usage():
    print "usage: python search.py -d dictionary-file -p postings-file -q query-file -o output-file-of-results"

dictionary_file = postings_file = query_file = output_file =  None
try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except getopt.GetoptError, err:
    usage()
    sys.exit(2)
for o, a in opts:
    if o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        query_file = a
    elif o == '-o':
        output_file = a
    else:
        assert False, "unhandled option"
if query_file == None or output_file == None or dictionary_file == None or postings_file == None:
    usage()
    sys.exit(2)

main(dictionary_file, postings_file, query_file, output_file)