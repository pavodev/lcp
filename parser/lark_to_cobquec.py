import json
import os
import re
import sys


IGNORE = {"_INDENT", "_DEDENT", "_NL"}


class Ref:
    def __init__(self, name, options={}):
        self.name = name
        self.minItems = (
            int(options.get("minItems")) if options.get("minItems") else None
        )
        self.maxItems = (
            int(options.get("maxItems")) if options.get("maxItems") else None
        )
        self.required = not options.get("optional", False)

    @property
    def propertyName(self):
        name = re.sub(r"__.*", "", self.name)
        name = re.sub(r"_([a-z])", lambda x: x[1].upper(), name)
        return name


class RuleRef(Ref):
    def __init__(self, ruleName, options={}):
        super().__init__(ruleName, options)

    @property
    def type(self):
        if self.minItems:
            return "array"
        assert self.name in all_rules, f"Couldn't find {self.name} in rules"
        # return "object"
        return all_rules[self.name].type

    @property
    def as_object(self):
        o = {"type": self.type}
        if self.minItems or self.maxItems:
            o["items"] = {"$ref": f"#/$defs/{self.name}"}
            if self.minItems:
                o["minItems"] = self.minItems
            if self.maxItems:
                o["maxItems"] = self.maxItems
        else:
            assert self.name in all_rules, f"Couldn't find {self.name} in rules"
            rule = all_rules[self.name]
            print(f"returning {self.name} as an object {rule} - {rule.name}")
            if self.name.endswith("__"):
                o = rule.as_object
            else:
                o = {"type": self.type, "$ref": f"#/$defs/{self.name}"}

        return (o, self.required)


class TermRef(Ref):
    def __init__(self, terminalName, options={}):
        super().__init__(terminalName, options)

    @property
    def type(self):
        if self.minItems:
            return "array"  # Should never happen?
        return "string"

    @property
    def as_object(self):
        assert (
            self.type == "string"
        ), f"Terminal references cannot be of a type other than string ({self.name})"
        return (
            {"type": "string", "pattern": all_terminals[self.name].pattern[1:-1]},
            self.required,
        )


all_rules = dict()


