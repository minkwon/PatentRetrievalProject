import sys
import getopt
import nltk
import os
import math
import xml.etree
import cPickle as pickle

"""
Returns integer format of the given string. Used as the key function in
sorted() so that documents are read by the program in numeric order.
"""
def numerical(file_name):
    return int(file_name)


"""
Returns a dictionary that maps doc ID with its document length.
Document length is the magnitude of weighted term frequency vector

generate_doc_length_table(dict<str:[int, ...]>) -> dict<int:>
"""
def generate_doc_length_table(hash_index):
    doc_length_table = {}
    for term, postings_list in hash_index.iteritems():
        for doc_id, weighted_term_frequency in postings_list:
            if doc_id in doc_length_table:
                doc_length_table[doc_id] += pow(weighted_term_frequency, 2)
            else:
                doc_length_table[doc_id] = pow(weighted_term_frequency, 2)

    for doc_id, length in doc_length_table.iteritems():
        doc_length_table[doc_id] = pow(length, 1/2)

    return doc_length_table

"""
Indexing is done in following order:

1. Read the documents in directory_file in numerical order
2. Tokenize the words
3. Sort by terms and by doc id
4. Build postings list where each element in postings list is (doc ID, term frequency) pair
5. Converting term frequency to weighted term frequency
6. Calculate each document's document length and map it in the dictionary <doc ID : document length>
7. Construct dictionary while saving the postings on disk
    and record the byte offset in the dictionary to be used as a pointer to the matching postings
8. Include a special key "DOC LENGTH TABLE" and map it with the document length dictionary
9. Save the dictionary on disk

Processing the documents in doc id order helps because the order by doc id is
preserved even after sorting the index by terms as sort() is guaranteed to be
stable since Python 2.2

index_documents(str, str, str) -> None
"""
def index_documents(directory_file, dictionary_file, postings_file):
    hash_index = {}
    list_index = []
    stemmer = nltk.stem.porter.PorterStemmer()
    # list of all doc ids, to help unary NOT operation in search
    doc_id_list = []

    # TODO CHANGE TO RETRIEVE XML

    # tokenizing
    for doc_id in sorted(os.listdir(directory_file), key=numerical):
        for sentence in nltk.sent_tokenize(open(directory_file + doc_id, "r").read()):
            for word in nltk.word_tokenize(sentence):
                term_docID_pair =  (str(stemmer.stem(word.lower())), int(doc_id))
                list_index.append(term_docID_pair)

    # sorting the index by terms while maintaining the doc id order
    list_index.sort(key=lambda pair: pair[0])

################################################
    # TODO MAKE TERM TO (TERM, NUM)
    # constructing each postings list [(doc_id, term_frequency), ...]
    # and storing in hash table where the term is the key
    for term, doc_id in list_index:
        if term in hash_index:
            if doc_id == hash_index.get(term)[-1][0]:
                hash_index.get(term)[-1][1] += 1
            else:
                hash_index.get(term).append([doc_id, 1])
        else:
            hash_index[term] = [[doc_id, 1]]

    # converting term frequency to
    #  weighted term frequency
    for term, postings_list in hash_index.iteritems():
        for i, value in enumerate(postings_list):
            # [doc_id, tf] -> (doc_id, tf_weighted)
            postings_list[i] = (value[0], 1 + math.log(value[1], 10))

    doc_length_table = generate_doc_length_table(hash_index)

    # constructing dictionary while saving postings file on-disk
    dictionary = {}
    postings_writer = open(postings_file, "wb")
    for term, postings_list in hash_index.iteritems():
        # current position of the file pointer
        pointer = postings_writer.tell()
        pickle.dump(postings_list, postings_writer)
        # each entry of dictionary: { term : (doc frequency, pointer to postings_list) }
        dictionary[term] = (len(hash_index[term]), pointer)

    # special entry for document lengths hash table
    dictionary["DOC LENGTH TABLE"] = (-1, postings_writer.tell())
    pickle.dump(doc_length_table, postings_writer)
    postings_writer.close()

    # saving dictionary file on-disk
    dictionary_writer = open(dictionary_file, "w")
    pickle.dump(dictionary, dictionary_writer)
    dictionary_writer.close()

def usage():
    print "usage: python index.py -i directory-of-documents -d dictionary-file -p postings-file"

directory_file = dictionary_file = postings_file = None
try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
except getopt.GetoptError, err:
    usage()
    sys.exit(2)
for o, a in opts:
    if o == '-i':
        directory_file = a
    elif o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    else:
        assert False, "unhandled option"
if directory_file == None or dictionary_file == None or postings_file == None:
    usage()
    sys.exit(2)

index_documents(directory_file, dictionary_file, postings_file)