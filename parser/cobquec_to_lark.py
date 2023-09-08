
class Converter():
    
    def __init__(self, config):
        self.terminals = dict()
        self.rules = dict()
        
        req = config.get("required",[])        
        self.defs = config.get("$defs", {})
        self.lark = [f"?start: _NL* {' '.join(req)}"]
        props = config.get("properties", {})
        for r in req:
            reqProps = props.get(r, None)
            if reqProps is None: continue
            self.parseRef(r, reqProps)
    
    
    def cqc_to_lark(self, config):
        req = config.get("required",[])
        global defs
        defs = config.get("$defs", {})
        lark += [f"?start: _NL* {' '.join(req)}"]
        props = config.get("properties", {})
        for r in req:
            reqProps = props.get(r, None)
            if reqProps is None: continue
            self.parseRef(r, reqProps)
        return lark


    def parseRef(self, name, obj):
        type = obj.get("type", None)
        enum = obj.get("enum", None)
        pattern = obj.get("pattern", None)
        oneOf = obj.get("oneOf", None)
        items = obj.get("items", None)
        properties = obj.get("properties", None)
        required = obj.get("required", [])
        
        if type=="string":
            if not pattern: pattern = ".*"
            return self.terminal(name,pattern)
        
        if type=="number":
            return self.terminal(name,"^\d+(\.\d+)?")
        
        if type=="array" and items:
            minItems, maxItems = (obj.get("minItems", 1), obj.get("maxItems", None))
            # Two cases: either a ref, or an enum
            item = ""
            if "enum" in items:
                enums = [f'"{e}"' for e in items["enum"]]
                item = f'({"|".join(enums)})'
            elif "$ref" in items:
                item = items["$ref"].split('/')[-1]
            if minItems > 1:
                rule = f"{item} ~ {str(minItems)}"
                if maxItems is None:
                    rule += f" {item}*"
                elif maxItems > maxItems:
                    rule += f"..{str(maxItems)}"
                return rule
        
        rule = ""
        
        if properties:
            if name == "unit":
                # This is hard-coded but ideally cobquec should list the properties in the proper order
                sort_props = ('layer','partOf','label','constraints')
                for p in sort_props:
                    if p not in properties: continue
                    if p in required:
                        rule += f" {self.parseRef(p,properties[p])}"
                    else:
                        rule += f"{'"@"' if p=='partOf' else ' '}{self.parseRef(p,properties[p])}?"
                    
            else:
                if name in ("sequence", "group", "set"):
                    rule = f'"{name}"'
                for p in sort_props:
                    if p not in properties: continue
                    if p == "comment": continue
                    rule += f" {self.parseRef(p,properties[p])}{'?' if p not in required else ''}"

                    
        if enum:
            enumNamePrefix = f"{name}Enum"
            rule = f"({'|'.join([self.parseRef(enumNamePrefix+str(n),e) for n,e in enumerate(enum)])})"
        elif oneOf:
            pass
        
        self.rules[name] = rule
        
    def terminal(self,name,pattern):
        name = name.upper()
        if name in self.terminals:
            if self.terminals[name] == pattern:
                return name
            else:
                i = 0
                while name+str(i) in self.terminals:
                    if self.terminals[name+str(i)] == pattern: return name+str(i)
                    else: i += 1
                self.terminals[name+str(i)] = pattern
                return name+str(i)
        else:
            self.terminals[name] = pattern
            return name
        # if (type=="string" and pattern and not ref):
        #     self.getVariable(name,obj)
        
        # if type and enum:
        #     return f"/({'|'.join([e for e in enum])})/" # Need to escape any regex char in e first
        
        # if oneOf is not None:
        #     refs = [o['$ref'] for o in oneOf if o.get('$ref',None)]
        #     lark += [f"{name}   : {before}{'|'.join(refs)}{after}"]
        #     for ref in refs:
        #         refProps = defs.get(ref,None)
        #         if refProps is not None: self.parseRef(ref, refProps)
        #         return
        #     return
        # properties = obj.get("properties",None)
        # if properties:
        #     self.handleProperties(name,properties)
        #     return    
        # before, after = ("","")
        # if (name=="statement"):
        #     before,after = ("_NL [_INDENT ","_DEDENT]")
        # its = obj.get("items",None)
        # if its is not None:
        #     ref = its.get("$ref", None)
        #     if ref is not None:
        #         lark += [f"{name}   : {before}{ref}{after}"]
        #         refProps = defs.get(ref,None)
        #         if refProps is not None: self.parseRef(ref, refProps)
        #         return


    def getVariable(self, name,props):
        self.terminal[name.upper()] = props
        
        
    def enum(self, enums):
        r = "({enums})"
        ar = []
        for e in enums:
            if self.isRef(e):
                ar.append(self.getRef(e))
            else: # text?
                # create a new VARIABLE
                ar.append("VARIABLE")
        return r.format(enums='|'.join(r))


    def isRef(self, o):
        return isinstance(o,dict) and o.get("$ref",None)
        
        
    def getProp(self, name,element):
        props = element.get("properties", {name: None})
        return props[name]
        
        
    def getDef(self, name):
        return defs.get(name, None)


    def getRef(self, name,element):
        if isinstance(name,dict) and name.get("$ref"):
            return self.getDef(name['$ref'].split('/')[-1])
        elif isinstance(name,str):
            return self.getProp(name,element)


    def handleProperties(self, name,props):
        pass