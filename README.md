Contains code to clean up your Bibtex reference list with.

It takes a Latex project as input, identifies all of the `.bib` files and entries in it.
These entries are cleaned (i.e., only relevant fields are kept; which you filter by specifying a whitelist).
It also cleans up each bibtex entry's title to conform ICSE rules; i.e., it capitalizes all 'main' words, skipping words like 'and', and decapitalizing words with hypens (i.e., 'Project-Based' becomes 'Project-based').
It then iterates through all of the `.tex` files, finding indexing citations, and removing all bibtex entries that are not referenced.
Finally, it outputs a 'clean' `.bib` file.

_Although it's a nice utility, it is not perfect, so you should still do a manual sweep through your reference list._
