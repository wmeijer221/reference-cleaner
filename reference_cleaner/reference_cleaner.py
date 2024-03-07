from enum import Enum
import io
import json
import logging
from typing import Dict, Iterator, List

from wmeijer_utils.file import OpenMany
from wmeijer_utils.collections.safe_dict import SafeDict
from wmeijer_utils.file import iterate_through_files_in_nested_folders


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


_ARTICLE_TYPE_KEY = "__article_type"


def clean_references(
    project_dir: str,
    whitelist: str,
    output_file: str,
):
    # Identifies all latex and bibtex files.
    files = list(iterate_through_files_in_nested_folders(project_dir, max_depth=10000))
    bibtex_files = [file for file in files if file.endswith(".bib")]
    latex_files = [file for file in files if file.endswith(".tex")]

    # Load bibtex files.
    # Index all bibtex entries.
    bibtex_entries = load_bibtex_entries(bibtex_files)

    # Load tex files.
    # Find bibtex references in files.
    # Extract relevant bibtex entries.
    reference_keys = list(bibtex_entries.keys())
    bibtex_references = find_bibtex_references_in_files(latex_files, reference_keys)

    # Extract relevant information from bibtex entries and trace what data is removed.
    bibtex_extract = {key: bibtex_entries[key] for key in bibtex_references}

    # Print some meta data you can easily build a whitelist with.
    _count_fields(bibtex_extract)

    # Filters data with whitelist.
    bibtex_extract = apply_whitelist(bibtex_extract, whitelist)

    # Write bibtex to output file.
    store_bibtex(output_file, bibtex_extract)


def load_bibtex_entries(bibtex_files: Iterator[str]) -> Dict[str, Dict]:
    all_entries = dict()
    with OpenMany(bibtex_files, "r", encoding="utf-8") as bibtex_files:
        for file in bibtex_files:
            file_entries = _load_bibtex_entry(file)
            new_entries = {
                key: value
                for key, value in file_entries.items()
                if key not in all_entries
            }
            all_entries.update(new_entries)
    logger.info(f"Loaded {len(all_entries)} bibtex entries.")
    return all_entries


def _safe_strip_comma(entry: str) -> str:
    if entry.endswith(","):
        return entry[:-1]
    return entry


def format_title(title: str) -> str:
    """Formats the title to adhere with ICSE rules."""
    # Constants.
    UNCAPITALIZED_TERMS = (
        "a",
        "an",
        "and",
        "as",
        "at",
        "but",
        "by",
        "for",
        "in",
        "nor",
        "of",
        "on",
        "or",
        "the",
        "to",
        "up",
    )
    SUBTITLE_ICONS = (":", "-")

    # Function state.
    formatted_title = ""
    is_new_title = True

    # Cleans input.
    title = title.replace("{", "").replace("}", "")

    # Updates each of the terms in the title.
    terms = title.split(" ")
    for term in terms:
        # Every term that is not ignored, or the start of a (sub)title, is capitalized.
        if term not in UNCAPITALIZED_TERMS or is_new_title:
            term = term[0].upper() + term[1:]

        # In terms containing a hypen, only the first character is capitalized.
        parts = term.split("-")
        new_term = parts[0]
        for part in parts[1:]:
            part = part[0].lower() + part[1:]
            new_term = f"{new_term}-{part}"

        # Title is updated.
        formatted_title = f"{formatted_title} {{{new_term}}}"

        # Check if a subtitle has started.
        is_new_title = new_term[-1] in SUBTITLE_ICONS
    formatted_title = f"{{{formatted_title[1:]}}}"

    return formatted_title