class Rule:
    def __init__(self, name, firstline=None, anonymous=False):
        name = re.sub(r"\.\d+", "", name)
        if anonymous:
            n = 0
            while f"{name}_anonymous_{chr(n+97)}" in all_rules:
                n += 1
            name = f"{name}_anonymous_{chr(n+97)}"
        else:
            assert name not in all_rules, f"Rule name {name} defined more than once"
        self.name = name
        self.lines = []
        if firstline:
            self.addLine(firstline)
        self.references = list()
        self._object = {}
        print("new rule", name)
        all_rules[self.name] = self

    @property
    def propertyName(self):
        name = re.sub(r"__.*", "", self.name)
        name = re.sub(r"_([a-z])", lambda x: x[1].upper(), name)
        return name

    # This is particularly messy; needs to be rewritten
    @property
    def as_object(self):
        if self._object:
            return self._object

        self._object = {"properties": {}, "oneOf": [], "required": []}
        if all(isinstance(r,TermRef) for r in self.references):
            if len(self.references) > 1:
                self._object['type'] = "string"
                self._object['oneOf'] = [r.as_object[0] for r in self.references]
            else:
                self._object, _ = self.references[0].as_object
        elif (
            len(self.references) > 1
        ):  # Big disjunction -- assumption: all disjuncts are named rules
            if self.name.endswith(
                "__"
            ):  # If this is a forwarding rule, the named rules are properties
                for r in self.references:
                    assert isinstance(
                        r[0], Ref
                    ), f"Disjuncts of big disjunctions must all be named rules ({self.name}, {r[0]})"
                    self._object["properties"][r[0].propertyName] = {
                        "type": r[0].type,
                        "$ref": f"#/$defs/{r[0].name}",
                    }
                    if r[0].required:
                        self._object["oneOf"].append({"required": [r[0].propertyName]})
                if not self._object["oneOf"]:
                    self._object.pop("oneOf")
            else:  # If this is not a forwarding rule, return a bare oneOf
                for r in self.references:
                    if not isinstance(r[0], Ref): continue
                    o = {"type": r[0].type, "$ref": f"#/$defs/{r[0].name}"}
                    if r[0].name.endswith("__"):
                        self._object["oneOf"].append(o)
                    else:
                        self._object["properties"][r[0].propertyName] = o
                        self._object["oneOf"].append({"required": [r[0].propertyName]})
        else:
            refs = self.references[0]  # one-line rule
            if isinstance(refs, list):  # the rule does not point to a terminal
                if len(refs) == 1:
                    if isinstance(refs[0], list) and all(
                        isinstance(x, Ref) for x in refs[0]
                    ):
                        for r in refs[0]:
                            o, required = r.as_object
                            self._object["properties"][r.propertyName] = o.get(
                                "properties", o
                            )
                            if required:
                                self._object["oneOf"].append(r.propertyName)
                        if not self._object["oneOf"]:
                            self._object.pop("oneOf")
                    elif isinstance(refs[0], Ref):
                        self._object, required = refs[0].as_object
                        if (
                            required
                            and not refs[0].name.endswith("__")
                            and refs[0].type not in ("string", "array")
                        ):
                            self._object["required"] = [refs[0].propertyName]
                    else:
                        assert (
                            False
                        ), f"Reference {refs[0]} from rule {self.name} of type unhandled"
                elif (
                    len(refs) > 1
                ):  # If there's more than one reference, there *need* to be properties
                    for ref in refs:
                        if isinstance(ref, list):  # Disjunction inside properties
                            for disjunct in ref:
                                array_required = []
                                if isinstance(
                                    disjunct, list
                                ):  # Sequence of properties!
                                    for subref in [
                                        x for x in disjunct if isinstance(x, Ref)
                                    ]:
                                        o, required = subref.as_object
                                        self._object["properties"][
                                            subref.propertyName
                                        ] = o.get("properties", o)
                                        if required:
                                            array_required.append(subref.propertyName)
                                else:
                                    assert isinstance(
                                        disjunct, Ref
                                    ), f"Unhandled reference type {disjunct} in {self.name}"
                                    o, required = disjunct.as_object
                                    self._object["properties"][
                                        disjunct.propertyName
                                    ] = o.get("properties", o)
                                    if required:
                                        array_required.append(disjunct.propertyName)
                                self._object["oneOf"].append(
                                    {"required": array_required}
                                )
                        else:  # Simple property
                            assert isinstance(
                                ref, Ref
                            ), f"Unhandled reference type {disjunct} in {self.name}"
                            o, required = ref.as_object
                            print("simple property from within", self.name, ref.name, o)
                            if (
                                "properties" in o
                            ):  # Forwarding references will themselves return properties
                                for propname, propref in o["properties"].items():
                                    self._object["properties"][propname] = propref
                                for oneOf in o.get("oneOf", []):
                                    self._object["oneOf"].append(oneOf)
                            else:
                                print(
                                    f"adding property {ref.propertyName} to {self.name}",
                                    ref,
                                    o,
                                )
                                # self._object['properties'][ref.propertyName] = {"type":ref.type, "$ref":f"#/$defs/{ref.name}"}
                                self._object["properties"][ref.propertyName] = o
                                if required:
                                    self._object["required"].append(ref.propertyName)
                    # end for refs
            else:
                assert (
                    False
                ), f"Reference {refs} from rule {self.name} of type unhandled"

        for p in ("oneOf", "required", "properties"):
            if p in self._object and not self._object[p]:
                self._object.pop(p)
        return self._object

    @property
    def type(self):
        assert self.references, f"Rule {self.name} has no references!"
        if all( # disjunction of terminal references
            isinstance(r, TermRef) for r in self.references
        ):
            return "string"
        elif len(self.references) > 1:  # big disjunction
            if self.name.endswith(
                "__"
            ):  # forwarding: named disjunct rules count as properties ~> object
                return "object"
            if all(
                r[0].type == "string" for r in self.references if isinstance(r[0], Ref)
            ):
                return "string"
            elif all(
                r[0].type == "array" for r in self.references if isinstance(r[0], Ref)
            ):
                return "array"
            else:
                return "object"
        else:
            refs = self.references[0]
            if isinstance(refs, Ref) and (
                isinstance(refs, TermRef) or refs.name.endswith("__")
            ):
                return refs.type
            elif len(refs) == 1:
                if isinstance(refs[0], list) and len(refs[0]) > 1:
                    return refs[0][0].type
                elif isinstance(refs[0], Ref):
                    return refs[0].type
        return "object"

    def addLine(self, line):
        line = line.strip()  # strip final \n
        for i in IGNORE:
            line = re.sub(
                rf"{i}[^\s)\]]*", "", line
            )  # strip rule names/keywords to ignore
        line = re.sub(r"(^[\s\t]+|[\s\t]+$)", "", line)  # strip all spaces at start/end
        line = re.sub(r"[\s\t]+", " ", line)  # Keep single spaces in the middle
        if line:
            self.lines.append(line)

    def process_references_in_line(self, line):
        line = re.sub(r"[\s\t]+", " ", line)
        line = re.sub(
            r"(?<![a-z_])((\".+\")|[_A-Z]+)[+?*]?(?![a-z])", "", line
        )  # remove literals

        line = re.sub(
            r"\s+([|+?*~\])0-9.])", "\\1", line
        )  # attach closing brackets and repetition flags to previous character
        line = re.sub(
            r"([(\[|~.])\s+", "\\1", line
        )  # attach opening brackets and ~ to next character
        line = re.sub(
            r"([a-z0-9)\]+?*~])([\[(])", "\\1 \\2", line
        )  # insert spaces before opening brackets

        line = re.sub(
            r"(\([^()]+\)|\[[^\[\]]+\])", lambda x: re.sub(r"\s+", "^", x[0]), line
        )  # temporarily paste bracket members with carrets

        continue_on_next = False
        options = dict()
        splitrules = [x for x in line.split(" ") if x]  # discard empty pieces

        refs = []
        for n, piece in enumerate(splitrules):
            if continue_on_next:
                continue_on_next = False
                continue
            # remove any attached literal
            piece = re.sub(r"\".+\"", "", piece)  # remove literals
            # Special case: at least N
            if n + 1 < len(splitrules) and splitrules[n + 1].startswith(piece):
                options["minItems"] = 1
                if splitrules[n + 1] and splitrules[n + 1][-1] == "?":
                    options["maxItems"] = 2
                continue_on_next = True
            # [], ?, *, +, n..m
            if re.match(r"^\[.+\]$", piece):
                options["optional"] = True
                piece = piece[1:-1]
            if piece.endswith("?"):
                options["optional"] = True
                piece = piece[0:-1]
            if piece.endswith("*"):
                options["optional"] = True
                options["minItems"] = 0
                piece = piece[0:-1]
            if piece.endswith("+"):
                options["minItems"] = 1
                piece = piece[0:-1]
            exact_reps = re.match(r"^([a-z_]+)~(\d+)(\.\.(\d+))?$", piece)
            if exact_reps:
                options["minItems"] = exact_reps.group(2)
                options["maxItems"] = exact_reps.group(4) or options["minItems"]
                piece = exact_reps.group(1)

            piece = re.sub(
                "^\((.+)\)$", "\\1", piece
            )  # remove any remaining parentheses

            disjuncts = piece.split("|")
            if len(disjuncts) > 1:
                disjunct_refs = []
                for d in disjuncts:
                    sequents = d.split("^")
                    if len(sequents) == 1:
                        disjunct_refs.append(RuleRef(d, options))
                    else:
                        disjunct_refs.append(
                            [RuleRef(x, options) for x in sequents]
                        )  # append a an array
                refs.append(disjunct_refs)
            elif len(disjuncts) == 1:
                sequents = disjuncts[0].split("^")
                if len(sequents) == 1:
                    refs.append(
                        RuleRef(disjuncts[0], options)
                    )  # no support for repetitions inside disjunctions for now
                else:
                    refs.append(
                        [[RuleRef(x, options) for x in sequents]]
                    )  # append a disjunction whose single member is an array

        return refs

    def build_references(self):
        # Direct reference to a string
        if (
            len(self.lines) == 1
            # and not re.match(r".*\|.*", self.lines[0])
            and not re.match(r".*[a-z].*", self.lines[0])
        ):
            terminal_names = self.lines[0].split('|')
            for terminal_name in terminal_names:
                cleaned_name = re.sub(r"[^A-Z_]+","",terminal_name)
                self.references.append(TermRef(cleaned_name))
        else:
            for line in self.lines:
                self.references.append(self.process_references_in_line(line))


