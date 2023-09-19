import json
import random
import re
import string

DEFAULT_STRING_PATTERN = "[a-zA-Z_][a-zA-Z0-9_\.]*"

EOF = r'''
%import common.CNAME                                                                -> NAME
%import common.WS_INLINE
%declare _INDENT _DEDENT
%ignore WS_INLINE

_NL: /(\r?\n[\t ]*)+/
'''

KEYWORDS = {
    'attributes': {
        'substitute': '("attributes" _NL [_INDENT {} _DEDENT])',  
    },
    'center': {
        'substitute': '("center" _NL [_INDENT {} _NL* _DEDENT])',  
    },
    'context': {
        'substitute': '("context" _NL [_INDENT {} _DEDENT])',
    },
    'entities':  {
        'substitute': '("entities" _NL [_INDENT {} _DEDENT])',
    },
    'entityComparison': {
        'substitute': '{} _NL',
        'from': '$defs'
    },
    # 'entityRef':  {
    #     'substitute': '({} _NL?)',
    #     'from': '$defs'
    # },
    'filter': {
        'substitute': '("filter" _NL [_INDENT {} _DEDENT])',  
    },
    'function': {
        'substitute': '("function" _NL [_INDENT {} _DEDENT])',  
    },
    'group':  {
        'substitute': '("group" {})',
        'from': '$defs'
    },
    'mathComparison': {
        'substitute': '{} _NL',
        'from': '$defs'
    },
    'members': {
        'substitute': '(_NL [_INDENT {} _DEDENT])',
    },
    'resultSetPlain':  {
        'substitute': '("plain" _NL [_INDENT {} _DEDENT])',
        'from': '$defs'
    },
    'resultSetStatAnalysis':  {
        'substitute': '("analysis" _NL [_INDENT {} _DEDENT])',
        'from': '$defs'
    },
    'resultSetCollAnalysis':  {
        'substitute': '("collocation" _NL [_INDENT {} _DEDENT])',
        'from': '$defs'
    },
    # 'resultSet':  {
    #     'substitute': '(_NL {})',
    #     'from': '$defs'
    # },
    'set':  {
        'substitute': '("set" {})',
        'from': '$defs'
    },
    'sequence':  {
        'substitute': '("sequence" {})',
        'from': '$defs'
    },
    'stringComparison': {
        'substitute': '{} _NL',
        'from': '$defs'
    },
    "stringRegexComparison": {
        'substitute': '{} _NL',
        'from': '$defs'
    },
    'space': {
        'substitute': '("space" _NL [_INDENT {} _NL* _DEDENT])',  
    },
    'window': {
        'substitute': '("window" _NL [_INDENT {} _DEDENT])',  
    }
}

uuids = set()

