from pathlib import Path
from git.repo.base import Repo
from git import RemoteProgress
import logging


from typing import Dict, Any
from thefuzz import process, fuzz

import click


log = logging.getLogger("cf2tf")


class SearchManager:
    def __init__(self, docs_path: Path) -> None:
        self.docs_path = docs_path
        self.resources = list(docs_path.joinpath("r").glob("*.html.markdown"))
        self.datas = list(docs_path.joinpath("d").glob("*.html.markdown"))

    def find(self, name: str) -> Path:

        name = name.replace("::", " ").lower().replace("aws", "").strip()

        # click.echo(f"Searcing for {name} in terraform docs...")

        files = {
            doc_file: doc_file.name.split(".")[0].replace("_", " ")
            for doc_file in self.resources
        }

        resource_name: str
        ranking: int
        doc_path: Path
        resource_name, ranking, doc_path = process.extractOne(
            name.lower(), files, scorer=fuzz.token_sort_ratio
        )

        # click.echo(
        #     f"Best match was {resource_name} at {doc_path} with score of {ranking}."
        # )

        return doc_path


def search_manager():
    docs_dir = "website/docs"

    repo = get_code()

    docs_path = Path(repo.working_dir).joinpath(docs_dir)

    if not docs_path.exists():
        print("The docs path does not exist")

    return SearchManager(docs_path)


def get_code():

    repo_path = Path("/tmp/terraform_src")

    print(f"Cloning Terraform src code to {repo_path}...")

    if repo_path.joinpath(".git").exists():
        # Need to check to make sure the remote is correct
        click.echo(" existing repo found.")
        repo = Repo(repo_path)
        return repo

    # print("cloning ....")

    repo = Repo.clone_from(
        "https://github.com/hashicorp/terraform-provider-aws.git",
        "/tmp/terraform_src",
        depth=1,
        progress=CloneProgress(),
    )
    click.echo(" code has been checked out.")

    return repo


class CloneProgress(RemoteProgress):
    def __init__(self):
        super().__init__()
        self.pbar = None

    def update(self, op_code, cur_count, max_count=None, message=""):
        if not self.pbar and max_count:
            self.create_pbar(int(max_count))

        self.pbar.length = int(max_count)
        self.pbar.update(1)

    def create_pbar(self, max_count):
        self.pbar = click.progressbar(length=max_count)


class Data:
    def __init__(self, name: str, type: str, attributes: Dict[str, Any]) -> None:
        self.name = name
        self.type = type
        self.attributes = attributes

    def write(self):

        code_block = f'data "aws_{self.type}" "{self.name}" {{\n'

        for name, value in self.attributes.items():

            if isinstance(value, dict):
                code_block = code_block + "\n\n" + self.create_subsection(name, value)
                continue
            code_block = code_block + f"\n  {name} = {use_quotes(value)}"

        return code_block + "\n}\n"