all_terminals = dict()


class Terminal:
    def __init__(self, name, pattern):
        name = re.sub("\.\d+", "", name)
        assert name not in all_terminals, f"Terminal name {name} defined more than once"
        self.name = name
        self.pattern = pattern
        all_terminals[self.name] = self
        print("new terminal", name, pattern)


# Parse a raw line from the LARK file
def parse_line(line, rule):
    terminal = re.match(r"^([A-Z_]+\.?\d*)\s*:\s*(.+)$", line)
    new_rule = re.match(r"^[?]?([a-z_]+)\s*:\s*(.+?)( -> .+)?$", line)
    disjunction = re.match(r"^\s+\|\s*(.+?)( -> .+)?$", line)

    if terminal:
        Terminal(*terminal.groups())
    else:
        name = rule.name if rule else ""
        strrule, alias = (None, None)

        if new_rule:
            name, strrule, alias = new_rule.groups()

        elif disjunction:
            strrule, alias = disjunction.groups()

        else:
            assert False, f"Unrecognized rule line: {line}"

        if alias:
            alias = re.sub(r"\s*->\s*", "", alias)
        if alias and alias != name:
            aliasRule = Rule(alias, strrule)
            if new_rule:
                rule = Rule(name, aliasRule.name)
            else:
                rule.addLine(aliasRule.name)
        elif new_rule:
            rule = Rule(name, strrule)
        else:
            rule.addLine(strrule)

        assert rule, "No rule to start with!"

    return rule


