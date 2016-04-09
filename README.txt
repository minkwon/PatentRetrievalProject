This is the README file for A0000000X's submission

== General Notes about this assignment ==

Place your comments or requests here for Min to read.  Discuss your
architecture or experiments in general.  A paragraph or two is usually
sufficient.

Feature:

Zone weighting
--------------
T = title
A = abstract
q = query
d = document

Same zone matches are given higher weight than cross-zone matches

Current: 0.6 for same zone, 0.4 for cross zone

<T,q> -> <T,d> gives higher score than <T,q> -> <A,d>

<A,q> -> <T,d> ??? <A,q> -> <A,d>

Document ID enummeration
------------------------
Document's enumumerated id is indexed instead of its actual doc id to
be compatible with the implementations in search.py

Top-N group multipliers
-----------------------
based on tf-idf + zone weighting, scores are sorted.
Thereafter, the top N groups are chosen and given multipliers

Current: Top 2 groups, 0.1 multiplier

1st group = 1.2x, 2nd group = 1.1x



== Files included with this submission ==

List the files in your submission here and provide a short 1 line
description of each file.  Make sure your submission's files are named
and formatted correctly.

== Statement of individual work ==

Please initial one of the following statements.

[X] I, A0000000X, certify that I have followed the CS 3245 Information
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