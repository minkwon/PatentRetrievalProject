import sys
import getopt
import nltk
import math
import xml.etree.ElementTree as ET
import cPickle as pickle
from nltk.corpus import wordnet as wn
from nltk.tag import pos_tag

QUERY_DESCRIPTION_PREFIX = "Relevant documents will describe"
ZONE_WEIGHT_SAME = 0.7
ZONE_WEIGHT_CROSS = 0.3
TOP_N_GROUP = 4
INCREMENT_MULTIPLIER = 0.8
TOP_N_RESULT = 2
PRUNE_THRESHOLD = 14

"""
Loads the postings file by byte pointer linked with the given term in dictionary.
The returned objects either are regular postings lists with a list of doc_id, weighted tf pairs,
or special entries that contains different objects which are:

{
"TITLE DOC LENGTH TABLE" : dict<int:float>, a dictionary mapping document id and document length for title
"ABSTRACT DOC LENGTH TABLE" : dict<int:float>, a dictionary mapping document id and document length for abstract
"DOC ID MAP" : dict<int, str>, a dictionary that maps enumerated doc id to the actual doc id
"IPC GROUP DICTIONARY" : dict<int:str> a dictionary that maps enumerated doc id to IPC Group ID
"DIRECTORY_PATH" : str, directory path of corpus
}

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
Any words that contains non-ascii chars are ignored.

tokenize_query -> dict<term:term frequency, ...>
"""
def tokenize_query(raw_query):
	temp = []
	tokenized_query = {}
	stemmer = nltk.stem.porter.PorterStemmer()
	
	''' 
	# for nouns only synonyms
	The approach with this commented code yields a lower score however we thought
	it is still interesting enough to keep the algorithm commented within the code.
    
	This is making use of synonym to do a query expansion provided in NLTK Synset.
	We specifically pick the nouns in synsets because we believe that nouns will
	help us guess the most relevant meanings for a patent information verbs or 
	adjectives do.
    
    #tag what type of word it is and check for nouns later
	tagged_query = pos_tag(nltk.word_tokenize(raw_query))
	
	for word, pos in tagged_query:
		tempList = []
		temp.append(str(stemmer.stem(word.lower())))
		#check if word is a type of noun, if yes, find syn as query expansion
		#for information on tags -> nltk.help.upenn_tagset()
		if (pos == 'NN' or pos == 'NNP' or pos == 'NNS' or pos == 'NNPS'):
			for synset in wn.synsets(word):
				for lemma in synset.lemmas():
					tempList.append(lemma)
		tempList = list(set(tempList))
		for syn in tempList:
			temp.append(str(stemmer.stem(syn.name().lower())))
	'''
	
	for word in nltk.word_tokenize(raw_query):
		# Ignoring any word that contains non-ascii characters
		try:
			word.decode('ascii')
		except UnicodeEncodeError:
			continue
		temp.append(str(stemmer.stem(word.lower())))
	temp.sort()
	for term in temp:
		if term in tokenized_query:
			tokenized_query[term] += 1
		else:
			tokenized_query[term] = 1
	return tokenized_query

"""
Returns the length of a given document vector

vector_length([(str, float), ...]) -> float
"""
def vector_length(vector):
    temp = 0
    for term, tf_idf_w in vector:
        temp += pow(tf_idf_w, 2)
    return pow(temp, 1 / 2)