def convert(input_file, output_file=None):
    current_rule = None

    with open(input_file) as f:
        for line in f.readlines():
            if re.match(r"^\s*$", line):
                continue
            if line.startswith("%"):
                continue
            current_rule = parse_line(line, current_rule)

    for _, rule in all_rules.items():
        rule.build_references()

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://liri.linguistik.uzh.ch/cobquec4.schema.json",
        "title": "Constraint-based Query Configuration",
        "description": "A linguistic query for LCP data Representation",
        "type": "object",
        "$defs": {},
    }

    for name, rule in all_rules.items():
        if name == "start":
            schema["properties"] = rule.as_object["properties"]
        else:
            schema["$defs"][name] = rule.as_object

    jsonSchema = json.dumps(schema)

    for name in all_rules.keys():
        if name not in schema["$defs"]:
            continue
        if re.match(rf".*#/\$defs/{name}", jsonSchema):
            continue
        schema["$defs"].pop(name)

    jsd = json.dumps(schema, indent=4)

    if output_file:
        open(output_file, "w").write(jsd)

    print(jsd)

    return jsd


def cmdline() -> None:
    input = next((f for f in sys.argv if f.endswith(".lark")), "")
    output = next((f for f in sys.argv if f.endswith(".json")), "")

    print("input: ", input)
    print("output: ", output)

    assert os.path.isfile(input), f"First argument should be a(n existing) .lark file"

    convert(input, output)


if __name__ == "__main__":
    cmdline()
