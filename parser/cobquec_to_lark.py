### TODO
#
#   - When a rule already exists, give it an alias instead of repeating it
#     If an already exists, then we're doomed...

import json
import re

EOF = r'''
%import common.CNAME                                                                -> NAME
%import common.WS_INLINE
%declare _INDENT _DEDENT
%ignore WS_INLINE

_NL: /(\r?\n[\t ]*)+/
'''

KEYWORDS = {
    'context': '("context" _NL [_INDENT context _DEDENT])',
    'entities': '("entities" _NL [_INDENT entities _DEDENT])',
    'entityRef': '(entityRef _NL?)',
    'group': '("group" LABEL_T? group)',
    'plain': '(LABEL_T "=> plain" _NL plain)',
    'statAnalysis': '(LABEL_T "=> analysis" _NL statAnalysis)',
    'collAnalysis': '(LABEL_T "=> collocation" _NL collAnalysis)',
    'resultSets': '(_NL resultSets)',
    'set': '("set" LABEL_T? set)',
    'sequence': '("sequence" LABEL_T? sequence)',
    'statement': '(_NL statement)',
}

class Converter():
    
    def __init__(self, configfile):
        
        f = open(configfile)
        config = json.load(f)
        
        req = config.get("required",[])
        properties = config.get("properties", {})
        
        self.start = "?start: _NL*"
        self.rules = dict()
        self.terminals = dict()
        
        for r in req:
            if r == "comment": continue
            # self.rules[r] = self.parseEntry(r, properties[r], True)
            name = self.parseEntry(r, properties[r], True)
            self.start += f" {name}"
    
        for name,props in config["$defs"].items():
            self.parseEntry(name,props,True)
            
        # Handle the keywords and new lines here
        for r in self.rules:
            for k in KEYWORDS:
                if r == "query" and k == "statement":
                    self.rules[r] = self.rules[r][0] + re.sub(r"\bstatement\b", KEYWORDS['statement'], self.rules[r][1:])
                else:
                    self.rules[r] = re.sub(rf"\b{k}\b", KEYWORDS[k], self.rules[r])
                    
        strrules = "\n".join([f"{r} : {self.rules[r]}" for r in self.rules])
        strterminals = "\n".join([f"{t} : {self.terminals[t]}" for t in self.terminals])
        self.output = f"""
{self.start}

{strrules}

{strterminals}

{EOF}
        """

    def parseEntry(self, name, obj, main=False):
        
        name = re.sub(r"[A-Z]", lambda x: "_"+x[0].lower(), name)
    
        ref = obj.get("$ref", None)
        type = obj.get("type", None)
        enum = obj.get("enum", None)
        pattern = obj.get("pattern", None)
        oneOf = obj.get("oneOf", None)
        items = obj.get("items", None)
        properties = obj.get("properties", None)
        required = obj.get("required", [])
         
        rule = "{rule}"
       
        # Array returns either reference ~ n..m or (literal|literal) ~ n..m
        if type=="array" and items:
            minItems, maxItems = (obj.get("minItems", 1), obj.get("maxItems", None))
            # Two cases: either a ref, or an enum
            item = ""
            if "enum" in items:
                enums = [f'"{e}"' for e in items["enum"]]
                item = f'({"|".join(enums)})'
            elif "$ref" in items:
                item = re.sub(r"[A-Z]", lambda x: "_"+x[0].lower(), items["$ref"].split('/')[-1])
            rule = f"{item} ~ {str(minItems)}"
            if maxItems is None:
                rule += f" {item}*"
            elif maxItems > maxItems:
                rule += f"..{str(maxItems)}"
            # return rule
    
        elif ref:
            reference = re.sub(r"[A-Z]", lambda x: "_"+x[0].lower(), ref.split("/")[-1])
            if name in self.rules:
                n = 2
                while name+chr(n+96) in self.rules: n += 1
                name = name+chr(n+96)
            rule = rule.format(rule=reference)
    
        elif type=="string" and not ref and not enum:
            if not pattern: pattern = ".*"
            rule = rule.format(rule=self.terminal(name,pattern))
        
        elif type=="number":
            rule = rule.format(rule=self.terminal(name,"^\d+(\.\d+)?"))
        
        if name == "statement":
            rule = rule.format(rule="[_INDENT {rule} _DEDENT]")
            # Add the _NL in a post-parse step
        
        if oneOf:
            rule = rule.format(rule="({rule})")
            oneOfArray = []
            
            for n, one in enumerate(oneOf):
                if "required" in one:
                    subArray = []
                    for o in one['required']:
                        assert properties and o in properties, f"'{name}' requires '{o}' but no property found with that name"
                        subArray.append(self.parseEntry(o,properties[o]))
                    oneOfArray.append(f"({'|'.join(subArray)})")
                else:
                    oneOfArray.append(self.parseEntry(f"{name}OneOf{chr(n+97)}",one))
                    
            rule = rule.format(rule=f"{'|'.join(oneOfArray)}")
        
        elif properties:
            if name == "unit":
                # This is hard-coded but ideally cobquec should list the properties in the proper order
                tmp_rule = ""
                sort_props = ('layer','partOf','label','constraints')
                for p in sort_props:
                    if p not in properties: continue
                    if p in required:
                        tmp_rule += f" {self.parseEntry(p,properties[p])}"
                    else:
                        at = '"@"'
                        tmp_rule += f"({at if p=='partOf' else ' '}{self.parseEntry(p,properties[p])})?"
                rule = rule.format(rule=tmp_rule)
                    
            else:
                tmp_rule = ""
                for p in properties:
                    if p not in properties: continue
                    if p == "comment": continue
                    tmp_rule += f" {self.parseEntry(p,properties[p])}{'?' if p not in required else ''}"
                rule = rule.format(rule=tmp_rule)
                    
        elif enum:
            enumNamePrefix = f"{name}Enum"
            enumArray = []
            for n,e in enumerate(enum):
                if isinstance(e, str):
                    enumArray.append(f'"{e}"')
                else:
                    enumArray.append(self.parseEntry(enumNamePrefix+chr(n+97),e))
                    
            rule = rule.format(rule=f"({'|'.join(enumArray)})")
            
            
        if name in self.rules:
            n = 2
            while name+chr(n+96) in self.rules:
                n += 1
            name = name+chr(n+96)
            
        self.rules[name] = rule
        return name
        
        
    def terminal(self,name,pattern):
        name = name.upper() + "_T"
        pattern = "/" + pattern.replace("/","\/") + "/"
        if name in self.terminals:
            if self.terminals[name] == pattern:
                return name
            else:
                n = 2
                while name+chr(n+64) in self.terminals:
                    if self.terminals[name+chr(n+64)] == pattern: return name+chr(n+64)
                    else: n += 1
                self.terminals[name+chr(n+64)] = pattern
                return name+chr(n+64)
        else:
            self.terminals[name] = pattern
            return name