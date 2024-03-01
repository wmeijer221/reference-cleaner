import argparse
import logging
import os
from typing import Iterator

from wmeijer_utils.file import iterate_through_files_in_nested_folders

import src.reference_cleaner as reference_cleaner


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


parser = argparse.ArgumentParser()
parser.add_argument("--bibtex", "-b", action="store", dest="bibtex_folder")
parser.add_argument("--latex", "-l", action="store", dest="latex_folder")
parser.add_argument("--output-file", "-o", action="store", dest="output_file")
parser.add_argument(
    "--nested-search-files", action="store_true", dest="nested_search_files"
)
parser.add_argument("--whitelist", "-w", action="store", dest="whitelist")


def __get_folder_contents(folder: str) -> Iterator[str]:
    """Returns contents of a folder."""
    return [f"{folder}/{file}" for file in os.listdir(folder)]


def __get_nested_folder_contents(folder: str) -> Iterator[str]:
    """Returns contents of a folder and all of its subfolders."""
    return iterate_through_files_in_nested_folders(folder, max_depth=10000)


def main():
    args = parser.parse_args()
    logger.info(f"{args=}")

    if args.nested_search_files:
        bibtex_files = __get_nested_folder_contents(args.bibtex_folder)
        latex_files = __get_nested_folder_contents(args.latex_folder)
    else:
        bibtex_files = __get_folder_contents(args.bibtex_folder)
        latex_files = __get_folder_contents(args.latex_folder)

    bibtex_files = list(filter(lambda file: file.endswith(".bib"), bibtex_files))
    latex_files = list(filter(lambda file: file.endswith(".tex"), latex_files))

    reference_cleaner.clean_references(
        bibtex_files, latex_files, args.whitelist, args.output_file
    )


if __name__ == "__main__":
    main()
