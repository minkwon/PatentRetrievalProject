This is the README file for A0148916U-A0133920N-A0125495Y-A0105508M's submission

== General Notes about this assignment ==

Place your comments or requests here for Min to read.  Discuss your
architecture or experiments in general.  A paragraph or two is usually
sufficient.

Feature:

Document ID enummeration
------------------------
Document's enumumerated id is indexed instead of its actual doc id to
be compatible with the implementations in search.py

Zone weighting
--------------
T = title
A = abstract
q = query
d = document

Same zone matches are given higher weight than cross-zone matches
Current: 0.7 for same zone, 0.3 for cross zone
<T,q> -> <T,d> gives higher score than <T,q> -> <A,d>

Document Query based on top-N result
------------------------------------
Based on the score of tf-idf with zone weighting, retrieve and ultilize the top N result as a query
** this requires that the directory containing corpus used during indexing remains ** (Min has assured this)


Top-N group multipliers
-----------------------
based on tf-idf with zone weighting, of both query and top-N result, scores are sorted.
Thereafter, the top-N groups are chosen and given multipliers.
Multipliers are then applied to the result set and sorted for the last time.

Current: Top 4 groups, 0.8 multiplier
1st group = 4.2x, 2nd group = 3.4x, 3rd group = 2.6x, 4th group = 1.8x


Tested but removed features (codes are commented out):

Synonyms for noun query words (query expansion)
-----------------------------------------
If the query word is a noun, find the synonyms of it and add them as part of the query expansion

Pruning threshold
-----------------
If a score falls below the threshold, remove the document as a possible result

-------------------------------------------------------------------------------------------------

Work allocations
----------------

A0148916U - Min Kwon
--------------------
Base Code from HW3
Document ID enummeration
XML processing
Stop words removal
Documentation

A0133920N - Liu Yang
--------------------
Zone weighting
Document Query based on top-N result
Pruning threshold
Documentation

A0125495Y - Gan Wen Jie, Adam
-----------------------------
Top-N group multipliers
Synonyms for noun query words (query expansion)
Documentation

A0105508M - Xu Gelin
--------------------
Code review and bug fixes
Documentation

== Files included with this submission ==

index.py - Indexes the corpus and generates postings file and dictionary file
search.py - Searches through the index with the given query and produces output file
teamname.txt - Simple text file that contains the teamname followed by 27 which denotes
    that the version of python interpreter for the script should be 2.7x


== Statement of individual work ==

Please initial one of the following statements.

[X] I, A0148916U-A0133920N-A0125495Y-A0105508M, certify that I have followed the CS 3245 Information
Retrieval class guidelines for homework assignments.  In particular, I
expressly vow that I have followed the Facebook rule in discussing
with others in doing the assignment and did not take notes (digital or
printed) from the discussions.

[ ] I, A0000000X, did not follow the class rules regarding homework
assignment, because of the following reason:

<Please fill in>

I suggest that I should be graded as follows:

As fairly as anybody in the class who have put in the work individually with honesty.

== References ==
nltk wordnet
http://www.nltk.org/howto/wordnet.html

nltk pos_tag
http://stackoverflow.com/questions/17669952/finding-proper-nouns-using-nltk-wordnet
http://stackoverflow.com/questions/15388831/what-are-all-possible-pos-tags-of-nltk
http://stackoverflow.com/questions/35861482/nltk-lookup-error
http://troublevn.com/265142/nltk-pos-tagging-not-working