class Rule():
    
    def __init__(self,
                 converter,
                 name,
                 obj,
                 isDefinition=False
    ):

        self.name = name
        # 2 random lowercase letters should be enough (26*26 possibilities)
        self.uuid = ''.join(random.choices(string.ascii_letters[0:26], k=2))
        while self.name + self.uuid in uuids:
            self.uuid = ''.join(random.choices(string.ascii_letters[0:26], k=2))
        uuids.add(self.name + self.uuid)
        self.obj = obj
        self.isDefinition = isDefinition
        self.converter = converter
        self.references = []
        
    
    def build(self):
        
        # name = re.sub(r"[A-Z]", lambda x: "_"+x[0].lower(), name)
        
        ref = self.obj.get("$ref", None)
        type = self.obj.get("type", None)
        enum = self.obj.get("enum", None)
        pattern = self.obj.get("pattern", None)
        oneOf = self.obj.get("oneOf", [])
        items = self.obj.get("items", None)
        prefixItems = self.obj.get("prefixItems", None)
        properties = self.obj.get("properties", None)
        required = self.obj.get("required", [])
         
        rule = "{rule}"
        
        # For now we treat arrays with prefixItems as min==max==len(prefixItems)
        if type=="array" and prefixItems:
            subRules = []
            for n,it in enumerate(prefixItems):
                if "$ref" in it:
                    subRules.append( self.getReferenceFromConverter(it['$ref']) )
                else:
                    subRules.append( self.referenceRule(self.name+chr(n+97),it) )
            rule = rule.format(rule=f"({' '.join(subRules)})")

        # Array returns either reference ~ n..m or (literal|literal) ~ n..m
        elif type=="array" and items:
            minItems, maxItems = (self.obj.get("minItems", 1), self.obj.get("maxItems", None))
            # Two cases: either a ref, or an enum
            item = ""
            if "enum" in items: # enum of literals
                enums = [f'"{e}"' for e in items["enum"]]
                item = f'({"|".join(enums)})'
            elif "$ref" in items:
                item = self.getReferenceFromConverter(items['$ref'])
            if maxItems is None:
                if minItems == 0:
                    rule = f"{item}*"
                elif minItems == 1:
                    rule = f"{item}+"
                else:
                    rule = f"{item} ~ {str(minItems)} {item}*"
                    if self.references:
                        self.references.append( self.references[-1] )
            elif minItems == maxItems:
                rule = f"{item} ~ {str(minItems)}"
            else:
                rule = f"{item} ~ {str(minItems)}..{str(maxItems)}"
                
        # Simple forwarding reference
        elif ref:
            rule = rule.format(rule=self.getReferenceFromConverter(ref))
    
        # Two scenarios for terminals: simple string or number
        elif type=="string" and not enum and not oneOf:
            if not pattern: pattern = DEFAULT_STRING_PATTERN
            rule = rule.format(rule=self.converter.terminal(self.name,pattern))
        elif type=="number":
            rule = rule.format(rule=self.converter.terminal(self.name,"^\d+(\.\d+)?"))
        
        # Properties created needed named rules
        elif properties:
            tmp_rule = ""
            added_in_one_of = set()
            
            for p in properties:
                if p=="comment": continue
                if p in added_in_one_of: continue
                # Special cases first
                if self.name=="unit" and p=="constraints":
                    tmp_rule += f" _NL [_INDENT { self.referenceRule(p,properties[p],propertyOf=self) } _DEDENT]"
                elif self.name=="unit" and p=="partOf":
                    at = '"@"'
                    tmp_rule += f"({at}{ self.referenceRule(p,properties[p],propertyOf=self) })?"
                elif self.name=="resultSet" and p=="label":
                    fat_arrow = '"=>"'
                    tmp_rule += f"{ self.referenceRule(p,properties[p],propertyOf=self) } {fat_arrow}"
                elif (self.name,p) in {("resultSetPlain",'entities'), ("resultSetCollAnalysis","space")}:
                    tmp_rule += f"({ self.referenceRule(p,properties[p],propertyOf=self) } _NL?)+"
                # End special cases
                else:
                    # If the property is referenced in oneOf, disjunction
                    if p in {r for o in oneOf if isinstance(o,dict) for r in o.get('required')}:
                        oneOfArray = []
                        for o in oneOf:
                            if 'required' not in o: continue
                            if len(o['required']) > 1: # subsequence of properties
                                subArray = []
                                for pname in o['required']:
                                    subArray.append( self.referenceRule(pname,properties[pname],propertyOf=self) )
                                    added_in_one_of.add(pname)
                                oneOfArray.append("({})".format(' '.join(subArray)))
                            else:
                                pname = o['required'][0]
                                oneOfArray.append( self.referenceRule(pname,properties[pname],propertyOf=self) )
                                added_in_one_of.add(pname)
                        tmp_rule += "( {})".format('|'.join(oneOfArray))
                    else:
                        if p in required:
                            tmp_rule += f" { self.referenceRule(p,properties[p],propertyOf=self) }"
                        else:
                            tmp_rule += f"( { self.referenceRule(p,properties[p],propertyOf=self) })?"
            
            rule = rule.format(rule=tmp_rule)
            
            # if self.name == "unit":
            #     # This is hard-coded but ideally cobquec should list the properties in the proper order
            #     tmp_rule = ""
            #     for p in sort_props:
            #         if p not in properties: continue
            #         if p in required:
            #             tmp_rule += f" { self.referenceRule(p,properties[p],propertyOf=self) }"
            #         elif p=="constraints":
            #             tmp_rule += f" _NL [_INDENT { self.referenceRule(p,properties[p],propertyOf=self) } _DEDENT]"
            #         else:
            #             at = '"@"'
            #             tmp_rule += f"({at if p=='partOf' else ' '}{ self.referenceRule(p,properties[p],propertyOf=self) })?"
            #     rule = rule.format(rule=tmp_rule)
            # elif self.name == "sequence":
            #     # This is hard-coded but ideally cobquec should list the properties in the proper order
            #     tmp_rule = ""
            #     sort_props = ('label','repetition','members')
            #     for p in sort_props:
            #         if p not in properties: continue
            #         if p in required:
            #             tmp_rule += f" { self.referenceRule(p,properties[p],propertyOf=self) }"
            #         else:
            #             tmp_rule += f" ({ self.referenceRule(p,properties[p],propertyOf=self) })?"
            #     rule = rule.format(rule=tmp_rule)
                    
            # else:
            #     tmp_rule = ""
            #     for p in properties:
            #         if p not in properties: continue
            #         if p == "comment": continue
            #         tmp_rule += f" { self.referenceRule(p,properties[p],propertyOf=self) }{'?' if p not in required else ''}"
            #     rule = rule.format(rule=tmp_rule)
         
        # oneOf without properties creates forwarding rules, their names don't matter
        elif oneOf:
            rule = rule.format(rule=f"({'|'.join([self.referenceRule('anonymous_forwarder',o) for o in oneOf])})")
            
            # rule = rule.format(rule="({rule})")
            # oneOfArray = []
            
            # # oneOf is an array of properties, terminals or references (no literals)
            # for _, one in enumerate(oneOf):
            #     if "required" in one:
            #         subArray = []
            #         for o in one['required']:
            #             assert properties and o in properties, f"'{self.name}' requires '{o}' but no property found with that name"
            #             subArray.append( self.referenceRule(o,properties[o],propertyOf=self) )
            #         oneOfArray.append(f"({' '.join(subArray)})")
            #     elif '$ref' in one:
            #         oneOfArray.append( self.getReferenceFromConverter(one['$ref']) )
            #     else: # terminal
            #         pattern = one.get("pattern", DEFAULT_STRING_PATTERN)
            #         if one.get("type") == "number":
            #             pattern = "\d+(\.\d+)?"
            #         oneOfArray.append( self.converter.terminal(self.name+"_ENUM",pattern) )
                    
            # rule = rule.format(rule=f"{'|'.join(oneOfArray)}")
    
        # Enums are either lists of literals, or lists of terminals/refs (ie. no property in enum)
        elif enum:
            enumArray = []
            if all([isinstance(e,str) for e in enum]):
                enumArray = [f'"{e}"' for e in enum]
            else:
                for _,e in enumerate(enum):
                    if "$ref" in e: # reference
                        enumArray.append( self.getReferenceFromConverter(e['$ref']) )
                    else: # terminal
                        pattern = e.get("pattern", DEFAULT_STRING_PATTERN)
                        if e.get("type") == "number":
                            pattern = "\d+(\.\d+)?"
                        enumArray.append( self.converter.terminal(self.name+"_ENUM",pattern) )
                        
            rule = rule.format(rule=f"({'|'.join(enumArray)})")
                
        self.rule = rule
        
    
    def getReferenceFromConverter(self,ref):
        refRule = self.converter.reference(ref.split('/')[-1])
        self.references.append( (refRule,None) )
        return '{}'
    
    
    def referenceRule(self,name,properties,propertyOf=None):
        rule = None
        if f"#/$defs/{name}" == properties.get("$ref", None):
            rule =  self.converter.reference(properties["$ref"].split('/')[-1])
        else:
            rule = self.converter.addRule(name,properties)
        self.references.append( (rule,propertyOf) )
        return '{}'
    
    
    def resolvedName(self):
        comps = [ re.sub(r"[A-Z]", lambda x: "_"+x[0].lower(), self.name) , self.uuid ]
        # if self.propertyOf:
        #     comps.append( re.sub(r"[A-Z]", lambda x: "_"+x[0].lower(), self.propertyOf.name) )
        return "__".join(comps)
        
    
    def toString(self,stack=set()):
        if self in stack:
            return self.resolvedName()
        newStack = {self,*stack}
        resolvedReferences = []
        for r,propertyOf in self.references:
            if r in newStack or propertyOf is self:
                resolvedReferences.append(r.resolvedName())
                self.converter.needRule(r)
            else:
                resolvedReferences.append(r.toString(newStack))
        rule = self.rule.format(*resolvedReferences)
        # rule = self.rule.format(*[r.resolvedName() for r in self.references])
        if self.name in KEYWORDS and ( self.isDefinition is False or KEYWORDS[self.name].get('from')=='$defs' ):
            rule = KEYWORDS[self.name]['substitute'].format(rule)
        return rule



