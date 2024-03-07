import argparse
import logging

import reference_cleaner.reference_cleaner as rc


def main(args: argparse.Namespace):
    rc.clean_references(args.project_dir, args.whitelist, args.output_file)


if __name__ == "__main__":
    # Logging config.
    logging.basicConfig()
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # CMD arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", "-d", action="store", dest="project_dir")
    parser.add_argument("--output-file", "-o", action="store", dest="output_file")
    parser.add_argument("--whitelist", "-w", action="store", dest="whitelist")

    args = parser.parse_args()
    logger.info(f"{args=}")

    main(args)