"""
Processes a query with title and abstract
Return unsorted scores
"""
def perform_search(query_title, query_description, title_dictionary, abstract_dictionary, postings_reader):
    # If title is missing, return empty string
    if query_title.strip() == '':
        return ''
    # If description is missing, still query but description is None
    if query_description.strip() == '':
        query_description = None
    score = {}
	
	# zone weight	
    # use four tables to store the scores for title-title, title-abstract, description-title,
    # description-abstract matchs
    query_title_weighted_tf_idf_table_for_title = {}
    query_title_weighted_tf_idf_table_for_abstract = {}
    query_description_weighted_tf_idf_table_for_title = {}
    query_description_weighted_tf_idf_table_for_abstract = {}
	
	# read documents' part lengths
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
            idf_in_abstract = math.log(
                len(abstract_doc_length_table) / (abstract_dictionary[description_term][0] * 1.0), 10)
            query_description_weighted_tf_idf_table_for_abstract[description_term] = tf_w * idf_in_abstract

    # calculating query length
    query_title_length_for_title = vector_length(query_title_weighted_tf_idf_table_for_title.iteritems())
    query_title_length_for_abstract = vector_length(query_title_weighted_tf_idf_table_for_abstract.iteritems())
    query_description_length_for_title = vector_length(query_description_weighted_tf_idf_table_for_title.iteritems())
    query_description_length_for_abstract = vector_length(
        query_description_weighted_tf_idf_table_for_abstract.iteritems())

    # calculating cosine angle between two vectors
    # between tilte query and docs' titles
    title_to_title_matched_ids = set()
    for term, tf_idf_w in query_title_weighted_tf_idf_table_for_title.iteritems():
        title_postings = load_postings_by_term(term, title_dictionary, postings_reader)

        for doc_id, d_tf_w in title_postings:
            if doc_id not in score:
                score[doc_id] = 0
            score[doc_id] += d_tf_w * tf_idf_w / (query_title_length_for_title * title_doc_length_table[doc_id]) * ZONE_WEIGHT_SAME
            title_to_title_matched_ids.add(doc_id)

    # between tilte query and docs' abstracts
    for term, tf_idf_w in query_title_weighted_tf_idf_table_for_abstract.iteritems():
        abstract_postings = load_postings_by_term(term, abstract_dictionary, postings_reader)

        for doc_id, d_tf_w in abstract_postings:
            if doc_id in title_to_title_matched_ids:
                continue
            if doc_id not in score:
                score[doc_id] = 0
            score[doc_id] += d_tf_w * tf_idf_w / (query_title_length_for_abstract * abstract_doc_length_table[doc_id]) * ZONE_WEIGHT_CROSS

    # between tilte description and docs' abstracts
    description_to_abstracts_matched_ids = set()
    for term, tf_idf_w in query_description_weighted_tf_idf_table_for_abstract.iteritems():
        abstract_postings = load_postings_by_term(term, abstract_dictionary, postings_reader)

        for doc_id, d_tf_w in abstract_postings:
            if doc_id not in score:
                score[doc_id] = 0
            score[doc_id] += d_tf_w * tf_idf_w / (query_description_length_for_abstract * abstract_doc_length_table[doc_id]) * ZONE_WEIGHT_SAME
            description_to_abstracts_matched_ids.add(doc_id)

    # between tilte description and docs' title
    for term, tf_idf_w in query_description_weighted_tf_idf_table_for_title.iteritems():
        title_postings = load_postings_by_term(term, title_dictionary, postings_reader)

        for doc_id, d_tf_w in title_postings:
            if doc_id in description_to_abstracts_matched_ids:
                continue
            if doc_id not in score:
                score[doc_id] = 0
            score[doc_id] += d_tf_w * tf_idf_w / (query_description_length_for_title * title_doc_length_table[doc_id]) * ZONE_WEIGHT_CROSS

    return score

