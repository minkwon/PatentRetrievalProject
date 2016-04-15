import sys
import getopt
import nltk
import os
import math
import xml.etree.ElementTree as ET
import cPickle as pickle

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
# TODO need to rewrite this
def index_documents(directory_file, dictionary_file, postings_file):
    title_hash_index = {}
    abstract_hash_index = {}
    title_list_index = []
    abstract_list_index = []
    IPC_group_dictionary = {}
    stemmer = nltk.stem.porter.PorterStemmer()
    stop_words = nltk.corpus.stopwords.words('english')
    # document's enumerated id is indexed instead of its actual doc id so that it doesn't break
    # the implementation in search.py
    doc_enum_id = 0
    # dictionary that maps enumerated id with the actual doc id
    # { enumerated id : document id }
    doc_id_map = {}
    # parsing an XML file in lexicographical order of doc id
    for doc_id in sorted(os.listdir(directory_file)):
        doc_enum_id += 1
        doc_id_map[doc_enum_id] = doc_id[:-4]
        directory = directory_file + '/' if directory_file[-1] != '/' else directory_file
        # looking for Title and Abstract attribute in the document
        # Note that not all documents have Abstract
        title = abstract = IPC_group_ID = None
        for child in ET.parse(directory + doc_id).getroot().iter():
            if child.get('name') == 'Title':
                title = child.text
            elif child.get('name') == 'Abstract':
                abstract = child.text
            elif child.get('name') == 'IPC Group':
                IPC_group_ID = child.text.strip()

        # Tokenization step for title: case folding, ignoring stop words and stemming
        for sentence in nltk.sent_tokenize(title):
            for word in nltk.word_tokenize(sentence):
                # Ignoring any word that contains non-ascii characters
                try:
                    word.decode('ascii')
                except UnicodeEncodeError:
                    continue
                if word.lower() not in stop_words:
                    term_docID_pair = (str(stemmer.stem(word.lower())), doc_enum_id)
                    title_list_index.append(term_docID_pair)

        # The same for abstract
        if abstract:
            for sentence in nltk.sent_tokenize(abstract):
                for word in nltk.word_tokenize(sentence):
                    # Ignoring any word that contains non-ascii characters
                    try:
                        word.decode('ascii')
                    except UnicodeEncodeError:
                        continue
                    if word.lower() not in stop_words:
                        term_docID_pair = (str(stemmer.stem(word.lower())), doc_enum_id)
                        abstract_list_index.append(term_docID_pair)

        # Keeping track of IPC group id in a dictionary
        IPC_group_dictionary[doc_enum_id] = IPC_group_ID

    # sorting the index by terms while maintaining the doc id order for identical terms
    title_list_index.sort(key=lambda pair: pair[0])
    abstract_list_index.sort(key=lambda pair: pair[0])

    # From here below, doc_id is the document's enumerated id not the actual doc id

    # constructing each postings list [(doc_id, term_frequency), ...]
    # and storing in hash table where the term is the key and value is the postings list
    for term, doc_id in title_list_index:
        # if term already exists in hash index
        if term in title_hash_index:
            # if the term already appeared once before in the same document, increment term frequency
            if doc_id == title_hash_index.get(term)[-1][0]:
                title_hash_index.get(term)[-1][1] += 1
            # if it is the first time seeing the term in the document, append the doc id to the postings list
            else:
                title_hash_index.get(term).append([doc_id, 1])
        # if term does not exist in hash index initialise a postings list
        else:
            title_hash_index[term] = [[doc_id, 1]]

    # The same goes for abstract
    for term, doc_id in abstract_list_index:
        if term in abstract_hash_index:
            if doc_id == abstract_hash_index.get(term)[-1][0]:
                abstract_hash_index.get(term)[-1][1] += 1
            else:
                abstract_hash_index.get(term).append([doc_id, 1])
        else:
            abstract_hash_index[term] = [[doc_id, 1]]

    # converting term frequency to weighted term frequency for title
    for term, postings_list in title_hash_index.iteritems():
        for i, value in enumerate(postings_list):
            # [doc_id, tf] -> (doc_id, tf_weighted)
            postings_list[i] = (value[0], 1 + math.log(value[1], 10))

    # same goes for abstract
    for term, postings_list in abstract_hash_index.iteritems():
        for i, value in enumerate(postings_list):
            # [doc_id, tf] -> (doc_id, tf_weighted)
            postings_list[i] = (value[0], 1 + math.log(value[1], 10))

    # creating a doc length table
    title_doc_length_table = generate_doc_length_table(title_hash_index)
    abstract_doc_length_table = generate_doc_length_table(abstract_hash_index)

    # constructing two dictionaries while saving postings file on-disk
    title_dictionary = {}
    abstract_dictionary = {}

    # both dictionaries will point to the same postings file
    postings_writer = open(postings_file, "wb")
    for term, postings_list in title_hash_index.iteritems():
        # current position of the file pointer
        pointer = postings_writer.tell()
        pickle.dump(postings_list, postings_writer)
        # each entry of dictionary: { term : (doc frequency, pointer to postings_list) }
        title_dictionary[term] = (len(title_hash_index[term]), pointer)

    for term, postings_list in abstract_hash_index.iteritems():
        # current position of the file pointer
        pointer = postings_writer.tell()
        pickle.dump(postings_list, postings_writer)
        # each entry of dictionary: { term : (doc frequency, pointer to postings_list) }
        abstract_dictionary[term] = (len(abstract_hash_index[term]), pointer)

    # Special entries in dictionary. They are uniquely identifiable because other keys are
    # tokenized and case folded so it can never be multiple words or in capitals

    # document length tables
    title_dictionary["TITLE DOC LENGTH TABLE"] = (len(title_doc_length_table), postings_writer.tell())
    pickle.dump(title_doc_length_table, postings_writer)
    abstract_dictionary["ABSTRACT DOC LENGTH TABLE"] = (len(abstract_doc_length_table), postings_writer.tell())
    pickle.dump(abstract_doc_length_table, postings_writer)

    # These two entries will be saved in title_dictionary only.
    # doc id map
    title_dictionary["DOC ID MAP"] = (len(doc_id_map), postings_writer.tell())
    pickle.dump(doc_id_map, postings_writer)
    # IPC group dictionary
    title_dictionary["IPC GROUP DICTIONARY"] = (len(IPC_group_dictionary), postings_writer.tell())
    pickle.dump(IPC_group_dictionary, postings_writer)
    # STORE PATH OF CORPUS
    title_dictionary["DIRECTORY_PATH"] = directory
    postings_writer.close()

    # saving dictionary file on-disk
    dictionary_writer = open(dictionary_file, "w")
    pickle.dump((title_dictionary, abstract_dictionary), dictionary_writer)
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