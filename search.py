import sys
import getopt
import nltk
import math
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
def tokenize_query(raw_query, dictionary):
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


"""
Processes the raw string query and retrieves at most 10 documents by its ID for the query
that are the most relevant to the query. The returned string is a space-delimitered doc IDs
in the order of relevance from highest to the lowest.

The relevance is determined by the accumulated score of each document's cosine similarity
between its document vector and the query vector. The ranking scheme for the algorithm is
lnc.ltc in SMART notation.

search(dict<str:int>, file, str) -> str
"""
def search_query(dictionary, postings_reader, raw_query):
    if raw_query == '\n':
        return ''
    top_ten = []
    score = {}
    query_weighted_tf_idf_table = {}
    doc_length_table = load_postings_by_term("DOC LENGTH TABLE", dictionary, postings_reader)
    query_tokens = tokenize_query(raw_query, dictionary)

    # calculating each term's weighted tf-idf in query
    for term, q_frequency in query_tokens.iteritems():
        # only calculating score if term is indexed
        if term in dictionary:
            tf_w = 1 + math.log(q_frequency, 10)
            idf = math.log(len(query_tokens) / (dictionary[term][0] * 1.0), 10)
            query_weighted_tf_idf_table[term] = tf_w * idf

    # calculating query length
    temp = 0
    for term, tf_idf_w in query_weighted_tf_idf_table.iteritems():
        temp += pow(tf_idf_w, 2)
    query_length = pow(temp, 1/2)

    # calculating cosine angle between two vectors
    for term, tf_idf_w in query_weighted_tf_idf_table.iteritems():
        postings = load_postings_by_term(term, dictionary, postings_reader)
        for doc_id, d_tf_w in postings:
            if doc_id in score:
                score[doc_id] += d_tf_w * tf_idf_w / (query_length * doc_length_table[doc_id])
            else:
                score[doc_id] = d_tf_w * tf_idf_w / (query_length * doc_length_table[doc_id])

    # sorting by score in descending order and returning the top 10 result
    result = score.items()
    result.sort(key=lambda docId_score_pair: docId_score_pair[1], reverse=True)
    count = 0
    for doc_id, score in result:
        top_ten.append(doc_id)
        count += 1
        if count == 10:
            break
    return str(top_ten).strip('[]').replace(',', '')

def main(dictionary_file, postings_file, query_file, output_file):
    dictionary = pickle.load(open(dictionary_file, "rb"))
    postings_reader = open(postings_file, "rb")
    output = open(output_file, "w")
    queries = open(query_file, "r").readlines()
    for query in queries:
        result = search_query(dictionary, postings_reader, query)
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