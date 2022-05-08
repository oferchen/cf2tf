"""Defines classes and methods for creating and interacting with HCL syntax."""


from typing import Any, Dict, List
import re

import logging

log = logging.getLogger("cf2tf")


class Block:
    def __init__(
        self,
        block_type: str,
        labels: List[str],
        arguments: Dict[str, Any],
        valid_arguments: List[str],
        valid_attributes: List[str],
    ) -> None:
        self.block_type = block_type
        self.labels = labels
        self.arguments = arguments
        self.valid_arguments = valid_arguments
        self.valid_attributes = valid_attributes

    def write(self):

        code_block = ""

        code_block += f"{self.block_type} {create_labels(self.labels)} {{\n"

        # code_block += (
        #     f"  // Converted from {self.cf_resource.logical_id} {self.cf_resource.type}"
        # )

        for name, value in self.arguments.items():

            if isinstance(value, dict):
                code_block = code_block + "\n\n" + create_subsection(name, value)
                continue
            code_block = code_block + f"  {name} = {use_quotes(value)}\n"

        code_block += "}\n"

        return code_block


class Variable(Block):
    def __init__(self, name: str, arguments: Dict[str, Any]) -> None:
        self.name = name

        valid_arguments = ["description", "type", "default"]
        super().__init__("variable", [self.name], arguments, valid_arguments, [])

    def write(self):
        text = super().write()

        var_type = self.arguments["type"]

        return text.replace(f'"{var_type}"', var_type)


class Data(Block):
    def __init__(
        self,
        name: str,
        type: str,
        arguments: Dict[str, Any],
        attributes: Dict[str, Any],
    ) -> None:
        self.name = name
        self.type = type
        super().__init__("data", [self.type, self.name], arguments, attributes)


class Resource(Block):
    def __init__(
        self,
        name: str,
        type: str,
        arguments: Dict[str, Any],
        valid_arguments: List[str],
        valid_attributes: List[str],
    ) -> None:
        self.name = name
        self.type = type
        super().__init__(
            "resource",
            [self.type, self.name],
            arguments,
            valid_arguments,
            valid_attributes,
        )


class Output(Block):
    def __init__(self, name: str, arguments: Dict[str, Any]) -> None:
        self.name = name

        valid_arguments = ["description", "value"]
        super().__init__("output", [self.name], arguments, valid_arguments, [])


def create_labels(labels: List[str]):

    label_quotes = [f'"{label}"' for label in labels]

    return " ".join(label_quotes)


def create_subsection(name: str, values: Dict[str, Any], indent_level: int = 1):

    indent = "  " * indent_level

    code_block = f"{indent}{name} {{"

    for name, value in values.items():
        code_block = code_block + f"\n{indent}  {name} = {use_quotes(value)}"

    return code_block + f"\n{indent}}}\n"


def use_quotes(item: str):

    if isinstance(item, dict):
        log.error(f"Found a map when writing a terraform attribute value {item}")
        value: str = next(iter(item))

        if "Fn::" in value or "Ref" in value:
            return str(item)

        return item
        # raise Exception("Found weird map when writing values")

    # Basically if the item references a variable then no quotes

    # Handle this in the future
    if isinstance(item, list):
        return item

    if item.startswith("aws_"):
        return item

    if item.startswith("var."):
        return item

    if is_function(item):
        return item

    return f'"{item}"'


def is_function(item: str):
    regex = r"([a-z]+)\(.*\)"

    matches = re.search(regex, item)

    if matches:
        match = matches.group(1)

        if match in ["join"]:
            return True

    return False