class Converter():
    
    def __init__(self, configfile):
        
        f = open(configfile)
        config = json.load(f)
        
        req = config.get("required",[])
        properties = config.get("properties", {})
        
        self.defs = config.get("$defs", {})
        self.definitions = dict()
        self.rules = list()
        self.terminals = dict()
        self.neededRules = set()
        
        start = "?start: _NL* [main_property+]\n\nmain_property: ({})"
        
        required_main_properties = []
        for r in req:
            if r == "comment": continue
            assert (r in properties), f"Required '{r}' absent from root properties"
            assert (properties.get(r,{}).get("type")=="array"), f"Root property '{r}' must be an array"
            properties[r]['maxItems'] = 1 # Override this because we're handling repetition in main_property
            rule = self.addRule(r, properties[r])
            self.neededRules.add( rule )
            required_main_properties.append( rule.resolvedName() )
        start = start.format('|'.join(required_main_properties))
            
        strrules = ""
        
        writtenRules = set()
        remainingRules = self.neededRules - writtenRules
        while remainingRules:
            rule = next(r for r in remainingRules)
            strrules += f"\n{rule.resolvedName()}: {rule.toString()}"
            writtenRules.add(rule)
            remainingRules = self.neededRules - writtenRules

#         strrules = "\n".join([
#             # f"{r.resolvedName()} : { KEYWORDS[r.name].format(r.toString()) if r.name in KEYWORDS and r.isDefinition else r.toString() }" for r in self.rules
#             # f"{r.resolvedName()} : {r.toString()}" for r in self.rules
#             f"{r.resolvedName()} : {r.toString()}" for r in self.neededRules
#         ])
        strterminals = "\n".join([f"{t} : {self.terminals[t]}" for t in self.terminals])
        self.output = f"""
{start}
{strrules}

{strterminals}

{EOF}
        """


    def needRule(self, rule):
        self.neededRules.add(rule)
        

    def addRule(self, name, obj, build=True, isDefinition=False):
        
        rule = Rule(self, name, obj, isDefinition=isDefinition)
        self.rules.append( rule )
        if build:
            rule.build()
        return rule
        
    
    # Return a rule that points to a reference
    def reference(self, reference):
        
        if reference in self.definitions:
            return self.definitions[reference]
        elif reference in self.defs:
            self.definitions[reference] = self.addRule(reference, self.defs[reference], build=False, isDefinition=True)
            self.definitions[reference].build()
            return self.definitions[reference]
        else:
            assert False, f"Reference {reference} could not be found anywhere"
        
        
    def terminal(self,name,pattern):
        name = name.upper() + "_T"
        pattern = "/" + pattern.replace("/","\/") + "/"
        
        existing = next((t_name for t_name, t_pattern in self.terminals.items() if pattern == t_pattern), None)
        if existing:
            return existing
        
        if name in self.terminals:
            n = 2
            while name+chr(n+64) in self.terminals:
                n += 1
            name = name+chr(n+64)
        
        self.terminals[name] = pattern
        return name