def _load_bibtex_entry(bibtex_file: io.IOBase) -> Dict[str, Dict[str, str]]:
    """Loads bibtex entries from a bibtex file."""
    logger.info(f'Extracting bibtex entries from "{bibtex_file.name}".')
    entries = dict()

    class ReadState(Enum):
        ENTRY = 1
        NOTHING = 0

    state = ReadState.NOTHING

    for line in bibtex_file:
        # Searches for a new entry
        if state == ReadState.NOTHING:
            if line.startswith("@"):
                state = ReadState.ENTRY
                article_type, reference_key = line.split("{")
                article_type = article_type.strip()
                reference_key = _safe_strip_comma(reference_key.strip())
                new_entry = dict()
                new_entry[_ARTICLE_TYPE_KEY] = article_type

        # Deals with entry lines.
        elif state == ReadState.ENTRY:
            line = line.strip()
            # We assume the end bracket is ALWAYS on a new line.
            if line == "}":
                state = ReadState.NOTHING
                entries[reference_key] = new_entry

            # We assume '=' isn't used for any other purpose beyond URLs.
            elif "=" in line:
                split = line.split("=")
                field_key = split[0]
                value = "=".join(split[1:])
                field_key = field_key.strip()
                value = _safe_strip_comma(value.strip())
                if field_key == "title":
                    value = format_title(value)
                new_entry[field_key] = value

            # We assume we're still dealing with the previous entry.
            else:
                line = _safe_strip_comma(line)
                old_entry = new_entry[field_key]
                new_entry[field_key] = f"{old_entry} {line}"

    return entries


def find_bibtex_references_in_files(
    latex_files: Iterator[str], bibtex_entry_keys: List[str]
) -> Iterator[str]:
    """Filters out bibtex entries that are not referenced in the provided latex files."""
    references = set()
    with OpenMany(latex_files, "r", encoding="utf-8") as latex_files:
        for file in latex_files:
            file_references = find_bibtex_references_in_file(file, bibtex_entry_keys)
            references = references.union(file_references)
    logger.info(f"Extracted {len(references)} references.")
    return references


def find_bibtex_references_in_file(
    latex_file: io.IOBase, bibtex_entry_keys: List[str]
) -> Iterator[str]:
    """Finds all bibtex references in a latex file."""
    logger.info(f'Extracting references from "{latex_file.name}".')
    references = set()
    for line in latex_file:
        for key in bibtex_entry_keys:
            if key in line:
                references.add(key)
    return references


def apply_whitelist(bibtex_entries: Dict[str, Dict[str, str]], whitelist_file: str):
    with open(whitelist_file, "r", encoding="utf-8") as whitelist_file:
        whitelist = set([entry.strip() for entry in whitelist_file.readlines()])

    logger.info(f"{whitelist=}")

    if len(whitelist) == 0:
        return bibtex_entries

    for key, entry in bibtex_entries.items():
        extract = dict()
        for field_key, value in entry.items():
            field_key = field_key.lower()
            if field_key in whitelist or field_key == _ARTICLE_TYPE_KEY:
                extract[field_key] = value
        bibtex_entries[key] = extract

    return bibtex_entries


def store_bibtex(output_file: str, bibtex_entries: Dict[str, Dict[str, str]]):
    print(f"Writing output to '{output_file}'.")
    with open(output_file, "w+", encoding="utf-8") as output_file:
        sorted_fields = sorted(bibtex_entries.keys())
        for key in sorted_fields:
            entry = bibtex_entries[key]
            output = _build_bibtex_entry_from(key, entry)
            output_file.write(output)


def _build_bibtex_entry_from(key: str, entry: Dict[str, str]) -> str:
    article_type = entry[_ARTICLE_TYPE_KEY]
    # NOTE: This has side effects.
    del entry[_ARTICLE_TYPE_KEY]

    output = f"{article_type}{{{key},"

    sorted_fields = sorted(entry.keys())
    for field_key in sorted_fields:
        value = entry[field_key]
        output = f"{output}\n\t{field_key} = {value},"

    output = f"{output}\n}}\n"

    return output


def _count_fields(bibtex_entries: Dict[str, Dict[str, str]]):
    field_count = SafeDict(0)
    for entry in bibtex_entries.values():
        for key in entry.keys():
            field_count[key] += 1
    del field_count[_ARTICLE_TYPE_KEY]
    logger.info(f"Bibtex field entries:\n{json.dumps(field_count, indent=2)}")
