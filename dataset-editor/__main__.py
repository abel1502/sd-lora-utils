from __future__ import annotations
import typing
import pathlib
import argparse

from . import ui


parser = argparse.ArgumentParser(
    description='Image tagging utility'
)

parser.add_argument(
    "-d", "--dataset",
    type=pathlib.Path,
    help="immediately open the specified dataset",
)

parser.add_argument(
    "-p", "--port",
    type=int,
    default=7924,
    help="port to run the webserver on",
)

parser.add_argument(
    "--show",
    action="store_true",
    help="open the browser automatically",
)

parser.add_argument(
    "--dark-mode",
    action="store_true",
    help="start in dark mode"
)


def main() -> None:
    args = parser.parse_args()

    ui.run_ui(
        port=args.port,
        dataset_path=args.dataset,
        show=args.show,
        dark_mode=args.dark_mode,
    )


if __name__ in {'__main__', '__mp_main__'}:
    exit(main())