"""
Given an xml query file, the title and description are extracted.
Parameters are sent to perform_search() to obtain scores.
Based on the above results, the top-N documents are read and used as a query.
Scores from both are then consolidated and sorted.

Based on this new score, top-N groups are identified and given a multiplier
This multiplier is then applied to the scores of all documents that belongs to the top-N groups
The scores is sorted for the last time after multipliers and output string is returned
"""
def search_query(title_dictionary, abstract_dictionary, postings_reader, query_file):
    """

    :rtype : dictionary of doc id to query
    """
    query = ET.parse(query_file).getroot()
    query_title = query.find('title').text
    query_description = query.find('description').text.strip()
    if query_description[:len(QUERY_DESCRIPTION_PREFIX)] == QUERY_DESCRIPTION_PREFIX:
        query_description = query_description[len(QUERY_DESCRIPTION_PREFIX):]

    score = perform_search(query_title, query_description, title_dictionary, abstract_dictionary, postings_reader)

    # sorting by score from most to the least
    result = score.items()
    result.sort(key=lambda docId_score_pair: docId_score_pair[1], reverse=True)

    doc_id_map = load_postings_by_term("DOC ID MAP", title_dictionary, postings_reader)
    directory = title_dictionary["DIRECTORY_PATH"]

	# expand the query by using the top TOP_N_RESULT as another n queries
    # added up their resulting scores
    for num in range(0, TOP_N_RESULT):
        if num >= len(result):
            break
        else:
            content = ET.parse(directory + doc_id_map[result[num][0]] + ".xml").getroot()
            title = abstract = None
            for child in content:
                name = child.get("name")
                if name == "Title":
                    title = child.text
                elif name == "Abstract":
                    abstract = child.text
        score_for_new_query = perform_search(title, abstract, title_dictionary, abstract_dictionary, postings_reader)
        for doc_id in score_for_new_query:
            if doc_id in score:
                score[doc_id] += score_for_new_query[doc_id]
            else:
                score[doc_id] = score_for_new_query[doc_id]

    # sorting by score from most to the least
    result = score.items()
    result.sort(key=lambda docId_score_pair: docId_score_pair[1], reverse=True)

    
	
	# Magnifying top N groups with a multiplier
	# This approach is using the assumption that if another patent belonging to 
	# the same group as the current top N results, it should also mean that it is 
	# more likely to be relevant than others not within the same group
	
	# top N category score multiplier
    IPC_group_dictionary = load_postings_by_term("IPC GROUP DICTIONARY", title_dictionary, postings_reader)
    target_id_multiplier = {}	#contains {group:multiplier to be applied}
    multiplied_results = []
    counter = 0
	
    for num in range(TOP_N_GROUP, 0, -1):
        # check if there are any more items to fit N groups
        if counter >= len(result):
            break
        else:
            # resolve group of this top N ranked item
            target_doc_id = result[counter][0]
            counter += 1
            target_group = IPC_group_dictionary[target_doc_id]

            # check if group was already recorded before
            if target_group not in target_id_multiplier:
                target_id_multiplier[target_group] = 1 + (num * INCREMENT_MULTIPLIER)
            else:
				#repeated group, skip
                num += 1

    # apply corresponding multipliers to scores of matching group
    for doc_id, score in result:
        temp_list = []
        if IPC_group_dictionary[doc_id] in target_id_multiplier:
            temp_list.append(doc_id)
            temp_list.append(score * target_id_multiplier[IPC_group_dictionary[doc_id]])
            multiplied_results.append(temp_list)
        else:
            temp_list.append(doc_id)
            temp_list.append(score)
            multiplied_results.append(temp_list)

    # sort again after adjusting scores
    multiplied_results.sort(key=lambda docId_score_pair: docId_score_pair[1], reverse=True)

    resultString = ""
	
	#generate result string
    for doc_id, score in multiplied_results:
		''' # pruning of results based on threshold score
			# this also had a negative impact on the results as it greatly reduces recall
			# and is therefore commented out
		# since scores are sorted, if reaches below threshold, stop appending
		if score < PRUNE_THRESHOLD:
            break
		'''
		resultString += doc_id_map[doc_id] + " "
    return resultString[:-1]


def main(dictionary_file, postings_file, query_file, output_file):
    (title_dictionary, abstract_dictionary) = pickle.load(open(dictionary_file, "rb"))
    postings_reader = open(postings_file, "rb")
    output = open(output_file, "w")
    result = search_query(title_dictionary, abstract_dictionary, postings_reader, query_file)
    output.write(result)
    output.write('\n')


def usage():
    print "usage: python search.py -d dictionary-file -p postings-file -q query-file -o output-file-of-results"


dictionary_file = postings_file = query_file = output_file = None
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
