/* eslint-disable */
//
//  Lark.js stand-alone parser
//===============================

"use strict";

/**
	This is the main entrypoint into the generated Lark parser.

  @param {object} options An object with the following optional properties:

	  - transformer: an object of {rule: callback}, or an instance of Transformer
	  - propagate_positions (bool): should all tree nodes calculate line/column info?
	  - tree_class (Tree): a class that extends Tree, to be used for creating the parse tree.
	  - debug (bool): in case of error, should the parser output debug info to the console?

  @returns {Lark} an object which provides the following methods:

    - parse
    - parse_interactive
    - lex

*/
function get_parser(options = {}) {
  if (
    options.transformer &&
    options.transformer.constructor.name === "object"
  ) {
    options.transformer = Transformer.fromObj(options.transformer);
  }

  return Lark._load_from_dict({ data: DATA, memo: MEMO, ...options });
}

const NO_VALUE = {};
class _Decoratable {}
const Discard = {};

//
//   Implementation of Scanner + module emulation for Python's stdlib re
// -------------------------------------------------------------------------

const re = {
  escape(string) {
    // See: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions#escaping
    return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); // $& means the whole matched string
  },
  compile(regex, flags) {
    // May throw re.error
    return new RegExp(regex, flags);
  },
  error: SyntaxError,
};

function _get_match(re_, regexp, s, flags) {
  const m = re_.compile(regexp, flags).exec(s);
  if (m != null) return m[0];
}

class Scanner {
  constructor(terminals, g_regex_flags, re_, use_bytes, match_whole = false) {
    this.terminals = terminals;
    this.g_regex_flags = g_regex_flags;
    this.re_ = re_;
    this.use_bytes = use_bytes;
    this.match_whole = match_whole;
    this.allowed_types = new Set(this.terminals.map((t) => t.name));

    this._regexps = this._build_mres(terminals);
  }

  _build_mres(terminals) {
    // TODO deal with priorities!
    let postfix = this.match_whole ? "$" : "";
    let patterns_by_flags = segment_by_key(terminals, (t) =>
      t.pattern.flags.join("")
    );

    let regexps = [];
    for (let [flags, patterns] of patterns_by_flags) {
      const pattern = patterns
        .map((t) => `(?<${t.name}>${t.pattern.to_regexp() + postfix})`)
        .join("|");
      regexps.push(new RegExp(pattern, this.g_regex_flags + flags + "y"));
    }

    return regexps;
  }

  match(text, pos) {
    for (const re of this._regexps) {
      re.lastIndex = pos;
      let m = re.exec(text);
      if (m) {
        // Find group. Ugly hack, but javascript is forcing my hand.
        let group = null;
        for (let [k, v] of Object.entries(m.groups)) {
          if (v) {
            group = k;
            break;
          }
        }
        return [m[0], group];
      }
    }
  }
}
//
//  Start of library code
// --------------------------

const util = typeof require !== "undefined" && require("util");

class ABC {}

const NotImplemented = {};

function dict_items(d) {
  return Object.entries(d);
}
function dict_keys(d) {
  return Object.keys(d);
}
function dict_values(d) {
  return Object.values(d);
}

function dict_pop(d, key) {
  if (key === undefined) {
    key = Object.keys(d)[0];
  }
  let value = d[key];
  delete d[key];
  return value;
}

function dict_get(d, key, otherwise = null) {
  return d[key] || otherwise;
}

function dict_update(self, other) {
  if (self.constructor.name === "Map") {
    for (const [k, v] of dict_items(other)) {
      self.set(k, v);
    }
  } else {
    for (const [k, v] of dict_items(other)) {
      self[k] = v;
    }
  }
}

function make_constructor(cls) {
  return function () {
    return new cls(...arguments);
  };
}

function range(start, end) {
  if (end === undefined) {
    end = start;
    start = 0;
  }
  const res = [];
  for (let i = start; i < end; i++) res.push(i);
  return res;
}

function format(s) {
  let counter = 0;
  let args = [...arguments].slice(1);

  return s.replace(/%([sr])/g, function () {
    const t = arguments[1];
    const item = args[counter++];
    if (t === "r") {
      return util
        ? util.inspect(item, false, null, true)
        : JSON.stringify(item, null, 0);
    } else {
      return item;
    }
  });
}

function union(setA, setB) {
  let _union = new Set(setA);
  for (const elem of setB) {
    _union.add(elem);
  }
  return _union;
}

function intersection(setA, setB) {
  let _intersection = new Set();
  for (const elem of setB) {
    if (setA.has(elem)) {
      _intersection.add(elem);
    }
  }
  return _intersection;
}

function set_subtract(a, b) {
  return [...a].filter((e) => !b.has(e));
}

function dict(d) {
  return { ...d };
}

function bool(x) {
  return !!x;
}

function new_object(cls) {
  return Object.create(cls.prototype);
}

function copy(obj) {
  if (typeof obj == "object") {
    let empty_clone = Object.create(Object.getPrototypeOf(obj));
    return Object.assign(empty_clone, obj);
  }
  return obj;
}

function map_pop(key) {
  let value = this.get(key);
  this.delete(key);
  return value;
}

function hash(x) {
  return x;
}
function tuple(x) {
  return x;
}
function frozenset(x) {
  return new Set(x);
}

function is_dict(x) {
  return x && x.constructor.name === "Object";
}
function is_array(x) {
  return x && x.constructor.name === "Array";
}
function callable(x) {
  return typeof x === "function";
}

function* enumerate(it, start = 0) {
  // Taken from: https://stackoverflow.com/questions/34336960/what-is-the-es6-equivalent-of-python-enumerate-for-a-sequence
  let i = start;
  for (const x of it) {
    yield [i++, x];
  }
}

function any(lst) {
  for (const item of lst) {
    if (item) {
      return true;
    }
  }
  return false;
}

function all(lst) {
  for (const item of lst) {
    if (!item) {
      return false;
    }
  }
  return true;
}

function filter(pred, lst) {
  return lst.filter(pred || bool);
}

function partial(f) {
  let args = [...arguments].slice(1);
  return function () {
    return f(...args, ...arguments);
  };
}

class EOFError extends Error {}

function last_item(a) {
  return a[a.length - 1];
}

function callable_class(cls) {
  return function () {
    let inst = new cls(...arguments);
    return inst.__call__.bind(inst);
  };
}

function list_repeat(list, count) {
  return Array.from({ length: count }, () => list).flat();
}

function isupper(a) {
  return /^[A-Z_$]*$/.test(a);
}

function rsplit(s, delimiter, limit) {
  const arr = s.split(delimiter);
  return limit ? arr.splice(-limit - 1) : arr;
}

function str_count(s, substr) {
  let re = new RegExp(substr, "g");
  return (s.match(re) || []).length;
}

function list_count(list, elem) {
  let count = 0;
  for (const e of list) {
    if (e === elem) {
      count++;
    }
  }
  return count;
}

function isSubset(subset, set) {
  for (let elem of subset) {
    if (!set.has(elem)) {
      return false;
    }
  }
  return true;
}

function* segment_by_key(a, key) {
  let buffer = [];
  let last_k = null;
  for (const item of a) {
    const k = key(item);
    if (last_k && k != last_k) {
      yield [last_k, buffer];
      buffer = [];
    }
    buffer.push(item);
    last_k = k;
  }
  yield [last_k, buffer];
}

// --------------------------
//  End of library code
//

//
// Exceptions
//

class LarkError extends Error {
  // pass
}

class ConfigurationError extends LarkError {
  // pass
}

function assert_config(value, options, msg = "Got %r, expected one of %s") {
  if (!(options.includes(value))) {
    throw new ConfigurationError(format(msg, value, options));
  }
}

class GrammarError extends LarkError {
  // pass
}

class ParseError extends LarkError {
  // pass
}

class LexError extends LarkError {
  // pass
}

/**
  UnexpectedInput Error.

    Used as a base class for the following exceptions:

    - ``UnexpectedCharacters``: The lexer encountered an unexpected string
    - ``UnexpectedToken``: The parser received an unexpected token
    - ``UnexpectedEOF``: The parser expected a token, but the input ended

    After catching one of these exceptions, you may call the following helper methods to create a nicer error message.

*/

class UnexpectedInput extends LarkError {
  pos_in_stream = null;
  _terminals_by_name = null;
  /**
    Returns a pretty string pinpointing the error in the text,
        with span amount of context characters around it.

        Note:
            The parser doesn't hold a copy of the text it has to parse,
            so you have to provide it again

  */
  get_context(text, span = 40) {
    let after, before;
    let pos = this.pos_in_stream;
    let start = max(pos - span, 0);
    let end = pos + span;
    if (!(text instanceof bytes)) {
      before = last_item(rsplit(text.slice(start, pos), "\n", 1));
      after = text.slice(pos, end).split("\n", 1)[0];
      return before + after + "\n" + " " * before.expandtabs().length + "^\n";
    } else {
      before = last_item(rsplit(text.slice(start, pos), "\n", 1));
      after = text.slice(pos, end).split("\n", 1)[0];
      return (
        before +
        after +
        "\n" +
        " " * before.expandtabs().length +
        "^\n"
      ).decode("ascii", "backslashreplace");
    }
  }

  /**
    Allows you to detect what's wrong in the input text by matching
        against example errors.

        Given a parser instance and a dictionary mapping some label with
        some malformed syntax examples, it'll return the label for the
        example that bests matches the current error. The function will
        iterate the dictionary until it finds a matching error, and
        return the corresponding value.

        For an example usage, see `examples/error_reporting_lalr.py`

        Parameters:
            parse_fn: parse function (usually ``lark_instance.parse``)
            examples: dictionary of ``{'example_string': value}``.
            use_accepts: Recommended to keep this as ``use_accepts=True``.

  */
  match_examples(
    parse_fn,
    examples,
    token_type_match_fallback = false,
  ) {
    if (is_dict(examples)) {
      examples = dict_items(examples);
    }

    let candidate = [null, false];
    for (const [i, [label, example]] of enumerate(examples)) {
      for (const [j, malformed] of enumerate(example)) {
        try {
          parse_fn(malformed);
        } catch (ut) {
          if (ut instanceof UnexpectedInput) {
            if (ut.state.eq(this.state)) {
                if (ut.token === this.token) {
                  return label;
                }

                if (token_type_match_fallback) {
                  // Fallback to token types match
                  if (
                    ut.token.type === this.token.type &&
                    !last_item(candidate)
                  ) {
                    candidate = [label, true];
                  }
                }
              if (candidate[0] === null) {
                candidate = [label, false];
              }
            }
          } else {
            throw ut;
          }
        }
      }
    }

    return candidate[0];
  }

  _format_expected(expected) {
    let d;
    if (this._terminals_by_name) {
      d = this._terminals_by_name;
      expected = expected.map((t_name) =>
        t_name in d ? d[t_name].user_repr() : t_name
      );
    }

    return format("Expected one of: \n\t* %s\n", expected.join("\n\t* "));
  }
}

/**
  An exception that is raised by the parser, when the input ends while it still expects a token.

*/

class UnexpectedEOF extends UnexpectedInput {
  constructor(expected, state = null, terminals_by_name = null) {
    super();
    this.expected = expected;
    this.state = state;
    this.token = new Token("<EOF>", "");
    // , line=-1, column=-1, pos_in_stream=-1)
    this.pos_in_stream = -1;
    this.line = -1;
    this.column = -1;
    this._terminals_by_name = terminals_by_name;
  }
}

/**
  An exception that is raised by the lexer, when it cannot match the next
    string of characters to any of its terminals.

*/

class UnexpectedCharacters extends UnexpectedInput {
  constructor({
    seq,
    lex_pos,
    line,
    column,
    allowed = null,
    considered_tokens = null,
    state = null,
    token_history = null,
    terminals_by_name = null,
    considered_rules = null,
  } = {}) {
    super();
    // TODO considered_tokens and allowed can be figured out using state
    this.line = line;
    this.column = column;
    this.pos_in_stream = lex_pos;
    this.state = state;
    this._terminals_by_name = terminals_by_name;
    this.allowed = allowed;
    this.considered_tokens = considered_tokens;
    this.considered_rules = considered_rules;
    this.token_history = token_history;
      this.char = seq[lex_pos];
    // this._context = this.get_context(seq);
  }
}

/**
  An exception that is raised by the parser, when the token it received
    doesn't match any valid step forward.

    Parameters:
        token: The mismatched token
        expected: The set of expected tokens
        considered_rules: Which rules were considered, to deduce the expected tokens
        state: A value representing the parser state. Do not rely on its value or type.
        interactive_parser: An instance of ``InteractiveParser``, that is initialized to the point of failture,
                            and can be used for debugging and error handling.

    Note: These parameters are available as attributes of the instance.

*/

class UnexpectedToken extends UnexpectedInput {
  constructor({
    token,
    expected,
    considered_rules = null,
    state = null,
    interactive_parser = null,
    terminals_by_name = null,
    token_history = null,
  } = {}) {
    super();
    // TODO considered_rules and expected can be figured out using state
    this.line = (token && token["line"]) || "?";
    this.column = (token && token["column"]) || "?";
    this.pos_in_stream = (token && token["start_pos"]) || null;
    this.state = state;
    this.token = token;
    this.expected = expected;
    // XXX deprecate? `accepts` is better
    this._accepts = NO_VALUE;
    this.considered_rules = considered_rules;
    this.interactive_parser = interactive_parser;
    this._terminals_by_name = terminals_by_name;
    this.token_history = token_history;
  }

  get accepts() {
    if (this._accepts === NO_VALUE) {
      this._accepts =
        this.interactive_parser && this.interactive_parser.accepts();
    }

    return this._accepts;
  }
}

/**
  VisitError is raised when visitors are interrupted by an exception

    It provides the following attributes for inspection:

    Parameters:
        rule: the name of the visit rule that failed
        obj: the tree-node or token that was being processed
        orig_exc: the exception that cause it to fail

    Note: These parameters are available as attributes

*/

class VisitError extends LarkError {
  constructor(rule, obj, orig_exc) {
    let message = format(
      'Error trying to process rule "%s":\n\n%s',
      rule,
      orig_exc
    );
    super(message);
    this.rule = rule;
    this.obj = obj;
    this.orig_exc = orig_exc;
  }
}

//
// Utils
//

function classify(seq, key = null, value = null) {
  let k, v;
  let d = new Map();
  for (const item of seq) {
    k = key !== null ? key(item) : item;
    v = value !== null ? value(item) : item;
    if (d.has(k)) {
      d.get(k).push(v);
    } else {
      d.set(k, [v]);
    }
  }

  return d;
}

function _deserialize(data, namespace, memo) {
  let class_;
  if (is_dict(data)) {
    if ("__type__" in data) {
      // Object
      class_ = namespace[data["__type__"]];
      return class_.deserialize(data, memo);
    } else if ("@" in data) {
      return memo[data["@"]];
    }

    return Object.fromEntries(
      dict_items(data).map(([key, value]) => [
        key,
        _deserialize(value, namespace, memo),
      ])
    );
  } else if (is_array(data)) {
    return data.map((value) => _deserialize(value, namespace, memo));
  }

  return data;
}

/**
  Safe-ish serialization interface that doesn't rely on Pickle

    Attributes:
        __serialize_fields__ (List[str]): Fields (aka attributes) to serialize.
        __serialize_namespace__ (list): List of classes that deserialization is allowed to instantiate.
                                        Should include all field types that aren't builtin types.

*/

class Serialize {
  static deserialize(data, memo) {
    const cls = this;
    let fields = cls && cls["__serialize_fields__"];
    if ("@" in data) {
      return memo[data["@"]];
    }

    let inst = new_object(cls);
    for (const f of fields) {
      if (data && f in data) {
        inst[f] = _deserialize(data[f], NAMESPACE, memo);
      } else {
        throw new KeyError("Cannot find key for class", cls, e);
      }
    }

    if ("_deserialize" in inst) {
      inst._deserialize();
    }

    return inst;
  }
}

/**
  A version of serialize that memoizes objects to reduce space
*/

class SerializeMemoizer extends Serialize {
  static get __serialize_fields__() {
    return ["memoized"];
  }
  constructor(types_to_memoize) {
    super();
    this.types_to_memoize = tuple(types_to_memoize);
    this.memoized = new Enumerator();
  }

  in_types(value) {
    return value instanceof this.types_to_memoize;
  }

  serialize() {
    return _serialize(this.memoized.reversed(), null);
  }

  static deserialize(data, namespace, memo) {
    const cls = this;
    return _deserialize(data, namespace, memo);
  }
}

//
// Tree
//

class Meta {
  constructor() {
    this.empty = true;
  }
}

/**
  The main tree class.

    Creates a new tree, and stores "data" and "children" in attributes of the same name.
    Trees can be hashed and compared.

    Parameters:
        data: The name of the rule or alias
        children: List of matched sub-rules and terminals
        meta: Line & Column numbers (if ``propagate_positions`` is enabled).
            meta attributes: line, column, start_pos, end_line, end_column, end_pos

*/

class Tree {
  constructor(data, children, meta = null) {
    this.data = data;
    this.children = children;
    this._meta = meta;
  }

  get meta() {
    if (this._meta === null) {
      this._meta = new Meta();
    }

    return this._meta;
  }

  repr() {
    return format("Tree(%r, %r)", this.data, this.children);
  }

  _pretty_label() {
    return this.data;
  }

  _pretty(level, indent_str) {
    if (this.children.length === 1 && !(this.children[0] instanceof Tree)) {
      return [
        list_repeat(indent_str, level).join(''),
        this._pretty_label(),
        "\t",
        format("%s", this.children[0].value),
        "\n",
      ];
    }

    let l = [list_repeat(indent_str, level).join(''), this._pretty_label(), "\n"];
    for (const n of this.children) {
      if (n instanceof Tree) {
        l.push(...n._pretty(level + 1, indent_str));
      } else {
        l.push(...[list_repeat(indent_str, level+1).join(''), format("%s", n.value), "\n"]);
      }
    }

    return l;
  }

  /**
    Returns an indented string representation of the tree.

        Great for debugging.

  */
  pretty(indent_str = "  ") {
    return this._pretty(0, indent_str).join("");
  }

  eq(other) {
    if (
      other &&
      this &&
      other &&
      this &&
      other.children &&
      this.children &&
      other.data &&
      this.data
    ) {
      return this.data === other.data && this.children === other.children;
    } else {
      return false;
    }
  }

  /**
    Depth-first iteration.

        Iterates over all the subtrees, never returning to the same node twice (Lark's parse-tree is actually a DAG).

  */
  iter_subtrees() {
    let queue = [this];
    let subtrees = new Map();
    for (const subtree of queue) {
      subtrees.set(subtree, subtree);
      queue.push(
        ...[...subtree.children]
          .reverse()
          .filter((c) => c instanceof Tree && !subtrees.has(c))
          .map((c) => c)
      );
    }

    queue = undefined;
    return [...subtrees.values()].reverse();
  }

  /**
    Returns all nodes of the tree that evaluate pred(node) as true.
  */
  find_pred(pred) {
    return filter(pred, this.iter_subtrees());
  }

  /**
    Returns all nodes of the tree whose data equals the given data.
  */
  find_data(data) {
    return this.find_pred((t) => t.data === data);
  }


  /**
    Return all values in the tree that evaluate pred(value) as true.

        This can be used to find all the tokens in the tree.

        Example:
            >>> all_tokens = tree.scan_values(lambda v: isinstance(v, Token))

  */
  *scan_values(pred) {
    for (const c of this.children) {
      if (c instanceof Tree) {
        for (const t of c.scan_values(pred)) {
          yield t;
        }
      } else {
        if (pred(c)) {
          yield c;
        }
      }
    }
  }

  /**
    Breadth-first iteration.

        Iterates over all the subtrees, return nodes in order like pretty() does.

  */
  *iter_subtrees_topdown() {
    let node;
    let stack = [this];
    while (stack.length) {
      node = stack.pop();
      if (!(node instanceof Tree)) {
        continue;
      }

      yield node;
      for (const child of [...node.children].reverse()) {
        stack.push(child);
      }
    }
  }

  copy() {
    return type(this)(this.data, this.children);
  }

  set(data, children) {
    this.data = data;
    this.children = children;
  }
}

//
// Visitors
//

/**
  Transformers work bottom-up (or depth-first), starting with visiting the leaves and working
    their way up until ending at the root of the tree.

    For each node visited, the transformer will call the appropriate method (callbacks), according to the
    node's ``data``, and use the returned value to replace the node, thereby creating a new tree structure.

    Transformers can be used to implement map & reduce patterns. Because nodes are reduced from leaf to root,
    at any point the callbacks may assume the children have already been transformed (if applicable).

    If the transformer cannot find a method with the right name, it will instead call ``__default__``, which by
    default creates a copy of the node.

    To discard a node, return Discard (``lark.visitors.Discard``).

    ``Transformer`` can do anything ``Visitor`` can do, but because it reconstructs the tree,
    it is slightly less efficient.

    A transformer without methods essentially performs a non-memoized partial deepcopy.

    All these classes implement the transformer interface:

    - ``Transformer`` - Recursively transforms the tree. This is the one you probably want.
    - ``Transformer_InPlace`` - Non-recursive. Changes the tree in-place instead of returning new instances
    - ``Transformer_InPlaceRecursive`` - Recursive. Changes the tree in-place instead of returning new instances

    Parameters:
        visit_tokens (bool, optional): Should the transformer visit tokens in addition to rules.
                                       Setting this to ``False`` is slightly faster. Defaults to ``True``.
                                       (For processing ignored tokens, use the ``lexer_callbacks`` options)


*/

class Transformer extends _Decoratable {
  static get __visit_tokens__() {
    return true;
  }
  // For backwards compatibility

  constructor(visit_tokens = true) {
    super();
    this.__visit_tokens__ = visit_tokens;
  }

  static fromObj(obj, ...args) {
    class _T extends this {}
    for (let [k, v] of Object.entries(obj)) {
      _T.prototype[k] = v
    }
    return new _T(...args)
  }

  _call_userfunc(tree, new_children = null) {
    let f, wrapper;
    // Assumes tree is already transformed
    let children = new_children !== null ? new_children : tree.children;
    if (tree && tree.data && this && this[tree.data]) {
      f = this && this[tree.data];
      try {
        wrapper = (f && f["visit_wrapper"]) || null;
        if (wrapper !== null) {
          return f.visit_wrapper(f, tree.data, children, tree.meta);
        } else {
          return f(children);
        }
      } catch (e) {
        if (e instanceof GrammarError) {
          throw e;
        } else if (e instanceof Error) {
          throw new VisitError(tree.data, tree, e);
        } else {
          throw e;
        }
      }
    } else {
      return this.__default__(tree.data, children, tree.meta);
    }
  }

  _call_userfunc_token(token) {
    let f;
    if (token && token.type && this && this[token.type]) {
      f = this && this[token.type];
      try {
        return f(token);
      } catch (e) {
        if (e instanceof GrammarError) {
          throw e;
        } else if (e instanceof Error) {
          throw new VisitError(token.type, token, e);
        } else {
          throw e;
        }
      }
    } else {
      return this.__default_token__(token);
    }
  }

  *_transform_children(children) {
    let res;
    for (const c of children) {
      if (c instanceof Tree) {
        res = this._transform_tree(c);
      } else if (this.__visit_tokens__ && c instanceof Token) {
        res = this._call_userfunc_token(c);
      } else {
        res = c;
      }
      if (res !== Discard) {
        yield res;
      }
    }
  }

  _transform_tree(tree) {
    let children = [...this._transform_children(tree.children)];
    return this._call_userfunc(tree, children);
  }

  /**
    Transform the given tree, and return the final result
  */
  transform(tree) {
    return this._transform_tree(tree);
  }

  /**
    Default function that is called if there is no attribute matching ``data``

        Can be overridden. Defaults to creating a new copy of the tree node (i.e. ``return Tree(data, children, meta)``)

  */
  __default__(data, children, meta) {
    return new Tree(data, children, meta);
  }

  /**
    Default function that is called if there is no attribute matching ``token.type``

        Can be overridden. Defaults to returning the token as-is.

  */
  __default_token__(token) {
    return token;
  }
}

/**
  Same as Transformer, but non-recursive, and changes the tree in-place instead of returning new instances

    Useful for huge trees. Conservative in memory.

*/

class Transformer_InPlace extends Transformer {
  _transform_tree(tree) {
    // Cancel recursion
    return this._call_userfunc(tree);
  }

  transform(tree) {
    for (const subtree of tree.iter_subtrees()) {
      subtree.children = [...this._transform_children(subtree.children)];
    }

    return this._transform_tree(tree);
  }
}

/**
  Same as Transformer but non-recursive.

    Like Transformer, it doesn't change the original tree.

    Useful for huge trees.

*/

class Transformer_NonRecursive extends Transformer {
  transform(tree) {
    let args, res, size;
    // Tree to postfix
    let rev_postfix = [];
    let q = [tree];
    while (q.length) {
      const t = q.pop();
      rev_postfix.push(t);
      if (t instanceof Tree) {
        q.push(...t.children);
      }
    }

    // Postfix to tree
    let stack = [];
    for (const x of [...rev_postfix].reverse()) {
      if (x instanceof Tree) {
        size = x.children.length;
        if (size) {
          args = stack.slice(-size);
          stack.splice(-size);
        } else {
          args = [];
        }
        res = this._call_userfunc(x, args);
        if (res !== Discard) {
          stack.push(res);
        }
      } else if (this.__visit_tokens__ && x instanceof Token) {
        res = this._call_userfunc_token(x);
        if (res !== Discard) {
          stack.push(res);
        }
      } else {
        stack.push(x);
      }
    }

    let [t] = stack;
    // We should have only one tree remaining
    return t;
  }
}

/**
  Same as Transformer, recursive, but changes the tree in-place instead of returning new instances
*/

class Transformer_InPlaceRecursive extends Transformer {
  _transform_tree(tree) {
    tree.children = [...this._transform_children(tree.children)];
    return this._call_userfunc(tree);
  }
}

// Visitors

class VisitorBase {
  _call_userfunc(tree) {
    const callback = this[tree.data]
    if (callback) {
      return callback(tree)
    } else {
      return this.__default__(tree);
    }
  }

  /**
    Default function that is called if there is no attribute matching ``tree.data``

        Can be overridden. Defaults to doing nothing.

  */
  __default__(tree) {
    return tree;
  }

  __class_getitem__(_) {
    return cls;
  }
}

/**
  Tree visitor, non-recursive (can handle huge trees).

    Visiting a node calls its methods (provided by the user via inheritance) according to ``tree.data``

*/

class Visitor extends VisitorBase {
  /**
    Visits the tree, starting with the leaves and finally the root (bottom-up)
  */
  visit(tree) {
    for (const subtree of tree.iter_subtrees()) {
      this._call_userfunc(subtree);
    }

    return tree;
  }

  /**
    Visit the tree, starting at the root, and ending at the leaves (top-down)
  */
  visit_topdown(tree) {
    for (const subtree of tree.iter_subtrees_topdown()) {
      this._call_userfunc(subtree);
    }

    return tree;
  }
}

/**
  Bottom-up visitor, recursive.

    Visiting a node calls its methods (provided by the user via inheritance) according to ``tree.data``

    Slightly faster than the non-recursive version.

*/

class Visitor_Recursive extends VisitorBase {
  /**
    Visits the tree, starting with the leaves and finally the root (bottom-up)
  */
  visit(tree) {
    for (const child of tree.children) {
      if (child instanceof Tree) {
        this.visit(child);
      }
    }

    this._call_userfunc(tree);
    return tree;
  }

  /**
    Visit the tree, starting at the root, and ending at the leaves (top-down)
  */
  visit_topdown(tree) {
    this._call_userfunc(tree);
    for (const child of tree.children) {
      if (child instanceof Tree) {
        this.visit_topdown(child);
      }
    }

    return tree;
  }
}

/**
  Interpreter walks the tree starting at the root.

    Visits the tree, starting with the root and finally the leaves (top-down)

    For each tree node, it calls its methods (provided by user via inheritance) according to ``tree.data``.

    Unlike ``Transformer`` and ``Visitor``, the Interpreter doesn't automatically visit its sub-branches.
    The user has to explicitly call ``visit``, ``visit_children``, or use the ``@visit_children_decor``.
    This allows the user to implement branching and loops.

*/

class Interpreter extends _Decoratable {
  visit(tree) {
    if (tree.data in this) {
      return this[tree.data](tree);
    } else {
      return this.__default__(tree)
    }
  }

  visit_children(tree) {
    return tree.children.map((child) =>
      child instanceof Tree ? this.visit(child) : child
    );
  }

  __default__(tree) {
    return this.visit_children(tree);
  }
}

//
// Grammar
//

var TOKEN_DEFAULT_PRIORITY = 0;
class Symbol extends Serialize {
  is_term = NotImplemented;
  constructor(name) {
    super();
    this.name = name;
  }

  eq(other) {
    return this.is_term === other.is_term && this.name === other.name;
  }

  repr() {
    return format("%s(%r)", type(this).name, this.name);
  }

  static get fullrepr() {
    return property(__repr__);
  }
  get fullrepr() {
    return this.constructor.fullrepr;
  }
  renamed(f) {
    return type(this)(f(this.name));
  }
}

class Terminal extends Symbol {
  static get __serialize_fields__() {
    return ["name", "filter_out"];
  }
  get is_term() {
    return true
  }

  constructor(name, filter_out = false) {
    super();
    this.name = name;
    this.filter_out = filter_out;
  }

  get fullrepr() {
    return format("%s(%r, %r)", type(this).name, this.name, this.filter_out);
  }

  renamed(f) {
    return type(this)(f(this.name), this.filter_out);
  }
}

class NonTerminal extends Symbol {
  static get __serialize_fields__() {
    return ["name"];
  }
  get is_term() {
    return false
  }

}

class RuleOptions extends Serialize {
  static get __serialize_fields__() {
    return [
      "keep_all_tokens",
      "expand1",
      "priority",
      "template_source",
      "empty_indices",
    ];
  }
  constructor(
    keep_all_tokens = false,
    expand1 = false,
    priority = null,
    template_source = null,
    empty_indices = []
  ) {
    super();
    this.keep_all_tokens = keep_all_tokens;
    this.expand1 = expand1;
    this.priority = priority;
    this.template_source = template_source;
    this.empty_indices = empty_indices;
  }

  repr() {
    return format(
      "RuleOptions(%r, %r, %r, %r)",
      this.keep_all_tokens,
      this.expand1,
      this.priority,
      this.template_source
    );
  }
}

/**

        origin : a symbol
        expansion : a list of symbols
        order : index of this expansion amongst all rules of the same name

*/

class Rule extends Serialize {
  static get __serialize_fields__() {
    return ["origin", "expansion", "order", "alias", "options"];
  }
  static get __serialize_namespace__() {
    return [Terminal, NonTerminal, RuleOptions];
  }
  constructor(origin, expansion, order = 0, alias = null, options = null) {
    super();
    this.origin = origin;
    this.expansion = expansion;
    this.alias = alias;
    this.order = order;
    this.options = options || new RuleOptions();
    this._hash = hash([this.origin, tuple(this.expansion)]);
  }

  _deserialize() {
    this._hash = hash([this.origin, tuple(this.expansion)]);
  }

  repr() {
    return format(
      "Rule(%r, %r, %r, %r)",
      this.origin,
      this.expansion,
      this.alias,
      this.options
    );
  }

  eq(other) {
    if (!(other instanceof Rule)) {
      return false;
    }

    return this.origin === other.origin && this.expansion === other.expansion;
  }
}

//
// Lexer
//

// Lexer Implementation

class Pattern extends Serialize {
  constructor(value, flags = [], raw = null) {
    super();
    this.value = value;
    this.flags = frozenset(flags);
    this.raw = raw;
  }

  repr() {
    return repr(this.to_regexp());
  }

  eq(other) {
    return (
      type(this) === type(other) &&
      this.value === other.value &&
      this.flags === other.flags
    );
  }

  to_regexp() {
    throw new NotImplementedError();
  }

  get min_width() {
    throw new NotImplementedError();
  }

  get max_width() {
    throw new NotImplementedError();
  }

  _get_flags(value) {
    return value;
  }
}

class PatternStr extends Pattern {
  static get __serialize_fields__() {
    return ["value", "flags"];
  }
  static get type() { return "str"; }
  to_regexp() {
    return this._get_flags(re.escape(this.value));
  }

  get min_width() {
    return this.value.length;
  }

  get max_width() {
    return this.value.length;
  }
}

class PatternRE extends Pattern {
  static get __serialize_fields__() {
    return ["value", "flags", "_width"];
  }
  static get type() { return "re"; }
  to_regexp() {
    return this._get_flags(this.value);
  }

  _get_width() {
    if (this._width === null) {
      this._width = get_regexp_width(this.to_regexp());
    }

    return this._width;
  }

  get min_width() {
    return this._get_width()[0];
  }

  get max_width() {
    return this._get_width()[1];
  }
}

class TerminalDef extends Serialize {
  static get __serialize_fields__() {
    return ["name", "pattern", "priority"];
  }
  static get __serialize_namespace__() {
    return [PatternStr, PatternRE];
  }
  constructor(name, pattern, priority = TOKEN_DEFAULT_PRIORITY) {
    super();
    this.name = name;
    this.pattern = pattern;
    this.priority = priority;
  }

  repr() {
    return format("%s(%r, %r)", type(this).name, this.name, this.pattern);
  }

  user_repr() {
    if (this.name.startsWith("__")) {
      // We represent a generated terminal
      return this.pattern.raw || this.name;
    } else {
      return this.name;
    }
  }
}

/**
  A string with meta-information, that is produced by the lexer.

    When parsing text, the resulting chunks of the input that haven't been discarded,
    will end up in the tree as Token instances. The Token class inherits from Python's ``str``,
    so normal string comparisons and operations will work as expected.

    Attributes:
        type: Name of the token (as specified in grammar)
        value: Value of the token (redundant, as ``token.value == token`` will always be true)
        start_pos: The index of the token in the text
        line: The line of the token in the text (starting with 1)
        column: The column of the token in the text (starting with 1)
        end_line: The line where the token ends
        end_column: The next column after the end of the token. For example,
            if the token is a single character with a column value of 4,
            end_column will be 5.
        end_pos: the index where the token ends (basically ``start_pos + len(token)``)

*/

class Token {
  constructor(
    type_,
    value,
    start_pos = null,
    line = null,
    column = null,
    end_line = null,
    end_column = null,
    end_pos = null
  ) {
    this.type = type_;
    this.start_pos = start_pos;
    this.value = value;
    this.line = line;
    this.column = column;
    this.end_line = end_line;
    this.end_column = end_column;
    this.end_pos = end_pos;
  }

  update(type_ = null, value = null) {
    return Token.new_borrow_pos(
      type_ !== null ? type_ : this.type,
      value !== null ? value : this.value,
      this
    );
  }

  static new_borrow_pos(type_, value, borrow_t) {
    const cls = this;
    return new cls(
      type_,
      value,
      borrow_t.start_pos,
      borrow_t.line,
      borrow_t.column,
      borrow_t.end_line,
      borrow_t.end_column,
      borrow_t.end_pos
    );
  }

  repr() {
    return format("Token(%r, %r)", this.type, this.value);
  }

  eq(other) {
    if (other instanceof Token && this.type !== other.type) {
      return false;
    }

    return str.__eq__(this, other);
  }

  static get __hash__() {
    return str.__hash__;
  }
}

class LineCounter {
  constructor(newline_char) {
    this.newline_char = newline_char;
    this.char_pos = 0;
    this.line = 1;
    this.column = 1;
    this.line_start_pos = 0;
  }

  eq(other) {
    if (!(other instanceof LineCounter)) {
      return NotImplemented;
    }

    return (
      this.char_pos === other.char_pos &&
      this.newline_char === other.newline_char
    );
  }

  /**
    Consume a token and calculate the new line & column.

        As an optional optimization, set test_newline=False if token doesn't contain a newline.

  */
  feed(token, test_newline = true) {
    let newlines;
    if (test_newline) {
      newlines = str_count(token, this.newline_char);
      if (newlines) {
        this.line += newlines;
        this.line_start_pos =
          this.char_pos + token.lastIndexOf(this.newline_char) + 1;
      }
    }

    this.char_pos += token.length;
    this.column = this.char_pos - this.line_start_pos + 1;
  }
}

class _UnlessCallback {
  constructor(scanner) {
    this.scanner = scanner;
  }

  __call__(t) {
    let _value;
    let res = this.scanner.match(t.value, 0);
    if (res) {
      [_value, t.type] = res;
    }

    return t;
  }
}

const UnlessCallback = callable_class(_UnlessCallback);
class _CallChain {
  constructor(callback1, callback2, cond) {
    this.callback1 = callback1;
    this.callback2 = callback2;
    this.cond = cond;
  }

  __call__(t) {
    let t2 = this.callback1(t);
    return this.cond(t2) ? this.callback2(t) : t2;
  }
}

const CallChain = callable_class(_CallChain);
function _create_unless(terminals, g_regex_flags, re_, use_bytes) {
  let s, unless;
  let tokens_by_type = classify(terminals, (t) => t.pattern.constructor.type);
  let embedded_strs = new Set();
  let callback = {};
  for (const retok of tokens_by_type.get('re') || []) {
    unless = [];
    for (const strtok of tokens_by_type.get('str') || []) {
      if (strtok.priority !== retok.priority) {
        continue;
      }

      s = strtok.pattern.value;
      if (s === _get_match(re_, retok.pattern.to_regexp(), s, g_regex_flags)) {
        unless.push(strtok);
        if (isSubset(new Set(strtok.pattern.flags), new Set(retok.pattern.flags))) {
          embedded_strs.add(strtok);
        }
      }
    }

    if (unless.length) {
      callback[retok.name] = new UnlessCallback(
        new Scanner(
          unless,
          g_regex_flags,
          re_,
          use_bytes,
          true,
        ),
      );
    }
  }

  let new_terminals = terminals
    .filter((t) => !embedded_strs.has(t))
    .map((t) => t);
  return [new_terminals, callback];
}

/**
    Expressions that may indicate newlines in a regexp:
        - newlines (\n)
        - escaped newline (\\n)
        - anything but ([^...])
        - any-char (.) when the flag (?s) exists
        - spaces (\s)

  */
function _regexp_has_newline(r) {
  return (
    r.includes("\n") ||
    r.includes("\\n") ||
    r.includes("\\s") ||
    r.includes("[^") ||
    (r.includes("(?s") && r.includes("."))
  );
}

/**
  Represents the current state of the lexer as it scans the text
    (Lexer objects are only instanciated per grammar, not per text)

*/

class LexerState {
  constructor(text, line_ctr = null, last_token = null) {
    this.text = text;
    this.line_ctr = line_ctr || new LineCounter("\n");
    this.last_token = last_token;
  }

  eq(other) {
    if (!(other instanceof LexerState)) {
      return NotImplemented;
    }

    return (
      this.text === other.text &&
      this.line_ctr === other.line_ctr &&
      this.last_token === other.last_token
    );
  }
}

/**
  A thread that ties a lexer instance and a lexer state, to be used by the parser

*/

class LexerThread {
  constructor(lexer, lexer_state) {
    this.lexer = lexer;
    this.state = lexer_state;
  }

  static from_text(lexer, text) {
    return new this(lexer, new LexerState(text));
  }

  lex(parser_state) {
    return this.lexer.lex(this.state, parser_state);
  }
}

/**
  Lexer interface

    Method Signatures:
        lex(self, lexer_state, parser_state) -> Iterator[Token]

*/

class Lexer extends ABC {
  lex(lexer_state, parser_state) {
    return NotImplemented;
  }
}

function sort_by_key_tuple(arr, key) {
  arr.sort( (a, b) => {
    let ta = key(a)
    let tb = key(b)
    for (let i=0; i<ta.length; i++) {
      if (ta[i] > tb[i]) {
        return 1;
      }
      else if (ta[i] < tb[i]) {
        return -1;
      }
    }
    return 0;
  })
}


class BasicLexer extends Lexer {
  constructor(conf) {
    super();
    let terminals = [...conf.terminals];
    this.re = conf.re_module;
    if (!conf.skip_validation) {
      // Sanitization
      for (const t of terminals) {
        try {
          this.re.compile(t.pattern.to_regexp(), conf.g_regex_flags);
        } catch (e) {
          if (e instanceof this.re.error) {
            throw new LexError(
              format("Cannot compile token %s: %s", t.name, t.pattern)
            );
          } else {
            throw e;
          }
        }
        if (t.pattern.min_width === 0) {
          throw new LexError(
            format(
              "Lexer does not allow zero-width terminals. (%s: %s)",
              t.name,
              t.pattern
            )
          );
        }
      }

      if (!(new Set(conf.ignore) <= new Set(terminals.map((t) => t.name)))) {
        throw new LexError(
          format(
            "Ignore terminals are not defined: %s",
            set_subtract(
              new Set(conf.ignore),
              new Set(terminals.map((t) => t.name))
            )
          )
        );
      }
    }

    // Init
    this.newline_types = frozenset(
      terminals
        .filter((t) => _regexp_has_newline(t.pattern.to_regexp()))
        .map((t) => t.name)
    );
    this.ignore_types = frozenset(conf.ignore);
    sort_by_key_tuple(terminals, (x) => [
        -x.priority,
        -x.pattern.max_width,
        -x.pattern.value.length,
        x.name,
    ]);
    this.terminals = terminals;
    this.user_callbacks = conf.callbacks;
    this.g_regex_flags = conf.g_regex_flags;
    this.use_bytes = conf.use_bytes;
    this.terminals_by_name = conf.terminals_by_name;
    this._scanner = null;
  }

  _build_scanner() {
    let terminals;
    [terminals, this.callback] = _create_unless(
      this.terminals,
      this.g_regex_flags,
      this.re,
      this.use_bytes
    );
    for (const [type_, f] of dict_items(this.user_callbacks)) {
      if (type_ in this.callback) {
        // Already a callback there, probably UnlessCallback
        this.callback[type_] = new CallChain(
          this.callback[type_],
          f,
          (t) => t.type === type_
        );
      } else {
        this.callback[type_] = f;
      }
    }

    this._scanner = new Scanner(
      terminals,
      this.g_regex_flags,
      this.re,
      this.use_bytes
    );
  }

  get scanner() {
    if (this._scanner === null) {
      this._build_scanner();
    }

    return this._scanner;
  }

  match(text, pos) {
    return this.scanner.match(text, pos);
  }

  *lex(state, parser_state) {
    try {
      while (true) {
        yield this.next_token(state, parser_state);
      }
    } catch (e) {
      if (e instanceof EOFError) {
        // pass
      } else {
        throw e;
      }
    }
  }

  next_token(lex_state, parser_state = null) {
    let allowed, res, t, t2, type_, value;
    let line_ctr = lex_state.line_ctr;
    while (line_ctr.char_pos < lex_state.text.length) {
      res = this.match(lex_state.text, line_ctr.char_pos);
      if (!res) {
        allowed = set_subtract(this.scanner.allowed_types, this.ignore_types);
        if (!allowed) {
          allowed = new Set(["<END-OF-FILE>"]);
        }

        throw new UnexpectedCharacters({
          seq: lex_state.text,
          lex_pos: line_ctr.char_pos,
          line: line_ctr.line,
          column: line_ctr.column,
          allowed: allowed,
          token_history: lex_state.last_token && [lex_state.last_token],
          state: parser_state,
          terminals_by_name: this.terminals_by_name,
        });
      }

      let [value, type_] = res;
      if (!this.ignore_types.has(type_)) {
        t = new Token(
          type_,
          value,
          line_ctr.char_pos,
          line_ctr.line,
          line_ctr.column
        );
        line_ctr.feed(value, this.newline_types.has(type_));
        t.end_line = line_ctr.line;
        t.end_column = line_ctr.column;
        t.end_pos = line_ctr.char_pos;
        if (t.type in this.callback) {
          t = this.callback[t.type](t);
          if (!(t instanceof Token)) {
            throw new LexError(
              format("Callbacks must return a token (returned %r)", t)
            );
          }
        }

        lex_state.last_token = t;
        return t;
      } else {
        if (type_ in this.callback) {
          t2 = new Token(
            type_,
            value,
            line_ctr.char_pos,
            line_ctr.line,
            line_ctr.column
          );
          this.callback[type_](t2);
        }

        line_ctr.feed(value, this.newline_types.has(type_));
      }
    }

    // EOF
    throw new EOFError(this);
  }
}

class ContextualLexer extends Lexer {
  constructor({ conf, states, always_accept = [] } = {}) {
    super();
    let accepts, key, lexer, lexer_conf;
    let terminals = [...conf.terminals];
    let terminals_by_name = conf.terminals_by_name;
    let trad_conf = copy(conf);
    trad_conf.terminals = terminals;
    let lexer_by_tokens = new Map();
    this.lexers = {};
    for (let [state, accepts] of dict_items(states)) {
      key = frozenset(accepts);
      if (lexer_by_tokens.has(key)) {
        lexer = lexer_by_tokens.get(key);
      } else {
        accepts = union(new Set(accepts), [
          ...new Set(conf.ignore),
          ...new Set(always_accept),
        ]);
        lexer_conf = copy(trad_conf);
        lexer_conf.terminals = [...accepts]
          .filter((n) => n in terminals_by_name)
          .map((n) => terminals_by_name[n]);
        lexer = new BasicLexer(lexer_conf);
        lexer_by_tokens.set(key, lexer);
      }
      this.lexers[state] = lexer;
    }

    this.root_lexer = new BasicLexer(trad_conf);
  }

  *lex(lexer_state, parser_state) {
    let last_token, lexer, token;
    try {
      while (true) {
        lexer = this.lexers[parser_state.position];
        yield lexer.next_token(lexer_state, parser_state);
      }
    } catch (e) {
      if (e instanceof EOFError) {
        // pass
      } else if (e instanceof UnexpectedCharacters) {
        // In the contextual lexer, UnexpectedCharacters can mean that the terminal is defined, but not in the current context.
        // This tests the input against the global context, to provide a nicer error.
        try {
          last_token = lexer_state.last_token;
          // Save last_token. Calling root_lexer.next_token will change this to the wrong token
          token = this.root_lexer.next_token(lexer_state, parser_state);
          throw new UnexpectedToken({
            token: token,
            expected: e.allowed,
            state: parser_state,
            token_history: [last_token],
            terminals_by_name: this.root_lexer.terminals_by_name,
          });
        } catch (e) {
          if (e instanceof UnexpectedCharacters) {
            throw e;
          } else {
            throw e;
          }
        }
      } else {
        throw e;
      }
    }
  }
}

//
// Common
//

class LexerConf extends Serialize {
  static get __serialize_fields__() {
    return ["terminals", "ignore", "g_regex_flags", "use_bytes", "lexer_type"];
  }
  static get __serialize_namespace__() {
    return [TerminalDef];
  }
  constructor({
    terminals,
    re_module,
    ignore = [],
    postlex = null,
    callbacks = null,
    g_regex_flags = '',
    skip_validation = false,
    use_bytes = false,
  } = {}) {
    super();
    this.terminals = terminals;
    this.terminals_by_name = Object.fromEntries(
      this.terminals.map((t) => [t.name, t])
    );
    this.ignore = ignore;
    this.postlex = postlex;
    this.callbacks = Object.keys(callbacks).length || {};
    this.g_regex_flags = g_regex_flags;
    this.re_module = re_module;
    this.skip_validation = skip_validation;
    this.use_bytes = use_bytes;
    this.lexer_type = null;
  }

  _deserialize() {
    this.terminals_by_name = Object.fromEntries(
      this.terminals.map((t) => [t.name, t])
    );
  }
}

class ParserConf extends Serialize {
  static get __serialize_fields__() {
    return ["rules", "start", "parser_type"];
  }
  constructor(rules, callbacks, start) {
    super();
    this.rules = rules;
    this.callbacks = callbacks;
    this.start = start;
    this.parser_type = null;
  }
}

//
// Parse Tree Builder
//

class _ExpandSingleChild {
  constructor(node_builder) {
    this.node_builder = node_builder;
  }

  __call__(children) {
    if (children.length === 1) {
      return children[0];
    } else {
      return this.node_builder(children);
    }
  }
}

const ExpandSingleChild = callable_class(_ExpandSingleChild);
class _PropagatePositions {
  constructor(node_builder, node_filter = null) {
    this.node_builder = node_builder;
    this.node_filter = node_filter;
  }

  __call__(children) {
    let first_meta, last_meta, res_meta;
    let res = this.node_builder(children);
    if (res instanceof Tree) {
      // Calculate positions while the tree is streaming, according to the rule:
      // - nodes start at the start of their first child's container,
      //   and end at the end of their last child's container.
      // Containers are nodes that take up space in text, but have been inlined in the tree.

      res_meta = res.meta;
      first_meta = this._pp_get_meta(children);
      if (first_meta !== null) {
        if (!("line" in res_meta)) {
          // meta was already set, probably because the rule has been inlined (e.g. `?rule`)
          res_meta.line =
            (first_meta && first_meta["container_line"]) || first_meta.line;
          res_meta.column =
            (first_meta && first_meta["container_column"]) || first_meta.column;
          res_meta.start_pos =
            (first_meta && first_meta["container_start_pos"]) ||
            first_meta.start_pos;
          res_meta.empty = false;
        }

        res_meta.container_line =
          (first_meta && first_meta["container_line"]) || first_meta.line;
        res_meta.container_column =
          (first_meta && first_meta["container_column"]) || first_meta.column;
      }

      last_meta = this._pp_get_meta([...children].reverse());
      if (last_meta !== null) {
        if (!("end_line" in res_meta)) {
          res_meta.end_line =
            (last_meta && last_meta["container_end_line"]) ||
            last_meta.end_line;
          res_meta.end_column =
            (last_meta && last_meta["container_end_column"]) ||
            last_meta.end_column;
          res_meta.end_pos =
            (last_meta && last_meta["container_end_pos"]) || last_meta.end_pos;
          res_meta.empty = false;
        }

        res_meta.container_end_line =
          (last_meta && last_meta["container_end_line"]) || last_meta.end_line;
        res_meta.container_end_column =
          (last_meta && last_meta["container_end_column"]) ||
          last_meta.end_column;
      }
    }

    return res;
  }

  _pp_get_meta(children) {
    for (const c of children) {
      if (this.node_filter !== null && !this.node_filter(c)) {
        continue;
      }

      if (c instanceof Tree) {
        if (!c.meta.empty) {
          return c.meta;
        }
      } else if (c instanceof Token) {
        return c;
      }
    }
  }
}

const PropagatePositions = callable_class(_PropagatePositions);
function make_propagate_positions(option) {
  if (callable(option)) {
    return partial({
      unknown_param_0: PropagatePositions,
      node_filter: option,
    });
  } else if (option === true) {
    return PropagatePositions;
  } else if (option === false) {
    return null;
  }

  throw new ConfigurationError(
    format("Invalid option for propagate_positions: %r", option)
  );
}

class _ChildFilter {
  constructor(to_include, append_none, node_builder) {
    this.node_builder = node_builder;
    this.to_include = to_include;
    this.append_none = append_none;
  }

  __call__(children) {
    let filtered = [];
    for (const [i, to_expand, add_none] of this.to_include) {
      if (add_none) {
        filtered.push(...list_repeat([null], add_none));
      }

      if (to_expand) {
        filtered.push(...children[i].children);
      } else {
        filtered.push(children[i]);
      }
    }

    if (this.append_none) {
      filtered.push(...list_repeat([null], this.append_none));
    }

    return this.node_builder(filtered);
  }
}

const ChildFilter = callable_class(_ChildFilter);
/**
  Optimized childfilter for LALR (assumes no duplication in parse tree, so it's safe to change it)
*/

class _ChildFilterLALR extends _ChildFilter {
  __call__(children) {
    let filtered = [];
    for (const [i, to_expand, add_none] of this.to_include) {
      if (add_none) {
        filtered.push(...list_repeat([null], add_none));
      }

      if (to_expand) {
        if (filtered.length) {
          filtered.push(...children[i].children);
        } else {
          // Optimize for left-recursion
          filtered = children[i].children;
        }
      } else {
        filtered.push(children[i]);
      }
    }

    if (this.append_none) {
      filtered.push(...list_repeat([null], this.append_none));
    }

    return this.node_builder(filtered);
  }
}

const ChildFilterLALR = callable_class(_ChildFilterLALR);
/**
  Optimized childfilter for LALR (assumes no duplication in parse tree, so it's safe to change it)
*/

class _ChildFilterLALR_NoPlaceholders extends _ChildFilter {
  constructor(to_include, node_builder) {
    super();
    this.node_builder = node_builder;
    this.to_include = to_include;
  }

  __call__(children) {
    let filtered = [];
    for (const [i, to_expand] of this.to_include) {
      if (to_expand) {
        if (filtered.length) {
          filtered.push(...children[i].children);
        } else {
          // Optimize for left-recursion
          filtered = children[i].children;
        }
      } else {
        filtered.push(children[i]);
      }
    }

    return this.node_builder(filtered);
  }
}

const ChildFilterLALR_NoPlaceholders = callable_class(
  _ChildFilterLALR_NoPlaceholders
);
function _should_expand(sym) {
  return !sym.is_term && sym.name.startsWith("_");
}

function maybe_create_child_filter(
  expansion,
  keep_all_tokens,
  ambiguous,
  _empty_indices
) {
  let empty_indices, s;
  // Prepare empty_indices as: How many Nones to insert at each index?
  if (_empty_indices.length) {
    s = _empty_indices.map((b) => (0 + b).toString()).join("");
    empty_indices = s.split("0").map((ones) => ones.length);
  } else {
    empty_indices = list_repeat([0], expansion.length + 1);
  }
  let to_include = [];
  let nones_to_add = 0;
  for (const [i, sym] of enumerate(expansion)) {
    nones_to_add += empty_indices[i];
    if (keep_all_tokens || !(sym.is_term && sym.filter_out)) {
      to_include.push([i, _should_expand(sym), nones_to_add]);
      nones_to_add = 0;
    }
  }

  nones_to_add += empty_indices[expansion.length];
  if (
    _empty_indices.length ||
    to_include.length < expansion.length ||
    any(to_include.map(([i, to_expand, _]) => to_expand))
  ) {
    if ((_empty_indices.length || ambiguous).length) {
      return partial(
        ambiguous ? ChildFilter : ChildFilterLALR,
        to_include,
        nones_to_add
      );
    } else {
      // LALR without placeholders
      return partial(
        ChildFilterLALR_NoPlaceholders,
        to_include.map(([i, x, _]) => [i, x])
      );
    }
  }
}


/**

    Propagate ambiguous intermediate nodes and their derivations up to the
    current rule.

    In general, converts

    rule
      _iambig
        _inter
          someChildren1
          ...
        _inter
          someChildren2
          ...
      someChildren3
      ...

    to

    _ambig
      rule
        someChildren1
        ...
        someChildren3
        ...
      rule
        someChildren2
        ...
        someChildren3
        ...
      rule
        childrenFromNestedIambigs
        ...
        someChildren3
        ...
      ...

    propagating up any nested '_iambig' nodes along the way.

*/

function inplace_transformer(func) {
  function f(children) {
    // function name in a Transformer is a rule name.
    let tree = new Tree(func.name, children);
    return func(tree);
  }

  f = wraps(func)(f);
  return f;
}

function apply_visit_wrapper(func, name, wrapper) {
  if (wrapper === _vargs_meta || wrapper === _vargs_meta_inline) {
    throw new NotImplementedError(
      "Meta args not supported for internal transformer"
    );
  }

  function f(children) {
    return wrapper(func, name, children, null);
  }

  f = wraps(func)(f);
  return f;
}

class ParseTreeBuilder {
  constructor(
    rules,
    tree_class,
    propagate_positions = false,
    ambiguous = false,
    maybe_placeholders = false
  ) {
    this.tree_class = tree_class;
    this.propagate_positions = propagate_positions;
    this.ambiguous = ambiguous;
    this.maybe_placeholders = maybe_placeholders;
    this.rule_builders = [...this._init_builders(rules)];
  }

  *_init_builders(rules) {
    let expand_single_child, keep_all_tokens, options, wrapper_chain;
    let propagate_positions = make_propagate_positions(
      this.propagate_positions
    );
    for (const rule of rules) {
      options = rule.options;
      keep_all_tokens = options.keep_all_tokens;
      expand_single_child = options.expand1;
      wrapper_chain = [
        ...filter(null, [
          expand_single_child && !rule.alias && ExpandSingleChild,
          maybe_create_child_filter(
            rule.expansion,
            keep_all_tokens,
            this.ambiguous,
            this.maybe_placeholders ? options.empty_indices : []
          ),
          propagate_positions,
        ]),
      ];
      yield [rule, wrapper_chain];
    }
  }

  create_callback(transformer = null) {
    let f, user_callback_name, wrapper;
    let callbacks = new Map();
    for (const [rule, wrapper_chain] of this.rule_builders) {
      user_callback_name =
        rule.alias || rule.options.template_source || rule.origin.name;
      if (transformer && transformer[user_callback_name]) {
        f = transformer && transformer[user_callback_name];
        wrapper = (f && f["visit_wrapper"]) || null;
        if (wrapper !== null) {
          f = apply_visit_wrapper(f, user_callback_name, wrapper);
        } else if (transformer instanceof Transformer_InPlace) {
          f = inplace_transformer(f);
        }
      } else {
        f = partial(this.tree_class, user_callback_name);
      }
      for (const w of wrapper_chain) {
        f = w(f);
      }

      if (callbacks.has(rule)) {
        throw new GrammarError(format("Rule '%s' already exists", rule));
      }

      callbacks.set(rule, f);
    }

    return callbacks;
  }
}

//
// Lalr Parser
//

class LALR_Parser extends Serialize {
  constructor({ parser_conf, debug = false } = {}) {
    super();
    let analysis = new LALR_Analyzer({
      unknown_param_0: parser_conf,
      debug: debug,
    });
    analysis.compute_lalr();
    let callbacks = parser_conf.callbacks;
    this._parse_table = analysis.parse_table;
    this.parser_conf = parser_conf;
    this.parser = new _Parser(analysis.parse_table, callbacks, debug);
  }

  static deserialize(data, memo, callbacks, debug = false) {
    const cls = this;
    let inst = new_object(cls);
    inst._parse_table = IntParseTable.deserialize(data, memo);
    inst.parser = new _Parser(inst._parse_table, callbacks, debug);
    return inst;
  }

  serialize(memo) {
    return this._parse_table.serialize(memo);
  }

  parse_interactive(lexer, start) {
    return this.parser.parse({
      lexer: lexer,
      start: start,
      start_interactive: true,
    });
  }

  parse({lexer, start, on_error = null} = {}) {
    let e, p, s;
    try {
      return this.parser.parse({ lexer: lexer, start: start });
    } catch (e) {
      if (e instanceof UnexpectedInput) {
        if (on_error === null) {
          throw e;
        }

        while (true) {
          if (e instanceof UnexpectedCharacters) {
            s = e.interactive_parser.lexer_thread.state;
            p = s.line_ctr.char_pos;
          }

          if (!on_error(e)) {
            throw e;
          }

          if (e instanceof UnexpectedCharacters) {
            // If user didn't change the character position, then we should
            if (p === s.line_ctr.char_pos) {
              s.line_ctr.feed(s.text.slice(p, p + 1));
            }
          }

          try {
            return e.interactive_parser.resume_parse();
          } catch (e2) {
            if (e2 instanceof UnexpectedToken) {
              if (
                e instanceof UnexpectedToken &&
                e.token.type === e2.token.type &&
                e2.token.type === "$END" &&
                e.interactive_parser.eq(e2.interactive_parser)
              ) {
                // Prevent infinite loop
                throw e2;
              }

              e = e2;
            } else if (e2 instanceof UnexpectedCharacters) {
              e = e2;
            } else {
              throw e2;
            }
          }
        }
      } else {
        throw e;
      }
    }
  }
}

class ParseConf {
  constructor(parse_table, callbacks, start) {
    this.parse_table = parse_table;
    this.start_state = this.parse_table.start_states[start];
    this.end_state = this.parse_table.end_states[start];
    this.states = this.parse_table.states;
    this.callbacks = callbacks;
    this.start = start;
  }
}

class ParserState {
  constructor(parse_conf, lexer, state_stack = null, value_stack = null) {
    this.parse_conf = parse_conf;
    this.lexer = lexer;
    this.state_stack = state_stack || [this.parse_conf.start_state];
    this.value_stack = value_stack || [];
  }

  get position() {
    return last_item(this.state_stack);
  }

  // Necessary for match_examples() to work

  eq(other) {
    if (!(other instanceof ParserState)) {
      return NotImplemented;
    }

    return (
      this.state_stack.length === other.state_stack.length &&
      this.position === other.position
    );
  }

  copy() {
    return copy(this);
  }

  feed_token(token, is_end = false) {
    let _action, action, arg, expected, new_state, rule, s, size, state, value;
    let state_stack = this.state_stack;
    let value_stack = this.value_stack;
    let states = this.parse_conf.states;
    let end_state = this.parse_conf.end_state;
    let callbacks = this.parse_conf.callbacks;
    while (true) {
      state = last_item(state_stack);
      if ( token.type in states[state] ) {
        [action, arg] = states[state][token.type];
      } else {
        expected = new Set(
          dict_keys(states[state])
            .filter((s) => isupper(s))
            .map((s) => s)
        );
        throw new UnexpectedToken({
          token: token,
          expected: expected,
          state: this,
          interactive_parser: null,
        });
      }
      if (action === Shift) {
        // shift once and return

        state_stack.push(arg);
        value_stack.push(
          !(token.type in callbacks) ? token : callbacks[token.type](token)
        );
        return;
      } else {
        // reduce+shift as many times as necessary
        rule = arg;
        size = rule.expansion.length;
        if (size) {
          s = value_stack.slice(-size);
          state_stack.splice(-size);
          value_stack.splice(-size);
        } else {
          s = [];
        }
        value = callbacks.get(rule)(s);
        [_action, new_state] = states[last_item(state_stack)][rule.origin.name];
        state_stack.push(new_state);
        value_stack.push(value);
        if (is_end && last_item(state_stack) === end_state) {
          return last_item(value_stack);
        }
      }
    }
  }
}

class _Parser {
  constructor(parse_table, callbacks, debug = false) {
    this.parse_table = parse_table;
    this.callbacks = callbacks;
    this.debug = debug;
  }

  parse({
    lexer,
    start,
    value_stack = null,
    state_stack = null,
    start_interactive = false,
  } = {}) {
    let parse_conf = new ParseConf(this.parse_table, this.callbacks, start);
    let parser_state = new ParserState(
      parse_conf,
      lexer,
      state_stack,
      value_stack
    );
    if (start_interactive) {
      return new InteractiveParser(this, parser_state, parser_state.lexer);
    }

    return this.parse_from_state(parser_state);
  }

  parse_from_state(state) {
    let end_token, token;
    // Main LALR-parser loop
    try {
      token = null;
      for (token of state.lexer.lex(state)) {
        state.feed_token(token);
      }

      end_token = token
        ? Token.new_borrow_pos("$END", "", token)
        : new Token("$END", "", 0, 1, 1);
      return state.feed_token(end_token, true);
    } catch (e) {
      if (e instanceof UnexpectedInput) {
        try {
          e.interactive_parser = new InteractiveParser(
            this,
            state,
            state.lexer
          );
        } catch (e) {
          if (e instanceof ReferenceError) {
            // pass
          } else {
            throw e;
          }
        }
        throw e;
      } else if (e instanceof Error) {
        if (this.debug) {
          console.log("");
          console.log("STATE STACK DUMP");
          console.log("----------------");
          for (const [i, s] of enumerate(state.state_stack)) {
            console.log(format("%d)", i), s);
          }

          console.log("");
        }

        throw e;
      } else {
        throw e;
      }
    }
  }
}

//
// Lalr Interactive Parser
//

// This module provides a LALR interactive parser, which is used for debugging and error handling

/**
  InteractiveParser gives you advanced control over parsing and error handling when parsing with LALR.

    For a simpler interface, see the ``on_error`` argument to ``Lark.parse()``.

*/

class InteractiveParser {
  constructor(parser, parser_state, lexer_thread) {
    this.parser = parser;
    this.parser_state = parser_state;
    this.lexer_thread = lexer_thread;
    this.result = null;
  }

  /**
    Feed the parser with a token, and advance it to the next state, as if it received it from the lexer.

        Note that ``token`` has to be an instance of ``Token``.

  */
  feed_token(token) {
    return this.parser_state.feed_token(token, token.type === "$END");
  }

  /**
    Step through the different stages of the parse, by reading tokens from the lexer
        and feeding them to the parser, one per iteration.

        Returns an iterator of the tokens it encounters.

        When the parse is over, the resulting tree can be found in ``InteractiveParser.result``.

  */
  *iter_parse() {
    for (const token of this.lexer_thread.lex(this.parser_state)) {
      yield token;
      this.result = this.feed_token(token);
    }
  }

  /**
    Try to feed the rest of the lexer state into the interactive parser.

        Note that this modifies the instance in place and does not feed an '$END' Token

  */
  exhaust_lexer() {
    return [...this.iter_parse()];
  }

  /**
    Feed a '$END' Token. Borrows from 'last_token' if given.
  */
  feed_eof(last_token = null) {
    let eof =
      last_token !== null
        ? Token.new_borrow_pos("$END", "", last_token)
        : new Token("$END", "", 0, 1, 1);
    return this.feed_token(eof);
  }

  copy() {
    return copy(this);
  }

  eq(other) {
    if (!(other instanceof InteractiveParser)) {
      return false;
    }

    return (
      this.parser_state === other.parser_state &&
      this.lexer_thread === other.lexer_thread
    );
  }

  /**
    Convert to an ``ImmutableInteractiveParser``.
  */
  as_immutable() {
    let p = copy(this);
    return new ImmutableInteractiveParser(
      p.parser,
      p.parser_state,
      p.lexer_thread
    );
  }

  /**
    Print the output of ``choices()`` in a way that's easier to read.
  */
  pretty() {
    let out = ["Parser choices:"];
    for (const [k, v] of dict_items(this.choices())) {
      out.push(format("\t- %s -> %r", k, v));
    }

    out.push(format("stack size: %s", this.parser_state.state_stack.length));
    return out.join("\n");
  }

  /**
    Returns a dictionary of token types, matched to their action in the parser.

        Only returns token types that are accepted by the current state.

        Updated by ``feed_token()``.

  */
  choices() {
    return this.parser_state.parse_conf.parse_table.states[
      this.parser_state.position
    ];
  }

  /**
    Returns the set of possible tokens that will advance the parser into a new valid state.
  */
  accepts() {
    let new_cursor;
    let accepts = new Set();
    for (const t of this.choices()) {
      if (isupper(t)) {
        // is terminal?
        new_cursor = copy(this);
        let exc = null;
        try {
          new_cursor.feed_token(new Token(t, ""));
        } catch (e) {
          exc = e;
          if (e instanceof UnexpectedToken) {
            // pass
          } else {
            throw e;
          }
        }
        if (!exc) {
          accepts.add(t);
        }
      }
    }

    return accepts;
  }

  /**
    Resume automated parsing from the current state.
  */
  resume_parse() {
    return this.parser.parse_from_state(this.parser_state);
  }
}

/**
  Same as ``InteractiveParser``, but operations create a new instance instead
    of changing it in-place.

*/

class ImmutableInteractiveParser extends InteractiveParser {
  result = null;
  feed_token(token) {
    let c = copy(this);
    c.result = InteractiveParser.feed_token(c, token);
    return c;
  }

  /**
    Try to feed the rest of the lexer state into the parser.

        Note that this returns a new ImmutableInteractiveParser and does not feed an '$END' Token
  */
  exhaust_lexer() {
    let cursor = this.as_mutable();
    cursor.exhaust_lexer();
    return cursor.as_immutable();
  }

  /**
    Convert to an ``InteractiveParser``.
  */
  as_mutable() {
    let p = copy(this);
    return new InteractiveParser(p.parser, p.parser_state, p.lexer_thread);
  }
}

//
// Lalr Analysis
//

class Action {
  constructor(name) {
    this.name = name;
  }

  repr() {
    return this.toString();
  }
}

var Shift = new Action("Shift");
var Reduce = new Action("Reduce");
class ParseTable {
  constructor(states, start_states, end_states) {
    this.states = states;
    this.start_states = start_states;
    this.end_states = end_states;
  }

  serialize(memo) {
    let tokens = new Enumerator();
    let states = Object.fromEntries(
      dict_items(this.states).map(([state, actions]) => [
        state,
        Object.fromEntries(
          dict_items(actions).map(([token, [action, arg]]) => [
            dict_get(tokens, token),
            action === Reduce ? [1, arg.serialize(memo)] : [0, arg],
          ])
        ),
      ])
    );
    return {
      tokens: tokens.reversed(),
      states: states,
      start_states: this.start_states,
      end_states: this.end_states,
    };
  }

  static deserialize(data, memo) {
    const cls = this;
    let tokens = data["tokens"];
    let states = Object.fromEntries(
      dict_items(data["states"]).map(([state, actions]) => [
        state,
        Object.fromEntries(
          dict_items(actions).map(([token, [action, arg]]) => [
            tokens[token],
            action === 1 ? [Reduce, Rule.deserialize(arg, memo)] : [Shift, arg],
          ])
        ),
      ])
    );
    return new cls(states, data["start_states"], data["end_states"]);
  }
}

class IntParseTable extends ParseTable {
  static from_ParseTable(parse_table) {
    const cls = this;
    let enum_ = [...parse_table.states];
    let state_to_idx = Object.fromEntries(
      enumerate(enum_).map(([i, s]) => [s, i])
    );
    let int_states = {};
    for (let [s, la] of dict_items(parse_table.states)) {
      la = Object.fromEntries(
        dict_items(la).map(([k, v]) => [
          k,
          v[0] === Shift ? [v[0], state_to_idx[v[1]]] : v,
        ])
      );
      int_states[state_to_idx[s]] = la;
    }

    let start_states = Object.fromEntries(
      dict_items(parse_table.start_states).map(([start, s]) => [
        start,
        state_to_idx[s],
      ])
    );
    let end_states = Object.fromEntries(
      dict_items(parse_table.end_states).map(([start, s]) => [
        start,
        state_to_idx[s],
      ])
    );
    return new cls(int_states, start_states, end_states);
  }
}

//
// Parser Frontends
//

function _wrap_lexer(lexer_class) {
  let future_interface =
    (lexer_class && lexer_class["__future_interface__"]) || false;
  if (future_interface) {
    return lexer_class;
  } else {
    class CustomLexerWrapper extends Lexer {
      constructor(lexer_conf) {
        super();
        this.lexer = lexer_class(lexer_conf);
      }

      lex(lexer_state, parser_state) {
        return this.lexer.lex(lexer_state.text);
      }
    }

    return CustomLexerWrapper;
  }
}

class MakeParsingFrontend {
  constructor(parser_type, lexer_type) {
    this.parser_type = parser_type;
    this.lexer_type = lexer_type;
  }

  deserialize(data, memo, lexer_conf, callbacks, options) {
    let parser_conf = ParserConf.deserialize(data["parser_conf"], memo);
    let parser = LALR_Parser.deserialize(
      data["parser"],
      memo,
      callbacks,
      options.debug
    );
    parser_conf.callbacks = callbacks;
    return new ParsingFrontend({
      lexer_conf: lexer_conf,
      parser_conf: parser_conf,
      options: options,
      parser: parser,
    });
  }
}

// ... Continued later in the module

function _deserialize_parsing_frontend(
  data,
  memo,
  lexer_conf,
  callbacks,
  options
) {
  let parser_conf = ParserConf.deserialize(data["parser_conf"], memo);
  let parser = LALR_Parser.deserialize(data["parser"], memo, callbacks, options.debug);
  parser_conf.callbacks = callbacks;
  return new ParsingFrontend({
    lexer_conf: lexer_conf,
    parser_conf: parser_conf,
    options: options,
    parser: parser,
  });
}

var _parser_creators = {}

class ParsingFrontend extends Serialize {
  static get __serialize_fields__() {
    return ["lexer_conf", "parser_conf", "parser"];
  }
  constructor({ lexer_conf, parser_conf, options, parser = null } = {}) {
    super();
    let create_lexer, create_parser;
    this.parser_conf = parser_conf;
    this.lexer_conf = lexer_conf;
    this.options = options;
    // Set-up parser
    if (parser) {
      // From cache
      this.parser = parser;
    } else {
      create_parser = dict_get(_parser_creators, parser_conf.parser_type);
      this.parser = create_parser(lexer_conf, parser_conf, options);
    }
    // Set-up lexer
    let lexer_type = lexer_conf.lexer_type;
    this.skip_lexer = false;
    if (["dynamic", "dynamic_complete"].includes(lexer_type)) {
      this.skip_lexer = true;
      return;
    }

    const lexers = {
        basic: create_basic_lexer,
        contextual: create_contextual_lexer
    }
    if (lexer_type in lexers) {
      create_lexer = lexers[lexer_type];
      this.lexer = create_lexer(
        lexer_conf,
        this.parser,
        lexer_conf.postlex,
        options
      );
    } else {
      this.lexer = _wrap_lexer(lexer_type)(lexer_conf);
    }
    if (lexer_conf.postlex) {
      this.lexer = new PostLexConnector(this.lexer, lexer_conf.postlex);
    }
  }

  _verify_start(start = null) {
    let start_decls;
    if (start === null) {
      start_decls = this.parser_conf.start;
      if (start_decls.length > 1) {
        throw new ConfigurationError(
          "Lark initialized with more than 1 possible start rule. Must specify which start rule to parse",
          start_decls
        );
      }

      [start] = start_decls;
    } else if (!(this.parser_conf.start.includes(start))) {
      throw new ConfigurationError(
        format(
          "Unknown start rule %s. Must be one of %r",
          start,
          this.parser_conf.start
        )
      );
    }

    return start;
  }

  _make_lexer_thread(text) {
    return this.skip_lexer ? text : LexerThread.from_text(this.lexer, text);
  }

  parse(text, start = null, on_error = null) {
    let chosen_start = this._verify_start(start);
    let kw = on_error === null ? {} : { on_error: on_error };
    let stream = this._make_lexer_thread(text);
    return this.parser.parse({
      lexer: stream,
      start: chosen_start,
      ...kw,
    });
  }

  parse_interactive(text = null, start = null) {
    let chosen_start = this._verify_start(start);
    if (this.parser_conf.parser_type !== "lalr") {
      throw new ConfigurationError(
        "parse_interactive() currently only works with parser='lalr' "
      );
    }

    let stream = this._make_lexer_thread(text);
    return this.parser.parse_interactive(stream, chosen_start);
  }
}

function _validate_frontend_args(parser, lexer) {
  let expected;
  assert_config(parser, ["lalr", "earley", "cyk"]);
  if (!(typeof lexer === "object")) {
    // not custom lexer?
    expected = {
      lalr: ["basic", "contextual"],
      earley: ["basic", "dynamic", "dynamic_complete"],
      cyk: ["basic"],
    }[parser];
    assert_config(
      lexer,
      expected,
      format(
        "Parser %r does not support lexer %%r, expected one of %%s",
        parser
      )
    );
  }
}

function _get_lexer_callbacks(transformer, terminals) {
  let callback;
  let result = {};
  for (const terminal of terminals) {
    callback = (transformer && transformer[terminal.name]) || null;
    if (callback !== null) {
      result[terminal.name] = callback;
    }
  }

  return result;
}

class PostLexConnector {
  constructor(lexer, postlexer) {
    this.lexer = lexer;
    this.postlexer = postlexer;
  }

  lex(lexer_state, parser_state) {
    let i = this.lexer.lex(lexer_state, parser_state);
    return this.postlexer.process(i);
  }
}

function create_basic_lexer(lexer_conf, parser, postlex, options) {
  return new BasicLexer(lexer_conf);
}

function create_contextual_lexer(lexer_conf, parser, postlex, options) {
  let states = Object.fromEntries(
    dict_items(parser._parse_table.states).map(([idx, t]) => [
      idx,
      [...dict_keys(t)],
    ])
  );
  let always_accept = postlex ? postlex.always_accept : [];
  return new ContextualLexer({
    conf: lexer_conf,
    states: states,
    always_accept: always_accept,
  });
}

function create_lalr_parser(lexer_conf, parser_conf, options = null) {
  let debug = options ? options.debug : false;
  return new LALR_Parser({ parser_conf: parser_conf, debug: debug });
}

_parser_creators["lalr"] = create_lalr_parser;

//
// Lark
//

class PostLex extends ABC {
  process(stream) {
    return stream;
  }

  always_accept = [];
}

/**
  Specifies the options for Lark


*/

class LarkOptions extends Serialize {
  OPTIONS_DOC = `
    **===  General Options  ===**

    start
            The start symbol. Either a string, or a list of strings for multiple possible starts (Default: "start")
    debug
            Display debug information and extra warnings. Use only when debugging (Default: \`\`False\`\`)
            When used with Earley, it generates a forest graph as "sppf.png", if 'dot' is installed.
    transformer
            Applies the transformer to every parse tree (equivalent to applying it after the parse, but faster)
    propagate_positions
            Propagates (line, column, end_line, end_column) attributes into all tree branches.
            Accepts \`\`False\`\`, \`\`True\`\`, or a callable, which will filter which nodes to ignore when propagating.
    maybe_placeholders
            When \`\`True\`\`, the \`\`[]\`\` operator returns \`\`None\`\` when not matched.
            When \`\`False\`\`,  \`\`[]\`\` behaves like the \`\`?\`\` operator, and returns no value at all.
            (default= \`\`True\`\`)
    cache
            Cache the results of the Lark grammar analysis, for x2 to x3 faster loading. LALR only for now.

            - When \`\`False\`\`, does nothing (default)
            - When \`\`True\`\`, caches to a temporary file in the local directory
            - When given a string, caches to the path pointed by the string
    regex
            When True, uses the \`\`regex\`\` module instead of the stdlib \`\`re\`\`.
    g_regex_flags
            Flags that are applied to all terminals (both regex and strings)
    keep_all_tokens
            Prevent the tree builder from automagically removing "punctuation" tokens (Default: \`\`False\`\`)
    tree_class
            Lark will produce trees comprised of instances of this class instead of the default \`\`lark.Tree\`\`.

    **=== Algorithm Options ===**

    parser
            Decides which parser engine to use. Accepts "earley" or "lalr". (Default: "earley").
            (there is also a "cyk" option for legacy)
    lexer
            Decides whether or not to use a lexer stage

            - "auto" (default): Choose for me based on the parser
            - "basic": Use a basic lexer
            - "contextual": Stronger lexer (only works with parser="lalr")
            - "dynamic": Flexible and powerful (only with parser="earley")
            - "dynamic_complete": Same as dynamic, but tries *every* variation of tokenizing possible.
    ambiguity
            Decides how to handle ambiguity in the parse. Only relevant if parser="earley"

            - "resolve": The parser will automatically choose the simplest derivation
              (it chooses consistently: greedy for tokens, non-greedy for rules)
            - "explicit": The parser will return all derivations wrapped in "_ambig" tree nodes (i.e. a forest).
            - "forest": The parser will return the root of the shared packed parse forest.

    **=== Misc. / Domain Specific Options ===**

    postlex
            Lexer post-processing (Default: \`\`None\`\`) Only works with the basic and contextual lexers.
    priority
            How priorities should be evaluated - "auto", \`\`None\`\`, "normal", "invert" (Default: "auto")
    lexer_callbacks
            Dictionary of callbacks for the lexer. May alter tokens during lexing. Use with caution.
    use_bytes
            Accept an input of type \`\`bytes\`\` instead of \`\`str\`\`.
    edit_terminals
            A callback for editing the terminals before parse.
    import_paths
            A List of either paths or loader functions to specify from where grammars are imported
    source_path
            Override the source of from where the grammar was loaded. Useful for relative imports and unconventional grammar loading
    **=== End of Options ===**
    `;
  // Adding a new option needs to be done in multiple places:
  // - In the dictionary below. This is the primary truth of which options `Lark.__init__` accepts
  // - In the docstring above. It is used both for the docstring of `LarkOptions` and `Lark`, and in readthedocs
  // - As an attribute of `LarkOptions` above
  // - Potentially in `_LOAD_ALLOWED_OPTIONS` below this class, when the option doesn't change how the grammar is loaded
  // - Potentially in `lark.tools.__init__`, if it makes sense, and it can easily be passed as a cmd argument
  _defaults = {
    debug: false,
    keep_all_tokens: false,
    tree_class: null,
    cache: false,
    postlex: null,
    parser: "earley",
    lexer: "auto",
    transformer: null,
    start: "start",
    priority: "auto",
    ambiguity: "auto",
    regex: false,
    propagate_positions: false,
    lexer_callbacks: {},
    maybe_placeholders: true,
    edit_terminals: null,
    g_regex_flags: '',
    use_bytes: false,
    import_paths: [],
    source_path: null,
    _plugins: null,
  };
  constructor(options_dict) {
    super();
    let value;
    let o = dict(options_dict);
    let options = this;
    for (const [name, default_] of dict_items(this._defaults)) {
      if (name in o) {
        value = dict_pop(o, name);
        if (
          typeof default_ === "boolean" &&
          !["cache", "use_bytes", "propagate_positions"].includes(name)
        ) {
          value = bool(value);
        }
      } else {
        value = default_;
      }
      options[name] = value;
    }

    if (typeof options["start"] === "string") {
      options["start"] = [options["start"]];
    }

    this["options"] = options;
    assert_config(this.parser, ["earley", "lalr", "cyk", null]);
    if (this.parser === "earley" && this.transformer) {
      throw new ConfigurationError(
        "Cannot specify an embedded transformer when using the Earley algorithm. " +
          "Please use your transformer on the resulting parse tree, or use a different algorithm (i.e. LALR)"
      );
    }

    if (Object.keys(o).length) {
      throw new ConfigurationError(format("Unknown options: %s", dict_keys(o)));
    }
  }

  serialize(memo) {
    return this.options;
  }

  static deserialize(data, memo) {
    const cls = this;
    return new cls(data);
  }
}

// Options that can be passed to the Lark parser, even when it was loaded from cache/standalone.
// These options are only used outside of `load_grammar`.
var _LOAD_ALLOWED_OPTIONS = new Set([
  "postlex",
  "transformer",
  "lexer_callbacks",
  "use_bytes",
  "debug",
  "g_regex_flags",
  "regex",
  "propagate_positions",
  "tree_class",
]);
var _VALID_PRIORITY_OPTIONS = ["auto", "normal", "invert", null];
var _VALID_AMBIGUITY_OPTIONS = ["auto", "resolve", "explicit", "forest"];
/**
  Main interface for the library.

    It's mostly a thin wrapper for the many different parsers, and for the tree constructor.

    Parameters:
        grammar: a string or file-object containing the grammar spec (using Lark's ebnf syntax)
        options: a dictionary controlling various aspects of Lark.

    Example:
        >>> Lark(r'''start: "foo" ''')
        Lark(...)

*/

class Lark extends Serialize {
  static get __serialize_fields__() {
    return ["parser", "rules", "options"];
  }
  _build_lexer(dont_ignore = false) {
    let lexer_conf = this.lexer_conf;
    if (dont_ignore) {
      lexer_conf = copy(lexer_conf);
      lexer_conf.ignore = [];
    }

    return new BasicLexer(lexer_conf);
  }

  _prepare_callbacks() {
    this._callbacks = new Map();
    // we don't need these callbacks if we aren't building a tree
    if (this.options.ambiguity !== "forest") {
      this._parse_tree_builder = new ParseTreeBuilder(
        this.rules,
        this.options.tree_class || make_constructor(Tree),
        this.options.propagate_positions,
        this.options.parser !== "lalr" && this.options.ambiguity === "explicit",
        this.options.maybe_placeholders
      );
      this._callbacks = this._parse_tree_builder.create_callback(
        this.options.transformer
      );
    }

    dict_update(
      this._callbacks,
      _get_lexer_callbacks(this.options.transformer, this.terminals)
    );
  }

  /**
    Saves the instance into the given file object

        Useful for caching and multiprocessing.

  */
  /**
    Loads an instance from the given file object

        Useful for caching and multiprocessing.

  */
  _deserialize_lexer_conf(data, memo, options) {
    let lexer_conf = LexerConf.deserialize(data["lexer_conf"], memo);
    lexer_conf.callbacks = options.lexer_callbacks || {};
    lexer_conf.re_module = options.regex ? regex : re;
    lexer_conf.use_bytes = options.use_bytes;
    lexer_conf.g_regex_flags = options.g_regex_flags || '';
    lexer_conf.skip_validation = true;
    lexer_conf.postlex = options.postlex;
    return lexer_conf;
  }

  _load({ f, ...kwargs } = {}) {
    let d;
    if (is_dict(f)) {
      d = f;
    } else {
      d = pickle.load(f);
    }
    let memo_json = d["memo"];
    let data = d["data"];
    let memo = SerializeMemoizer.deserialize(
      memo_json,
      { Rule: Rule, TerminalDef: TerminalDef },
      {}
    );
    let options = dict(data["options"]);
    // if (
    //   (new Set(kwargs) - _LOAD_ALLOWED_OPTIONS) &
    //   new Set(LarkOptions._defaults)
    // ) {
    //   throw new ConfigurationError(
    //     "Some options are not allowed when loading a Parser: {}".format(
    //       new Set(kwargs) - _LOAD_ALLOWED_OPTIONS
    //     )
    //   );
    // }

    dict_update(options, kwargs);
    this.options = LarkOptions.deserialize(options, memo);
    this.rules = data["rules"].map((r) => Rule.deserialize(r, memo));
    this.source_path = "<deserialized>";
    _validate_frontend_args(this.options.parser, this.options.lexer);
    this.lexer_conf = this._deserialize_lexer_conf(
      data["parser"],
      memo,
      this.options
    );
    this.terminals = this.lexer_conf.terminals;
    this._prepare_callbacks();
    this._terminals_dict = Object.fromEntries(
      this.terminals.map((t) => [t.name, t])
    );
    this.parser = _deserialize_parsing_frontend(
      data["parser"],
      memo,
      this.lexer_conf,
      this._callbacks,
      this.options
    );
    return this;
  }

  static _load_from_dict({ data, memo, ...kwargs } = {}) {
    const cls = this;
    let inst = new_object(cls);
    return inst._load({
      f: { data: data, memo: memo },
      ...kwargs,
    });
  }

  /**
    Create an instance of Lark with the grammar given by its filename

        If ``rel_to`` is provided, the function will find the grammar filename in relation to it.

        Example:

            >>> Lark.open("grammar_file.lark", rel_to=__file__, parser="lalr")
            Lark(...)


  */
  /**
    Create an instance of Lark with the grammar loaded from within the package `package`.
        This allows grammar loading from zipapps.

        Imports in the grammar will use the `package` and `search_paths` provided, through `FromPackageLoader`

        Example:

            Lark.open_from_package(__name__, "example.lark", ("grammars",), parser=...)

  */
  repr() {
    return format(
      "Lark(open(%r), parser=%r, lexer=%r, ...)",
      this.source_path,
      this.options.parser,
      this.options.lexer
    );
  }

  /**
    Only lex (and postlex) the text, without parsing it. Only relevant when lexer='basic'

        When dont_ignore=True, the lexer will return all tokens, even those marked for %ignore.

        :raises UnexpectedCharacters: In case the lexer cannot find a suitable match.

  */
  lex(text, dont_ignore = false) {
    let lexer;
    if (!("lexer" in this) || dont_ignore) {
      lexer = this._build_lexer(dont_ignore);
    } else {
      lexer = this.lexer;
    }
    let lexer_thread = LexerThread.from_text(lexer, text);
    let stream = lexer_thread.lex(null);
    if (this.options.postlex) {
      return this.options.postlex.process(stream);
    }

    return stream;
  }

  /**
    Get information about a terminal
  */
  get_terminal(name) {
    return this._terminals_dict[name];
  }

  /**
    Start an interactive parsing session.

        Parameters:
            text (str, optional): Text to be parsed. Required for ``resume_parse()``.
            start (str, optional): Start symbol

        Returns:
            A new InteractiveParser instance.

        See Also: ``Lark.parse()``

  */
  parse_interactive(text = null, start = null) {
    return this.parser.parse_interactive({
      unknown_param_0: text,
      start: start,
    });
  }

  /**
    Parse the given text, according to the options provided.

        Parameters:
            text (str): Text to be parsed.
            start (str, optional): Required if Lark was given multiple possible start symbols (using the start option).
            on_error (function, optional): if provided, will be called on UnexpectedToken error. Return true to resume parsing.
                LALR only. See examples/advanced/error_handling.py for an example of how to use on_error.

        Returns:
            If a transformer is supplied to ``__init__``, returns whatever is the
            result of the transformation. Otherwise, returns a Tree instance.

        :raises UnexpectedInput: On a parse error, one of these sub-exceptions will rise:
                ``UnexpectedCharacters``, ``UnexpectedToken``, or ``UnexpectedEOF``.
                For convenience, these sub-exceptions also inherit from ``ParserError`` and ``LexerError``.


  */
  parse(text, start = null, on_error = null) {
    return this.parser.parse(text, start, on_error);
  }
}

//
// Indenter
//

class DedentError extends LarkError {
  // pass
}

class Indenter extends PostLex {
  constructor() {
    super();
    this.paren_level = 0;
    this.indent_level = [0];
  }

  *handle_NL(token) {
    if (this.paren_level > 0) {
      return;
    }

    yield token;
    let indent_str = rsplit(token.value, "\n", 1)[1];
    // Tabs and spaces
    let indent =
      str_count(indent_str, " ") + str_count(indent_str, "\t") * this.tab_len;
    if (indent > last_item(this.indent_level)) {
      this.indent_level.push(indent);
      yield Token.new_borrow_pos(this.INDENT_type, indent_str, token);
    } else {
      while (indent < last_item(this.indent_level)) {
        this.indent_level.pop();
        yield Token.new_borrow_pos(this.DEDENT_type, indent_str, token);
      }

      if (indent !== last_item(this.indent_level)) {
        throw new DedentError(
          format(
            "Unexpected dedent to column %s. Expected dedent to %s",
            indent,
            last_item(this.indent_level)
          )
        );
      }
    }
  }

  *_process(stream) {
    for (const token of stream) {
      if (token.type === this.NL_type) {
        yield* this.handle_NL(token);
      } else {
        yield token;
      }
      if (this.OPEN_PAREN_types.includes(token.type)) {
        this.paren_level += 1;
      } else if (this.CLOSE_PAREN_types.includes(token.type)) {
        this.paren_level -= 1;
      }
    }

    while (this.indent_level.length > 1) {
      this.indent_level.pop();
      yield new Token(this.DEDENT_type, "");
    }
  }

  process(stream) {
    this.paren_level = 0;
    this.indent_level = [0];
    return this._process(stream);
  }

  // XXX Hack for ContextualLexer. Maybe there's a more elegant solution?

  get always_accept() {
    return [this.NL_type];
  }

  get NL_type() {
    throw new NotImplementedError();
  }

  get OPEN_PAREN_types() {
    throw new NotImplementedError();
  }

  get CLOSE_PAREN_types() {
    throw new NotImplementedError();
  }

  get INDENT_type() {
    throw new NotImplementedError();
  }

  get DEDENT_type() {
    throw new NotImplementedError();
  }

  get tab_len() {
    throw new NotImplementedError();
  }
}

class PythonIndenter extends Indenter {
  static get NL_type() {
    return "_NEWLINE";
  }
  get NL_type() {
    return this.constructor.NL_type;
  }
  static get OPEN_PAREN_types() {
    return ["LPAR", "LSQB", "LBRACE"];
  }
  get OPEN_PAREN_types() {
    return this.constructor.OPEN_PAREN_types;
  }
  static get CLOSE_PAREN_types() {
    return ["RPAR", "RSQB", "RBRACE"];
  }
  get CLOSE_PAREN_types() {
    return this.constructor.CLOSE_PAREN_types;
  }
  static get INDENT_type() {
    return "_INDENT";
  }
  get INDENT_type() {
    return this.constructor.INDENT_type;
  }
  static get DEDENT_type() {
    return "_DEDENT";
  }
  get DEDENT_type() {
    return this.constructor.DEDENT_type;
  }
  static get tab_len() {
    return 8;
  }
  get tab_len() {
    return this.constructor.tab_len;
  }
}

const NAMESPACE = {
    Terminal: Terminal,
    NonTerminal: NonTerminal,
    RuleOptions: RuleOptions,
    PatternStr: PatternStr,
    PatternRE: PatternRE,
    TerminalDef: TerminalDef
}

module.exports = {
  LarkError,
  ConfigurationError,
  GrammarError,
  ParseError,
  LexError,
  UnexpectedInput,
  UnexpectedEOF,
  UnexpectedCharacters,
  UnexpectedToken,
  VisitError,
  Meta,
  Tree,
  Discard,
  Transformer,
  Transformer_InPlace,
  Transformer_NonRecursive,
  Transformer_InPlaceRecursive,
  VisitorBase,
  Visitor,
  Visitor_Recursive,
  Interpreter,
  Symbol,
  Terminal,
  NonTerminal,
  RuleOptions,
  Rule,
  Pattern,
  PatternStr,
  PatternRE,
  TerminalDef,
  Token,
  Lexer,
  LexerConf,
  ParserConf,
  InteractiveParser,
  ImmutableInteractiveParser,
  PostLex,
  Lark,
  DedentError,
  Indenter,
  PythonIndenter,
  get_parser,
};

var DATA={
  "parser": {
    "lexer_conf": {
      "terminals": [
        {
          "@": 0
        },
        {
          "@": 1
        },
        {
          "@": 2
        },
        {
          "@": 3
        },
        {
          "@": 4
        },
        {
          "@": 5
        },
        {
          "@": 6
        },
        {
          "@": 7
        },
        {
          "@": 8
        },
        {
          "@": 9
        },
        {
          "@": 10
        },
        {
          "@": 11
        },
        {
          "@": 12
        },
        {
          "@": 13
        },
        {
          "@": 14
        },
        {
          "@": 15
        },
        {
          "@": 16
        },
        {
          "@": 17
        },
        {
          "@": 18
        },
        {
          "@": 19
        },
        {
          "@": 20
        },
        {
          "@": 21
        },
        {
          "@": 22
        },
        {
          "@": 23
        },
        {
          "@": 24
        },
        {
          "@": 25
        },
        {
          "@": 26
        },
        {
          "@": 27
        },
        {
          "@": 28
        },
        {
          "@": 29
        },
        {
          "@": 30
        },
        {
          "@": 31
        },
        {
          "@": 32
        },
        {
          "@": 33
        },
        {
          "@": 34
        }
      ],
      "ignore": [
        "WS_INLINE",
        "SL_COMMENT",
        "DL_COMMENT"
      ],
      "g_regex_flags": 0,
      "use_bytes": false,
      "lexer_type": "contextual",
      "__type__": "LexerConf"
    },
    "parser_conf": {
      "rules": [
        {
          "@": 35
        },
        {
          "@": 36
        },
        {
          "@": 37
        },
        {
          "@": 38
        },
        {
          "@": 39
        },
        {
          "@": 40
        },
        {
          "@": 41
        },
        {
          "@": 42
        },
        {
          "@": 43
        },
        {
          "@": 44
        },
        {
          "@": 45
        },
        {
          "@": 46
        },
        {
          "@": 47
        },
        {
          "@": 48
        },
        {
          "@": 49
        },
        {
          "@": 50
        },
        {
          "@": 51
        },
        {
          "@": 52
        },
        {
          "@": 53
        },
        {
          "@": 54
        },
        {
          "@": 55
        },
        {
          "@": 56
        },
        {
          "@": 57
        },
        {
          "@": 58
        },
        {
          "@": 59
        },
        {
          "@": 60
        },
        {
          "@": 61
        },
        {
          "@": 62
        },
        {
          "@": 63
        },
        {
          "@": 64
        },
        {
          "@": 65
        },
        {
          "@": 66
        },
        {
          "@": 67
        },
        {
          "@": 68
        },
        {
          "@": 69
        },
        {
          "@": 70
        },
        {
          "@": 71
        },
        {
          "@": 72
        },
        {
          "@": 73
        },
        {
          "@": 74
        },
        {
          "@": 75
        },
        {
          "@": 76
        },
        {
          "@": 77
        },
        {
          "@": 78
        },
        {
          "@": 79
        },
        {
          "@": 80
        },
        {
          "@": 81
        },
        {
          "@": 82
        },
        {
          "@": 83
        },
        {
          "@": 84
        },
        {
          "@": 85
        },
        {
          "@": 86
        },
        {
          "@": 87
        },
        {
          "@": 88
        },
        {
          "@": 89
        },
        {
          "@": 90
        },
        {
          "@": 91
        },
        {
          "@": 92
        },
        {
          "@": 93
        },
        {
          "@": 94
        },
        {
          "@": 95
        },
        {
          "@": 96
        },
        {
          "@": 97
        },
        {
          "@": 98
        },
        {
          "@": 99
        },
        {
          "@": 100
        },
        {
          "@": 101
        },
        {
          "@": 102
        },
        {
          "@": 103
        },
        {
          "@": 104
        },
        {
          "@": 105
        },
        {
          "@": 106
        },
        {
          "@": 107
        },
        {
          "@": 108
        },
        {
          "@": 109
        },
        {
          "@": 110
        },
        {
          "@": 111
        },
        {
          "@": 112
        },
        {
          "@": 113
        },
        {
          "@": 114
        },
        {
          "@": 115
        },
        {
          "@": 116
        },
        {
          "@": 117
        },
        {
          "@": 118
        },
        {
          "@": 119
        },
        {
          "@": 120
        },
        {
          "@": 121
        },
        {
          "@": 122
        },
        {
          "@": 123
        },
        {
          "@": 124
        },
        {
          "@": 125
        },
        {
          "@": 126
        },
        {
          "@": 127
        },
        {
          "@": 128
        }
      ],
      "start": [
        "start"
      ],
      "parser_type": "lalr",
      "__type__": "ParserConf"
    },
    "parser": {
      "tokens": {
        "0": "_NL",
        "1": "_INDENT",
        "2": "_DEDENT",
        "3": "GROUP",
        "4": "SET",
        "5": "QUANTOR_UNIVERSAL",
        "6": "OPERATOR_UNARY",
        "7": "OPERATOR_N_ARY",
        "8": "OPERATOR_BINARY",
        "9": "QUANTOR_EXISTENTIAL",
        "10": "VARIABLE",
        "11": "SEQUENCE",
        "12": "$END",
        "13": "__start_star_1",
        "14": "AT",
        "15": "label",
        "16": "layer",
        "17": "args__q_one",
        "18": "operator__n_ary",
        "19": "quantor__universal",
        "20": "operator__unary",
        "21": "operator__binary",
        "22": "statement__",
        "23": "quantor__existential",
        "24": "members",
        "25": "STRING",
        "26": "__attributes_plus_5",
        "27": "attribute__",
        "28": "args__q_two",
        "29": "NUMBER_EXPRESSION",
        "30": "comparison_type__",
        "31": "REGEX",
        "32": "STRING_LITERAL",
        "33": "__statement___plus_2",
        "34": "entity",
        "35": "constraints",
        "36": "functions__",
        "37": "ENUM_FUNCTIONS",
        "38": "__functions_plus_7",
        "39": "ATTRIBUTE",
        "40": "query",
        "41": "results",
        "42": "FUNCTIONS",
        "43": "functions",
        "44": "args__any",
        "45": "attribute",
        "46": "__statement___plus_3",
        "47": "RANGE",
        "48": "range__",
        "49": "attributes",
        "50": "ATTRIBUTES",
        "51": "window",
        "52": "WINDOW",
        "53": "ENTITIES",
        "54": "args__one",
        "55": "__entities_plus_4",
        "56": "entity_ref__",
        "57": "__start_plus_0",
        "58": "OPERATOR",
        "59": "FILTER",
        "60": "entities",
        "61": "RESULTS_ARROW",
        "62": "start",
        "63": "REPETITION",
        "64": "context",
        "65": "CONTEXT",
        "66": "__filter_plus_6",
        "67": "filter__",
        "68": "COLLOCATION",
        "69": "ANALYSIS",
        "70": "results_type__",
        "71": "PLAIN",
        "72": "filter",
        "73": "part_of",
        "74": "args__two",
        "75": "repetition",
        "76": "operator",
        "77": "CENTER",
        "78": "space",
        "79": "SPACE",
        "80": "center"
      },
      "states": {
        "0": {
          "0": [
            0,
            148
          ]
        },
        "1": {
          "1": [
            0,
            78
          ],
          "2": [
            1,
            {
              "@": 56
            }
          ],
          "3": [
            1,
            {
              "@": 56
            }
          ],
          "4": [
            1,
            {
              "@": 56
            }
          ],
          "5": [
            1,
            {
              "@": 56
            }
          ],
          "6": [
            1,
            {
              "@": 56
            }
          ],
          "7": [
            1,
            {
              "@": 56
            }
          ],
          "8": [
            1,
            {
              "@": 56
            }
          ],
          "9": [
            1,
            {
              "@": 56
            }
          ],
          "10": [
            1,
            {
              "@": 56
            }
          ],
          "11": [
            1,
            {
              "@": 56
            }
          ],
          "12": [
            1,
            {
              "@": 56
            }
          ]
        },
        "2": {
          "13": [
            0,
            71
          ],
          "0": [
            0,
            83
          ],
          "10": [
            1,
            {
              "@": 106
            }
          ],
          "2": [
            1,
            {
              "@": 106
            }
          ]
        },
        "3": {
          "10": [
            1,
            {
              "@": 103
            }
          ],
          "0": [
            1,
            {
              "@": 103
            }
          ]
        },
        "4": {
          "0": [
            1,
            {
              "@": 98
            }
          ]
        },
        "5": {
          "14": [
            0,
            173
          ],
          "10": [
            0,
            138
          ],
          "15": [
            0,
            230
          ],
          "0": [
            0,
            142
          ]
        },
        "6": {
          "2": [
            1,
            {
              "@": 55
            }
          ],
          "3": [
            1,
            {
              "@": 55
            }
          ],
          "4": [
            1,
            {
              "@": 55
            }
          ],
          "5": [
            1,
            {
              "@": 55
            }
          ],
          "6": [
            1,
            {
              "@": 55
            }
          ],
          "7": [
            1,
            {
              "@": 55
            }
          ],
          "8": [
            1,
            {
              "@": 55
            }
          ],
          "9": [
            1,
            {
              "@": 55
            }
          ],
          "10": [
            1,
            {
              "@": 55
            }
          ],
          "11": [
            1,
            {
              "@": 55
            }
          ],
          "12": [
            1,
            {
              "@": 55
            }
          ]
        },
        "7": {
          "10": [
            1,
            {
              "@": 102
            }
          ],
          "14": [
            1,
            {
              "@": 102
            }
          ],
          "0": [
            1,
            {
              "@": 102
            }
          ]
        },
        "8": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "17": [
            0,
            218
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            18
          ],
          "23": [
            0,
            72
          ]
        },
        "9": {
          "1": [
            0,
            139
          ]
        },
        "10": {
          "0": [
            0,
            60
          ]
        },
        "11": {
          "2": [
            1,
            {
              "@": 41
            }
          ],
          "3": [
            1,
            {
              "@": 41
            }
          ],
          "4": [
            1,
            {
              "@": 41
            }
          ],
          "5": [
            1,
            {
              "@": 41
            }
          ],
          "6": [
            1,
            {
              "@": 41
            }
          ],
          "7": [
            1,
            {
              "@": 41
            }
          ],
          "8": [
            1,
            {
              "@": 41
            }
          ],
          "9": [
            1,
            {
              "@": 41
            }
          ],
          "10": [
            1,
            {
              "@": 41
            }
          ],
          "11": [
            1,
            {
              "@": 41
            }
          ],
          "12": [
            1,
            {
              "@": 41
            }
          ]
        },
        "12": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "24": [
            0,
            208
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "2": [
            0,
            120
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "13": {
          "2": [
            1,
            {
              "@": 43
            }
          ],
          "3": [
            1,
            {
              "@": 43
            }
          ],
          "4": [
            1,
            {
              "@": 43
            }
          ],
          "5": [
            1,
            {
              "@": 43
            }
          ],
          "6": [
            1,
            {
              "@": 43
            }
          ],
          "7": [
            1,
            {
              "@": 43
            }
          ],
          "8": [
            1,
            {
              "@": 43
            }
          ],
          "9": [
            1,
            {
              "@": 43
            }
          ],
          "10": [
            1,
            {
              "@": 43
            }
          ],
          "11": [
            1,
            {
              "@": 43
            }
          ],
          "12": [
            1,
            {
              "@": 43
            }
          ]
        },
        "14": {
          "1": [
            0,
            25
          ]
        },
        "15": {
          "2": [
            1,
            {
              "@": 124
            }
          ],
          "25": [
            1,
            {
              "@": 124
            }
          ]
        },
        "16": {
          "26": [
            0,
            169
          ],
          "25": [
            0,
            164
          ],
          "27": [
            0,
            216
          ]
        },
        "17": {
          "0": [
            0,
            191
          ],
          "2": [
            1,
            {
              "@": 84
            }
          ]
        },
        "18": {
          "2": [
            1,
            {
              "@": 69
            }
          ]
        },
        "19": {
          "5": [
            1,
            {
              "@": 77
            }
          ],
          "10": [
            1,
            {
              "@": 77
            }
          ],
          "8": [
            1,
            {
              "@": 77
            }
          ],
          "11": [
            1,
            {
              "@": 77
            }
          ],
          "3": [
            1,
            {
              "@": 77
            }
          ],
          "4": [
            1,
            {
              "@": 77
            }
          ],
          "6": [
            1,
            {
              "@": 77
            }
          ],
          "9": [
            1,
            {
              "@": 77
            }
          ],
          "7": [
            1,
            {
              "@": 77
            }
          ],
          "12": [
            1,
            {
              "@": 77
            }
          ]
        },
        "20": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "28": [
            0,
            34
          ],
          "11": [
            0,
            198
          ],
          "10": [
            0,
            7
          ],
          "22": [
            0,
            52
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ]
        },
        "21": {
          "29": [
            0,
            150
          ],
          "10": [
            0,
            206
          ],
          "30": [
            0,
            211
          ],
          "31": [
            0,
            193
          ],
          "32": [
            0,
            4
          ]
        },
        "22": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "33": [
            0,
            95
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "35": [
            0,
            154
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ]
        },
        "23": {
          "1": [
            0,
            158
          ]
        },
        "24": {
          "2": [
            0,
            160
          ]
        },
        "25": {
          "36": [
            0,
            133
          ],
          "37": [
            0,
            153
          ],
          "38": [
            0,
            103
          ]
        },
        "26": {
          "3": [
            1,
            {
              "@": 74
            }
          ],
          "4": [
            1,
            {
              "@": 74
            }
          ],
          "5": [
            1,
            {
              "@": 74
            }
          ],
          "6": [
            1,
            {
              "@": 74
            }
          ],
          "7": [
            1,
            {
              "@": 74
            }
          ],
          "8": [
            1,
            {
              "@": 74
            }
          ],
          "9": [
            1,
            {
              "@": 74
            }
          ],
          "10": [
            1,
            {
              "@": 74
            }
          ],
          "11": [
            1,
            {
              "@": 74
            }
          ],
          "12": [
            1,
            {
              "@": 74
            }
          ]
        },
        "27": {
          "2": [
            1,
            {
              "@": 42
            }
          ],
          "3": [
            1,
            {
              "@": 42
            }
          ],
          "4": [
            1,
            {
              "@": 42
            }
          ],
          "5": [
            1,
            {
              "@": 42
            }
          ],
          "6": [
            1,
            {
              "@": 42
            }
          ],
          "7": [
            1,
            {
              "@": 42
            }
          ],
          "8": [
            1,
            {
              "@": 42
            }
          ],
          "9": [
            1,
            {
              "@": 42
            }
          ],
          "10": [
            1,
            {
              "@": 42
            }
          ],
          "11": [
            1,
            {
              "@": 42
            }
          ],
          "12": [
            1,
            {
              "@": 42
            }
          ]
        },
        "28": {
          "1": [
            0,
            152
          ]
        },
        "29": {
          "39": [
            1,
            {
              "@": 93
            }
          ]
        },
        "30": {
          "0": [
            1,
            {
              "@": 68
            }
          ]
        },
        "31": {
          "16": [
            0,
            5
          ],
          "10": [
            0,
            125
          ],
          "40": [
            0,
            200
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "41": [
            0,
            140
          ],
          "21": [
            0,
            96
          ],
          "15": [
            0,
            162
          ],
          "22": [
            0,
            221
          ],
          "12": [
            1,
            {
              "@": 37
            }
          ]
        },
        "32": {
          "42": [
            0,
            151
          ],
          "43": [
            0,
            24
          ]
        },
        "33": {
          "0": [
            0,
            9
          ]
        },
        "34": {
          "2": [
            0,
            117
          ]
        },
        "35": {
          "2": [
            0,
            136
          ]
        },
        "36": {
          "5": [
            1,
            {
              "@": 78
            }
          ],
          "10": [
            1,
            {
              "@": 78
            }
          ],
          "8": [
            1,
            {
              "@": 78
            }
          ],
          "11": [
            1,
            {
              "@": 78
            }
          ],
          "3": [
            1,
            {
              "@": 78
            }
          ],
          "4": [
            1,
            {
              "@": 78
            }
          ],
          "6": [
            1,
            {
              "@": 78
            }
          ],
          "9": [
            1,
            {
              "@": 78
            }
          ],
          "7": [
            1,
            {
              "@": 78
            }
          ],
          "12": [
            1,
            {
              "@": 78
            }
          ]
        },
        "37": {
          "0": [
            0,
            101
          ]
        },
        "38": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "44": [
            0,
            47
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ],
          "35": [
            0,
            59
          ]
        },
        "39": {
          "45": [
            0,
            144
          ],
          "39": [
            0,
            91
          ]
        },
        "40": {
          "0": [
            1,
            {
              "@": 65
            }
          ]
        },
        "41": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "46": [
            0,
            168
          ],
          "24": [
            0,
            172
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "42": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "2": [
            0,
            187
          ],
          "23": [
            0,
            72
          ],
          "24": [
            0,
            208
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "43": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "46": [
            0,
            201
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "24": [
            0,
            172
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "44": {
          "0": [
            0,
            45
          ]
        },
        "45": {
          "1": [
            0,
            196
          ]
        },
        "46": {
          "13": [
            0,
            17
          ],
          "0": [
            0,
            83
          ],
          "2": [
            1,
            {
              "@": 85
            }
          ]
        },
        "47": {
          "2": [
            0,
            174
          ]
        },
        "48": {
          "5": [
            1,
            {
              "@": 75
            }
          ],
          "10": [
            1,
            {
              "@": 75
            }
          ],
          "8": [
            1,
            {
              "@": 75
            }
          ],
          "11": [
            1,
            {
              "@": 75
            }
          ],
          "3": [
            1,
            {
              "@": 75
            }
          ],
          "4": [
            1,
            {
              "@": 75
            }
          ],
          "6": [
            1,
            {
              "@": 75
            }
          ],
          "9": [
            1,
            {
              "@": 75
            }
          ],
          "7": [
            1,
            {
              "@": 75
            }
          ],
          "12": [
            1,
            {
              "@": 75
            }
          ]
        },
        "49": {
          "0": [
            0,
            23
          ]
        },
        "50": {
          "0": [
            1,
            {
              "@": 66
            }
          ]
        },
        "51": {
          "0": [
            0,
            181
          ],
          "10": [
            0,
            138
          ],
          "15": [
            0,
            0
          ]
        },
        "52": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "22": [
            0,
            195
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ]
        },
        "53": {
          "2": [
            1,
            {
              "@": 40
            }
          ],
          "3": [
            1,
            {
              "@": 40
            }
          ],
          "4": [
            1,
            {
              "@": 40
            }
          ],
          "5": [
            1,
            {
              "@": 40
            }
          ],
          "6": [
            1,
            {
              "@": 40
            }
          ],
          "7": [
            1,
            {
              "@": 40
            }
          ],
          "8": [
            1,
            {
              "@": 40
            }
          ],
          "9": [
            1,
            {
              "@": 40
            }
          ],
          "10": [
            1,
            {
              "@": 40
            }
          ],
          "11": [
            1,
            {
              "@": 40
            }
          ],
          "12": [
            1,
            {
              "@": 40
            }
          ]
        },
        "54": {
          "2": [
            0,
            209
          ]
        },
        "55": {
          "47": [
            0,
            127
          ],
          "48": [
            0,
            105
          ]
        },
        "56": {
          "49": [
            0,
            166
          ],
          "50": [
            0,
            203
          ]
        },
        "57": {
          "2": [
            0,
            70
          ]
        },
        "58": {
          "1": [
            0,
            87
          ]
        },
        "59": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "33": [
            0,
            90
          ],
          "35": [
            0,
            154
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ]
        },
        "60": {
          "1": [
            0,
            56
          ]
        },
        "61": {
          "0": [
            1,
            {
              "@": 64
            }
          ]
        },
        "62": {
          "3": [
            1,
            {
              "@": 118
            }
          ],
          "4": [
            1,
            {
              "@": 118
            }
          ],
          "5": [
            1,
            {
              "@": 118
            }
          ],
          "6": [
            1,
            {
              "@": 118
            }
          ],
          "7": [
            1,
            {
              "@": 118
            }
          ],
          "8": [
            1,
            {
              "@": 118
            }
          ],
          "9": [
            1,
            {
              "@": 118
            }
          ],
          "2": [
            1,
            {
              "@": 118
            }
          ],
          "10": [
            1,
            {
              "@": 118
            }
          ],
          "11": [
            1,
            {
              "@": 118
            }
          ]
        },
        "63": {
          "2": [
            1,
            {
              "@": 94
            }
          ]
        },
        "64": {
          "0": [
            0,
            89
          ],
          "10": [
            0,
            138
          ],
          "15": [
            0,
            33
          ]
        },
        "65": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "24": [
            0,
            208
          ],
          "2": [
            0,
            146
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "66": {
          "1": [
            0,
            179
          ]
        },
        "67": {
          "2": [
            0,
            19
          ]
        },
        "68": {
          "0": [
            0,
            184
          ]
        },
        "69": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "33": [
            0,
            80
          ],
          "35": [
            0,
            154
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ]
        },
        "70": {
          "2": [
            1,
            {
              "@": 50
            }
          ],
          "3": [
            1,
            {
              "@": 50
            }
          ],
          "4": [
            1,
            {
              "@": 50
            }
          ],
          "5": [
            1,
            {
              "@": 50
            }
          ],
          "6": [
            1,
            {
              "@": 50
            }
          ],
          "7": [
            1,
            {
              "@": 50
            }
          ],
          "8": [
            1,
            {
              "@": 50
            }
          ],
          "9": [
            1,
            {
              "@": 50
            }
          ],
          "10": [
            1,
            {
              "@": 50
            }
          ],
          "11": [
            1,
            {
              "@": 50
            }
          ],
          "12": [
            1,
            {
              "@": 50
            }
          ]
        },
        "71": {
          "0": [
            0,
            191
          ],
          "10": [
            1,
            {
              "@": 105
            }
          ],
          "2": [
            1,
            {
              "@": 105
            }
          ]
        },
        "72": {
          "0": [
            0,
            114
          ]
        },
        "73": {
          "51": [
            0,
            39
          ],
          "52": [
            0,
            86
          ]
        },
        "74": {
          "1": [
            0,
            16
          ]
        },
        "75": {
          "1": [
            0,
            43
          ]
        },
        "76": {
          "1": [
            0,
            210
          ]
        },
        "77": {
          "0": [
            0,
            15
          ]
        },
        "78": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "33": [
            0,
            223
          ],
          "35": [
            0,
            154
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ]
        },
        "79": {
          "0": [
            0,
            229
          ]
        },
        "80": {
          "16": [
            0,
            5
          ],
          "2": [
            0,
            219
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ],
          "35": [
            0,
            62
          ]
        },
        "81": {
          "0": [
            1,
            {
              "@": 109
            }
          ]
        },
        "82": {
          "39": [
            1,
            {
              "@": 92
            }
          ]
        },
        "83": {
          "2": [
            1,
            {
              "@": 115
            }
          ],
          "10": [
            1,
            {
              "@": 115
            }
          ],
          "0": [
            1,
            {
              "@": 115
            }
          ],
          "53": [
            1,
            {
              "@": 115
            }
          ],
          "3": [
            1,
            {
              "@": 115
            }
          ],
          "4": [
            1,
            {
              "@": 115
            }
          ],
          "5": [
            1,
            {
              "@": 115
            }
          ],
          "6": [
            1,
            {
              "@": 115
            }
          ],
          "7": [
            1,
            {
              "@": 115
            }
          ],
          "8": [
            1,
            {
              "@": 115
            }
          ],
          "9": [
            1,
            {
              "@": 115
            }
          ],
          "11": [
            1,
            {
              "@": 115
            }
          ],
          "12": [
            1,
            {
              "@": 115
            }
          ]
        },
        "84": {
          "0": [
            0,
            191
          ],
          "53": [
            1,
            {
              "@": 80
            }
          ]
        },
        "85": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "54": [
            0,
            57
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ],
          "35": [
            0,
            121
          ]
        },
        "86": {
          "0": [
            0,
            131
          ]
        },
        "87": {
          "55": [
            0,
            180
          ],
          "56": [
            0,
            135
          ],
          "10": [
            0,
            2
          ]
        },
        "88": {
          "3": [
            1,
            {
              "@": 111
            }
          ],
          "4": [
            1,
            {
              "@": 111
            }
          ],
          "5": [
            1,
            {
              "@": 111
            }
          ],
          "6": [
            1,
            {
              "@": 111
            }
          ],
          "7": [
            1,
            {
              "@": 111
            }
          ],
          "8": [
            1,
            {
              "@": 111
            }
          ],
          "9": [
            1,
            {
              "@": 111
            }
          ],
          "10": [
            1,
            {
              "@": 111
            }
          ],
          "11": [
            1,
            {
              "@": 111
            }
          ],
          "12": [
            1,
            {
              "@": 111
            }
          ]
        },
        "89": {
          "1": [
            0,
            228
          ]
        },
        "90": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ],
          "35": [
            0,
            62
          ],
          "2": [
            1,
            {
              "@": 73
            }
          ]
        },
        "91": {
          "0": [
            0,
            66
          ]
        },
        "92": {
          "0": [
            0,
            58
          ]
        },
        "93": {
          "16": [
            0,
            5
          ],
          "10": [
            0,
            125
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "57": [
            0,
            202
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "0": [
            0,
            191
          ],
          "40": [
            0,
            88
          ],
          "21": [
            0,
            96
          ],
          "41": [
            0,
            122
          ],
          "15": [
            0,
            162
          ],
          "22": [
            0,
            221
          ],
          "12": [
            1,
            {
              "@": 36
            }
          ]
        },
        "94": {
          "0": [
            0,
            186
          ]
        },
        "95": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ],
          "2": [
            0,
            176
          ],
          "35": [
            0,
            62
          ]
        },
        "96": {
          "0": [
            0,
            104
          ]
        },
        "97": {
          "1": [
            0,
            149
          ]
        },
        "98": {
          "2": [
            0,
            48
          ]
        },
        "99": {
          "42": [
            1,
            {
              "@": 89
            }
          ]
        },
        "100": {
          "1": [
            0,
            205
          ]
        },
        "101": {
          "1": [
            0,
            194
          ]
        },
        "102": {
          "0": [
            1,
            {
              "@": 67
            }
          ]
        },
        "103": {
          "37": [
            0,
            153
          ],
          "36": [
            0,
            183
          ],
          "2": [
            0,
            177
          ]
        },
        "104": {
          "1": [
            0,
            190
          ]
        },
        "105": {
          "2": [
            0,
            82
          ]
        },
        "106": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "10": [
            0,
            111
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "35": [
            0,
            112
          ],
          "23": [
            0,
            72
          ]
        },
        "107": {
          "0": [
            0,
            113
          ]
        },
        "108": {
          "0": [
            0,
            147
          ]
        },
        "109": {
          "0": [
            0,
            76
          ]
        },
        "110": {
          "1": [
            0,
            69
          ],
          "2": [
            1,
            {
              "@": 58
            }
          ],
          "3": [
            1,
            {
              "@": 58
            }
          ],
          "4": [
            1,
            {
              "@": 58
            }
          ],
          "5": [
            1,
            {
              "@": 58
            }
          ],
          "6": [
            1,
            {
              "@": 58
            }
          ],
          "7": [
            1,
            {
              "@": 58
            }
          ],
          "8": [
            1,
            {
              "@": 58
            }
          ],
          "9": [
            1,
            {
              "@": 58
            }
          ],
          "10": [
            1,
            {
              "@": 58
            }
          ],
          "11": [
            1,
            {
              "@": 58
            }
          ],
          "12": [
            1,
            {
              "@": 58
            }
          ]
        },
        "111": {
          "10": [
            1,
            {
              "@": 102
            }
          ],
          "14": [
            1,
            {
              "@": 102
            }
          ],
          "0": [
            1,
            {
              "@": 102
            }
          ],
          "58": [
            1,
            {
              "@": 95
            }
          ]
        },
        "112": {
          "2": [
            1,
            {
              "@": 72
            }
          ]
        },
        "113": {
          "2": [
            1,
            {
              "@": 125
            }
          ],
          "25": [
            1,
            {
              "@": 125
            }
          ]
        },
        "114": {
          "1": [
            0,
            8
          ]
        },
        "115": {
          "59": [
            1,
            {
              "@": 88
            }
          ],
          "42": [
            1,
            {
              "@": 88
            }
          ]
        },
        "116": {
          "0": [
            0,
            188
          ]
        },
        "117": {
          "2": [
            1,
            {
              "@": 48
            }
          ],
          "3": [
            1,
            {
              "@": 48
            }
          ],
          "4": [
            1,
            {
              "@": 48
            }
          ],
          "5": [
            1,
            {
              "@": 48
            }
          ],
          "6": [
            1,
            {
              "@": 48
            }
          ],
          "7": [
            1,
            {
              "@": 48
            }
          ],
          "8": [
            1,
            {
              "@": 48
            }
          ],
          "9": [
            1,
            {
              "@": 48
            }
          ],
          "10": [
            1,
            {
              "@": 48
            }
          ],
          "11": [
            1,
            {
              "@": 48
            }
          ],
          "12": [
            1,
            {
              "@": 48
            }
          ]
        },
        "118": {
          "13": [
            0,
            130
          ],
          "0": [
            0,
            83
          ],
          "53": [
            1,
            {
              "@": 83
            }
          ]
        },
        "119": {
          "0": [
            0,
            75
          ]
        },
        "120": {
          "2": [
            1,
            {
              "@": 46
            }
          ],
          "3": [
            1,
            {
              "@": 46
            }
          ],
          "4": [
            1,
            {
              "@": 46
            }
          ],
          "5": [
            1,
            {
              "@": 46
            }
          ],
          "6": [
            1,
            {
              "@": 46
            }
          ],
          "7": [
            1,
            {
              "@": 46
            }
          ],
          "8": [
            1,
            {
              "@": 46
            }
          ],
          "9": [
            1,
            {
              "@": 46
            }
          ],
          "10": [
            1,
            {
              "@": 46
            }
          ],
          "11": [
            1,
            {
              "@": 46
            }
          ],
          "12": [
            1,
            {
              "@": 46
            }
          ]
        },
        "121": {
          "2": [
            1,
            {
              "@": 71
            }
          ]
        },
        "122": {
          "3": [
            1,
            {
              "@": 112
            }
          ],
          "4": [
            1,
            {
              "@": 112
            }
          ],
          "5": [
            1,
            {
              "@": 112
            }
          ],
          "6": [
            1,
            {
              "@": 112
            }
          ],
          "7": [
            1,
            {
              "@": 112
            }
          ],
          "8": [
            1,
            {
              "@": 112
            }
          ],
          "9": [
            1,
            {
              "@": 112
            }
          ],
          "10": [
            1,
            {
              "@": 112
            }
          ],
          "11": [
            1,
            {
              "@": 112
            }
          ],
          "12": [
            1,
            {
              "@": 112
            }
          ]
        },
        "123": {
          "53": [
            0,
            44
          ],
          "60": [
            0,
            98
          ]
        },
        "124": {
          "0": [
            0,
            191
          ],
          "2": [
            0,
            46
          ]
        },
        "125": {
          "10": [
            1,
            {
              "@": 102
            }
          ],
          "14": [
            1,
            {
              "@": 102
            }
          ],
          "0": [
            1,
            {
              "@": 102
            }
          ],
          "61": [
            1,
            {
              "@": 101
            }
          ]
        },
        "126": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "2": [
            0,
            27
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "24": [
            0,
            208
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "127": {
          "2": [
            1,
            {
              "@": 110
            }
          ]
        },
        "128": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "24": [
            0,
            208
          ],
          "10": [
            0,
            7
          ],
          "2": [
            0,
            11
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "129": {
          "13": [
            0,
            175
          ],
          "0": [
            0,
            83
          ],
          "2": [
            0,
            118
          ]
        },
        "130": {
          "0": [
            0,
            191
          ],
          "53": [
            1,
            {
              "@": 82
            }
          ]
        },
        "131": {
          "1": [
            0,
            55
          ]
        },
        "132": {
          "0": [
            0,
            165
          ]
        },
        "133": {
          "2": [
            1,
            {
              "@": 127
            }
          ],
          "37": [
            1,
            {
              "@": 127
            }
          ]
        },
        "134": {
          "1": [
            0,
            189
          ]
        },
        "135": {
          "10": [
            1,
            {
              "@": 121
            }
          ],
          "2": [
            1,
            {
              "@": 121
            }
          ],
          "0": [
            1,
            {
              "@": 121
            }
          ]
        },
        "136": {
          "5": [
            1,
            {
              "@": 79
            }
          ],
          "10": [
            1,
            {
              "@": 79
            }
          ],
          "8": [
            1,
            {
              "@": 79
            }
          ],
          "11": [
            1,
            {
              "@": 79
            }
          ],
          "3": [
            1,
            {
              "@": 79
            }
          ],
          "4": [
            1,
            {
              "@": 79
            }
          ],
          "6": [
            1,
            {
              "@": 79
            }
          ],
          "9": [
            1,
            {
              "@": 79
            }
          ],
          "7": [
            1,
            {
              "@": 79
            }
          ],
          "12": [
            1,
            {
              "@": 79
            }
          ]
        },
        "137": {
          "16": [
            0,
            5
          ],
          "10": [
            0,
            125
          ],
          "8": [
            0,
            102
          ],
          "62": [
            0,
            185
          ],
          "13": [
            0,
            93
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "57": [
            0,
            31
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "0": [
            0,
            83
          ],
          "40": [
            0,
            88
          ],
          "21": [
            0,
            96
          ],
          "41": [
            0,
            122
          ],
          "15": [
            0,
            162
          ],
          "22": [
            0,
            221
          ],
          "12": [
            1,
            {
              "@": 38
            }
          ]
        },
        "138": {
          "0": [
            1,
            {
              "@": 101
            }
          ],
          "2": [
            1,
            {
              "@": 101
            }
          ],
          "63": [
            1,
            {
              "@": 101
            }
          ]
        },
        "139": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "46": [
            0,
            65
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "24": [
            0,
            172
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "140": {
          "3": [
            1,
            {
              "@": 114
            }
          ],
          "4": [
            1,
            {
              "@": 114
            }
          ],
          "5": [
            1,
            {
              "@": 114
            }
          ],
          "6": [
            1,
            {
              "@": 114
            }
          ],
          "7": [
            1,
            {
              "@": 114
            }
          ],
          "8": [
            1,
            {
              "@": 114
            }
          ],
          "9": [
            1,
            {
              "@": 114
            }
          ],
          "10": [
            1,
            {
              "@": 114
            }
          ],
          "11": [
            1,
            {
              "@": 114
            }
          ],
          "12": [
            1,
            {
              "@": 114
            }
          ]
        },
        "141": {
          "10": [
            1,
            {
              "@": 122
            }
          ],
          "2": [
            1,
            {
              "@": 122
            }
          ],
          "0": [
            1,
            {
              "@": 122
            }
          ]
        },
        "142": {
          "1": [
            0,
            224
          ],
          "2": [
            1,
            {
              "@": 60
            }
          ],
          "3": [
            1,
            {
              "@": 60
            }
          ],
          "4": [
            1,
            {
              "@": 60
            }
          ],
          "5": [
            1,
            {
              "@": 60
            }
          ],
          "6": [
            1,
            {
              "@": 60
            }
          ],
          "7": [
            1,
            {
              "@": 60
            }
          ],
          "8": [
            1,
            {
              "@": 60
            }
          ],
          "9": [
            1,
            {
              "@": 60
            }
          ],
          "10": [
            1,
            {
              "@": 60
            }
          ],
          "11": [
            1,
            {
              "@": 60
            }
          ],
          "12": [
            1,
            {
              "@": 60
            }
          ]
        },
        "143": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "46": [
            0,
            12
          ],
          "24": [
            0,
            172
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "144": {
          "2": [
            0,
            36
          ]
        },
        "145": {
          "2": [
            1,
            {
              "@": 123
            }
          ],
          "25": [
            1,
            {
              "@": 123
            }
          ]
        },
        "146": {
          "2": [
            1,
            {
              "@": 44
            }
          ],
          "3": [
            1,
            {
              "@": 44
            }
          ],
          "4": [
            1,
            {
              "@": 44
            }
          ],
          "5": [
            1,
            {
              "@": 44
            }
          ],
          "6": [
            1,
            {
              "@": 44
            }
          ],
          "7": [
            1,
            {
              "@": 44
            }
          ],
          "8": [
            1,
            {
              "@": 44
            }
          ],
          "9": [
            1,
            {
              "@": 44
            }
          ],
          "10": [
            1,
            {
              "@": 44
            }
          ],
          "11": [
            1,
            {
              "@": 44
            }
          ],
          "12": [
            1,
            {
              "@": 44
            }
          ]
        },
        "147": {
          "1": [
            0,
            85
          ]
        },
        "148": {
          "1": [
            0,
            143
          ]
        },
        "149": {
          "64": [
            0,
            123
          ],
          "65": [
            0,
            155
          ]
        },
        "150": {
          "0": [
            1,
            {
              "@": 97
            }
          ]
        },
        "151": {
          "0": [
            0,
            14
          ]
        },
        "152": {
          "15": [
            0,
            129
          ],
          "10": [
            0,
            138
          ]
        },
        "153": {
          "2": [
            1,
            {
              "@": 107
            }
          ],
          "37": [
            1,
            {
              "@": 107
            }
          ]
        },
        "154": {
          "3": [
            1,
            {
              "@": 117
            }
          ],
          "4": [
            1,
            {
              "@": 117
            }
          ],
          "5": [
            1,
            {
              "@": 117
            }
          ],
          "6": [
            1,
            {
              "@": 117
            }
          ],
          "7": [
            1,
            {
              "@": 117
            }
          ],
          "8": [
            1,
            {
              "@": 117
            }
          ],
          "9": [
            1,
            {
              "@": 117
            }
          ],
          "2": [
            1,
            {
              "@": 117
            }
          ],
          "10": [
            1,
            {
              "@": 117
            }
          ],
          "11": [
            1,
            {
              "@": 117
            }
          ]
        },
        "155": {
          "0": [
            0,
            28
          ]
        },
        "156": {
          "0": [
            0,
            191
          ],
          "2": [
            1,
            {
              "@": 86
            }
          ]
        },
        "157": {
          "2": [
            1,
            {
              "@": 47
            }
          ],
          "3": [
            1,
            {
              "@": 47
            }
          ],
          "4": [
            1,
            {
              "@": 47
            }
          ],
          "5": [
            1,
            {
              "@": 47
            }
          ],
          "6": [
            1,
            {
              "@": 47
            }
          ],
          "7": [
            1,
            {
              "@": 47
            }
          ],
          "8": [
            1,
            {
              "@": 47
            }
          ],
          "9": [
            1,
            {
              "@": 47
            }
          ],
          "10": [
            1,
            {
              "@": 47
            }
          ],
          "11": [
            1,
            {
              "@": 47
            }
          ],
          "12": [
            1,
            {
              "@": 47
            }
          ]
        },
        "158": {
          "25": [
            0,
            81
          ],
          "66": [
            0,
            226
          ],
          "67": [
            0,
            107
          ]
        },
        "159": {
          "68": [
            0,
            109
          ],
          "69": [
            0,
            10
          ],
          "70": [
            0,
            26
          ],
          "71": [
            0,
            217
          ]
        },
        "160": {
          "5": [
            1,
            {
              "@": 76
            }
          ],
          "10": [
            1,
            {
              "@": 76
            }
          ],
          "8": [
            1,
            {
              "@": 76
            }
          ],
          "11": [
            1,
            {
              "@": 76
            }
          ],
          "3": [
            1,
            {
              "@": 76
            }
          ],
          "4": [
            1,
            {
              "@": 76
            }
          ],
          "6": [
            1,
            {
              "@": 76
            }
          ],
          "9": [
            1,
            {
              "@": 76
            }
          ],
          "7": [
            1,
            {
              "@": 76
            }
          ],
          "12": [
            1,
            {
              "@": 76
            }
          ]
        },
        "161": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "24": [
            0,
            208
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "2": [
            0,
            13
          ],
          "22": [
            0,
            225
          ]
        },
        "162": {
          "61": [
            0,
            159
          ]
        },
        "163": {
          "3": [
            1,
            {
              "@": 63
            }
          ],
          "4": [
            1,
            {
              "@": 63
            }
          ],
          "5": [
            1,
            {
              "@": 63
            }
          ],
          "6": [
            1,
            {
              "@": 63
            }
          ],
          "7": [
            1,
            {
              "@": 63
            }
          ],
          "8": [
            1,
            {
              "@": 63
            }
          ],
          "9": [
            1,
            {
              "@": 63
            }
          ],
          "2": [
            1,
            {
              "@": 63
            }
          ],
          "10": [
            1,
            {
              "@": 63
            }
          ],
          "11": [
            1,
            {
              "@": 63
            }
          ]
        },
        "164": {
          "0": [
            1,
            {
              "@": 108
            }
          ],
          "2": [
            1,
            {
              "@": 108
            }
          ]
        },
        "165": {
          "1": [
            0,
            38
          ]
        },
        "166": {
          "42": [
            0,
            151
          ],
          "59": [
            0,
            49
          ],
          "72": [
            0,
            32
          ],
          "43": [
            0,
            67
          ]
        },
        "167": {
          "2": [
            0,
            63
          ]
        },
        "168": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "24": [
            0,
            208
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "2": [
            0,
            157
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "169": {
          "27": [
            0,
            77
          ],
          "2": [
            0,
            115
          ],
          "25": [
            0,
            164
          ]
        },
        "170": {
          "2": [
            1,
            {
              "@": 49
            }
          ],
          "3": [
            1,
            {
              "@": 49
            }
          ],
          "4": [
            1,
            {
              "@": 49
            }
          ],
          "5": [
            1,
            {
              "@": 49
            }
          ],
          "6": [
            1,
            {
              "@": 49
            }
          ],
          "7": [
            1,
            {
              "@": 49
            }
          ],
          "8": [
            1,
            {
              "@": 49
            }
          ],
          "9": [
            1,
            {
              "@": 49
            }
          ],
          "10": [
            1,
            {
              "@": 49
            }
          ],
          "11": [
            1,
            {
              "@": 49
            }
          ],
          "12": [
            1,
            {
              "@": 49
            }
          ]
        },
        "171": {
          "45": [
            0,
            35
          ],
          "39": [
            0,
            91
          ]
        },
        "172": {
          "3": [
            1,
            {
              "@": 119
            }
          ],
          "4": [
            1,
            {
              "@": 119
            }
          ],
          "5": [
            1,
            {
              "@": 119
            }
          ],
          "6": [
            1,
            {
              "@": 119
            }
          ],
          "7": [
            1,
            {
              "@": 119
            }
          ],
          "8": [
            1,
            {
              "@": 119
            }
          ],
          "2": [
            1,
            {
              "@": 119
            }
          ],
          "9": [
            1,
            {
              "@": 119
            }
          ],
          "10": [
            1,
            {
              "@": 119
            }
          ],
          "11": [
            1,
            {
              "@": 119
            }
          ]
        },
        "173": {
          "73": [
            0,
            192
          ],
          "10": [
            0,
            3
          ]
        },
        "174": {
          "2": [
            1,
            {
              "@": 52
            }
          ],
          "3": [
            1,
            {
              "@": 52
            }
          ],
          "4": [
            1,
            {
              "@": 52
            }
          ],
          "5": [
            1,
            {
              "@": 52
            }
          ],
          "6": [
            1,
            {
              "@": 52
            }
          ],
          "7": [
            1,
            {
              "@": 52
            }
          ],
          "8": [
            1,
            {
              "@": 52
            }
          ],
          "9": [
            1,
            {
              "@": 52
            }
          ],
          "10": [
            1,
            {
              "@": 52
            }
          ],
          "11": [
            1,
            {
              "@": 52
            }
          ],
          "12": [
            1,
            {
              "@": 52
            }
          ]
        },
        "175": {
          "0": [
            0,
            191
          ],
          "2": [
            0,
            227
          ]
        },
        "176": {
          "2": [
            1,
            {
              "@": 53
            }
          ],
          "3": [
            1,
            {
              "@": 53
            }
          ],
          "4": [
            1,
            {
              "@": 53
            }
          ],
          "5": [
            1,
            {
              "@": 53
            }
          ],
          "6": [
            1,
            {
              "@": 53
            }
          ],
          "7": [
            1,
            {
              "@": 53
            }
          ],
          "8": [
            1,
            {
              "@": 53
            }
          ],
          "9": [
            1,
            {
              "@": 53
            }
          ],
          "10": [
            1,
            {
              "@": 53
            }
          ],
          "11": [
            1,
            {
              "@": 53
            }
          ],
          "12": [
            1,
            {
              "@": 53
            }
          ]
        },
        "177": {
          "2": [
            1,
            {
              "@": 90
            }
          ]
        },
        "178": {
          "3": [
            1,
            {
              "@": 62
            }
          ],
          "4": [
            1,
            {
              "@": 62
            }
          ],
          "5": [
            1,
            {
              "@": 62
            }
          ],
          "6": [
            1,
            {
              "@": 62
            }
          ],
          "7": [
            1,
            {
              "@": 62
            }
          ],
          "8": [
            1,
            {
              "@": 62
            }
          ],
          "9": [
            1,
            {
              "@": 62
            }
          ],
          "2": [
            1,
            {
              "@": 62
            }
          ],
          "10": [
            1,
            {
              "@": 62
            }
          ],
          "11": [
            1,
            {
              "@": 62
            }
          ]
        },
        "179": {
          "25": [
            0,
            164
          ],
          "27": [
            0,
            167
          ]
        },
        "180": {
          "56": [
            0,
            141
          ],
          "10": [
            0,
            2
          ],
          "2": [
            0,
            29
          ]
        },
        "181": {
          "1": [
            0,
            41
          ]
        },
        "182": {
          "2": [
            0,
            197
          ]
        },
        "183": {
          "2": [
            1,
            {
              "@": 128
            }
          ],
          "37": [
            1,
            {
              "@": 128
            }
          ]
        },
        "184": {
          "1": [
            0,
            20
          ]
        },
        "185": {},
        "186": {
          "1": [
            0,
            199
          ]
        },
        "187": {
          "2": [
            1,
            {
              "@": 45
            }
          ],
          "3": [
            1,
            {
              "@": 45
            }
          ],
          "4": [
            1,
            {
              "@": 45
            }
          ],
          "5": [
            1,
            {
              "@": 45
            }
          ],
          "6": [
            1,
            {
              "@": 45
            }
          ],
          "7": [
            1,
            {
              "@": 45
            }
          ],
          "8": [
            1,
            {
              "@": 45
            }
          ],
          "9": [
            1,
            {
              "@": 45
            }
          ],
          "10": [
            1,
            {
              "@": 45
            }
          ],
          "11": [
            1,
            {
              "@": 45
            }
          ],
          "12": [
            1,
            {
              "@": 45
            }
          ]
        },
        "188": {
          "1": [
            0,
            22
          ],
          "2": [
            1,
            {
              "@": 54
            }
          ],
          "3": [
            1,
            {
              "@": 54
            }
          ],
          "4": [
            1,
            {
              "@": 54
            }
          ],
          "5": [
            1,
            {
              "@": 54
            }
          ],
          "6": [
            1,
            {
              "@": 54
            }
          ],
          "7": [
            1,
            {
              "@": 54
            }
          ],
          "8": [
            1,
            {
              "@": 54
            }
          ],
          "9": [
            1,
            {
              "@": 54
            }
          ],
          "10": [
            1,
            {
              "@": 54
            }
          ],
          "11": [
            1,
            {
              "@": 54
            }
          ],
          "12": [
            1,
            {
              "@": 54
            }
          ]
        },
        "189": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "46": [
            0,
            161
          ],
          "24": [
            0,
            172
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "190": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "35": [
            0,
            106
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ],
          "74": [
            0,
            54
          ]
        },
        "191": {
          "2": [
            1,
            {
              "@": 116
            }
          ],
          "10": [
            1,
            {
              "@": 116
            }
          ],
          "0": [
            1,
            {
              "@": 116
            }
          ],
          "53": [
            1,
            {
              "@": 116
            }
          ],
          "3": [
            1,
            {
              "@": 116
            }
          ],
          "4": [
            1,
            {
              "@": 116
            }
          ],
          "5": [
            1,
            {
              "@": 116
            }
          ],
          "6": [
            1,
            {
              "@": 116
            }
          ],
          "7": [
            1,
            {
              "@": 116
            }
          ],
          "8": [
            1,
            {
              "@": 116
            }
          ],
          "9": [
            1,
            {
              "@": 116
            }
          ],
          "11": [
            1,
            {
              "@": 116
            }
          ],
          "12": [
            1,
            {
              "@": 116
            }
          ]
        },
        "192": {
          "10": [
            0,
            138
          ],
          "15": [
            0,
            116
          ],
          "0": [
            0,
            1
          ]
        },
        "193": {
          "0": [
            1,
            {
              "@": 99
            }
          ]
        },
        "194": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "46": [
            0,
            126
          ],
          "24": [
            0,
            172
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "195": {
          "2": [
            1,
            {
              "@": 70
            }
          ]
        },
        "196": {
          "55": [
            0,
            213
          ],
          "10": [
            0,
            2
          ],
          "56": [
            0,
            135
          ]
        },
        "197": {
          "52": [
            1,
            {
              "@": 91
            }
          ]
        },
        "198": {
          "15": [
            0,
            222
          ],
          "10": [
            0,
            138
          ],
          "63": [
            0,
            214
          ],
          "0": [
            0,
            134
          ],
          "75": [
            0,
            37
          ]
        },
        "199": {
          "10": [
            0,
            2
          ],
          "56": [
            0,
            182
          ]
        },
        "200": {
          "3": [
            1,
            {
              "@": 113
            }
          ],
          "4": [
            1,
            {
              "@": 113
            }
          ],
          "5": [
            1,
            {
              "@": 113
            }
          ],
          "6": [
            1,
            {
              "@": 113
            }
          ],
          "7": [
            1,
            {
              "@": 113
            }
          ],
          "8": [
            1,
            {
              "@": 113
            }
          ],
          "9": [
            1,
            {
              "@": 113
            }
          ],
          "10": [
            1,
            {
              "@": 113
            }
          ],
          "11": [
            1,
            {
              "@": 113
            }
          ],
          "12": [
            1,
            {
              "@": 113
            }
          ]
        },
        "201": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "2": [
            0,
            53
          ],
          "23": [
            0,
            72
          ],
          "24": [
            0,
            208
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "202": {
          "16": [
            0,
            5
          ],
          "10": [
            0,
            125
          ],
          "40": [
            0,
            200
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "41": [
            0,
            140
          ],
          "21": [
            0,
            96
          ],
          "15": [
            0,
            162
          ],
          "22": [
            0,
            221
          ],
          "12": [
            1,
            {
              "@": 35
            }
          ]
        },
        "203": {
          "0": [
            0,
            74
          ]
        },
        "204": {
          "76": [
            0,
            21
          ],
          "58": [
            0,
            215
          ]
        },
        "205": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "46": [
            0,
            128
          ],
          "24": [
            0,
            172
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "206": {
          "0": [
            1,
            {
              "@": 100
            }
          ]
        },
        "207": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "2": [
            0,
            212
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ],
          "35": [
            0,
            62
          ]
        },
        "208": {
          "3": [
            1,
            {
              "@": 120
            }
          ],
          "4": [
            1,
            {
              "@": 120
            }
          ],
          "5": [
            1,
            {
              "@": 120
            }
          ],
          "6": [
            1,
            {
              "@": 120
            }
          ],
          "7": [
            1,
            {
              "@": 120
            }
          ],
          "8": [
            1,
            {
              "@": 120
            }
          ],
          "2": [
            1,
            {
              "@": 120
            }
          ],
          "9": [
            1,
            {
              "@": 120
            }
          ],
          "10": [
            1,
            {
              "@": 120
            }
          ],
          "11": [
            1,
            {
              "@": 120
            }
          ]
        },
        "209": {
          "2": [
            1,
            {
              "@": 51
            }
          ],
          "3": [
            1,
            {
              "@": 51
            }
          ],
          "4": [
            1,
            {
              "@": 51
            }
          ],
          "5": [
            1,
            {
              "@": 51
            }
          ],
          "6": [
            1,
            {
              "@": 51
            }
          ],
          "7": [
            1,
            {
              "@": 51
            }
          ],
          "8": [
            1,
            {
              "@": 51
            }
          ],
          "9": [
            1,
            {
              "@": 51
            }
          ],
          "10": [
            1,
            {
              "@": 51
            }
          ],
          "11": [
            1,
            {
              "@": 51
            }
          ],
          "12": [
            1,
            {
              "@": 51
            }
          ]
        },
        "210": {
          "77": [
            0,
            94
          ],
          "78": [
            0,
            171
          ],
          "79": [
            0,
            92
          ],
          "80": [
            0,
            73
          ]
        },
        "211": {
          "0": [
            0,
            178
          ]
        },
        "212": {
          "2": [
            1,
            {
              "@": 59
            }
          ],
          "3": [
            1,
            {
              "@": 59
            }
          ],
          "4": [
            1,
            {
              "@": 59
            }
          ],
          "5": [
            1,
            {
              "@": 59
            }
          ],
          "6": [
            1,
            {
              "@": 59
            }
          ],
          "7": [
            1,
            {
              "@": 59
            }
          ],
          "8": [
            1,
            {
              "@": 59
            }
          ],
          "9": [
            1,
            {
              "@": 59
            }
          ],
          "10": [
            1,
            {
              "@": 59
            }
          ],
          "11": [
            1,
            {
              "@": 59
            }
          ],
          "12": [
            1,
            {
              "@": 59
            }
          ]
        },
        "213": {
          "0": [
            0,
            83
          ],
          "10": [
            0,
            2
          ],
          "13": [
            0,
            124
          ],
          "2": [
            0,
            220
          ],
          "56": [
            0,
            141
          ]
        },
        "214": {
          "0": [
            1,
            {
              "@": 104
            }
          ]
        },
        "215": {
          "29": [
            1,
            {
              "@": 96
            }
          ],
          "10": [
            1,
            {
              "@": 96
            }
          ],
          "32": [
            1,
            {
              "@": 96
            }
          ],
          "31": [
            1,
            {
              "@": 96
            }
          ]
        },
        "216": {
          "0": [
            0,
            145
          ]
        },
        "217": {
          "0": [
            0,
            97
          ]
        },
        "218": {
          "2": [
            0,
            170
          ]
        },
        "219": {
          "2": [
            1,
            {
              "@": 57
            }
          ],
          "3": [
            1,
            {
              "@": 57
            }
          ],
          "4": [
            1,
            {
              "@": 57
            }
          ],
          "5": [
            1,
            {
              "@": 57
            }
          ],
          "6": [
            1,
            {
              "@": 57
            }
          ],
          "7": [
            1,
            {
              "@": 57
            }
          ],
          "8": [
            1,
            {
              "@": 57
            }
          ],
          "9": [
            1,
            {
              "@": 57
            }
          ],
          "10": [
            1,
            {
              "@": 57
            }
          ],
          "11": [
            1,
            {
              "@": 57
            }
          ],
          "12": [
            1,
            {
              "@": 57
            }
          ]
        },
        "220": {
          "13": [
            0,
            156
          ],
          "0": [
            0,
            83
          ],
          "2": [
            1,
            {
              "@": 87
            }
          ]
        },
        "221": {
          "3": [
            1,
            {
              "@": 39
            }
          ],
          "4": [
            1,
            {
              "@": 39
            }
          ],
          "5": [
            1,
            {
              "@": 39
            }
          ],
          "6": [
            1,
            {
              "@": 39
            }
          ],
          "7": [
            1,
            {
              "@": 39
            }
          ],
          "8": [
            1,
            {
              "@": 39
            }
          ],
          "9": [
            1,
            {
              "@": 39
            }
          ],
          "10": [
            1,
            {
              "@": 39
            }
          ],
          "11": [
            1,
            {
              "@": 39
            }
          ],
          "12": [
            1,
            {
              "@": 39
            }
          ]
        },
        "222": {
          "63": [
            0,
            214
          ],
          "0": [
            0,
            100
          ],
          "75": [
            0,
            119
          ]
        },
        "223": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "2": [
            0,
            6
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ],
          "35": [
            0,
            62
          ]
        },
        "224": {
          "16": [
            0,
            5
          ],
          "8": [
            0,
            102
          ],
          "18": [
            0,
            132
          ],
          "34": [
            0,
            204
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "11": [
            0,
            198
          ],
          "3": [
            0,
            51
          ],
          "33": [
            0,
            207
          ],
          "35": [
            0,
            154
          ],
          "22": [
            0,
            163
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "10": [
            0,
            111
          ],
          "9": [
            0,
            40
          ],
          "23": [
            0,
            72
          ],
          "4": [
            0,
            64
          ],
          "21": [
            0,
            96
          ]
        },
        "225": {
          "3": [
            1,
            {
              "@": 61
            }
          ],
          "4": [
            1,
            {
              "@": 61
            }
          ],
          "5": [
            1,
            {
              "@": 61
            }
          ],
          "6": [
            1,
            {
              "@": 61
            }
          ],
          "7": [
            1,
            {
              "@": 61
            }
          ],
          "8": [
            1,
            {
              "@": 61
            }
          ],
          "2": [
            1,
            {
              "@": 61
            }
          ],
          "9": [
            1,
            {
              "@": 61
            }
          ],
          "10": [
            1,
            {
              "@": 61
            }
          ],
          "11": [
            1,
            {
              "@": 61
            }
          ]
        },
        "226": {
          "25": [
            0,
            81
          ],
          "2": [
            0,
            99
          ],
          "67": [
            0,
            79
          ]
        },
        "227": {
          "13": [
            0,
            84
          ],
          "0": [
            0,
            83
          ],
          "53": [
            1,
            {
              "@": 81
            }
          ]
        },
        "228": {
          "16": [
            0,
            5
          ],
          "4": [
            0,
            64
          ],
          "3": [
            0,
            51
          ],
          "8": [
            0,
            102
          ],
          "46": [
            0,
            42
          ],
          "24": [
            0,
            172
          ],
          "18": [
            0,
            132
          ],
          "19": [
            0,
            68
          ],
          "20": [
            0,
            108
          ],
          "7": [
            0,
            30
          ],
          "21": [
            0,
            96
          ],
          "11": [
            0,
            198
          ],
          "23": [
            0,
            72
          ],
          "10": [
            0,
            7
          ],
          "6": [
            0,
            50
          ],
          "5": [
            0,
            61
          ],
          "9": [
            0,
            40
          ],
          "22": [
            0,
            225
          ]
        },
        "229": {
          "2": [
            1,
            {
              "@": 126
            }
          ],
          "25": [
            1,
            {
              "@": 126
            }
          ]
        },
        "230": {
          "0": [
            0,
            110
          ]
        }
      },
      "start_states": {
        "start": 137
      },
      "end_states": {
        "start": 185
      }
    },
    "__type__": "ParsingFrontend"
  },
  "rules": [
    {
      "@": 35
    },
    {
      "@": 36
    },
    {
      "@": 37
    },
    {
      "@": 38
    },
    {
      "@": 39
    },
    {
      "@": 40
    },
    {
      "@": 41
    },
    {
      "@": 42
    },
    {
      "@": 43
    },
    {
      "@": 44
    },
    {
      "@": 45
    },
    {
      "@": 46
    },
    {
      "@": 47
    },
    {
      "@": 48
    },
    {
      "@": 49
    },
    {
      "@": 50
    },
    {
      "@": 51
    },
    {
      "@": 52
    },
    {
      "@": 53
    },
    {
      "@": 54
    },
    {
      "@": 55
    },
    {
      "@": 56
    },
    {
      "@": 57
    },
    {
      "@": 58
    },
    {
      "@": 59
    },
    {
      "@": 60
    },
    {
      "@": 61
    },
    {
      "@": 62
    },
    {
      "@": 63
    },
    {
      "@": 64
    },
    {
      "@": 65
    },
    {
      "@": 66
    },
    {
      "@": 67
    },
    {
      "@": 68
    },
    {
      "@": 69
    },
    {
      "@": 70
    },
    {
      "@": 71
    },
    {
      "@": 72
    },
    {
      "@": 73
    },
    {
      "@": 74
    },
    {
      "@": 75
    },
    {
      "@": 76
    },
    {
      "@": 77
    },
    {
      "@": 78
    },
    {
      "@": 79
    },
    {
      "@": 80
    },
    {
      "@": 81
    },
    {
      "@": 82
    },
    {
      "@": 83
    },
    {
      "@": 84
    },
    {
      "@": 85
    },
    {
      "@": 86
    },
    {
      "@": 87
    },
    {
      "@": 88
    },
    {
      "@": 89
    },
    {
      "@": 90
    },
    {
      "@": 91
    },
    {
      "@": 92
    },
    {
      "@": 93
    },
    {
      "@": 94
    },
    {
      "@": 95
    },
    {
      "@": 96
    },
    {
      "@": 97
    },
    {
      "@": 98
    },
    {
      "@": 99
    },
    {
      "@": 100
    },
    {
      "@": 101
    },
    {
      "@": 102
    },
    {
      "@": 103
    },
    {
      "@": 104
    },
    {
      "@": 105
    },
    {
      "@": 106
    },
    {
      "@": 107
    },
    {
      "@": 108
    },
    {
      "@": 109
    },
    {
      "@": 110
    },
    {
      "@": 111
    },
    {
      "@": 112
    },
    {
      "@": 113
    },
    {
      "@": 114
    },
    {
      "@": 115
    },
    {
      "@": 116
    },
    {
      "@": 117
    },
    {
      "@": 118
    },
    {
      "@": 119
    },
    {
      "@": 120
    },
    {
      "@": 121
    },
    {
      "@": 122
    },
    {
      "@": 123
    },
    {
      "@": 124
    },
    {
      "@": 125
    },
    {
      "@": 126
    },
    {
      "@": 127
    },
    {
      "@": 128
    }
  ],
  "options": {
    "debug": false,
    "strict": false,
    "keep_all_tokens": false,
    "tree_class": null,
    "cache": false,
    "postlex": null,
    "parser": "lalr",
    "lexer": "contextual",
    "transformer": null,
    "start": [
      "start"
    ],
    "priority": "normal",
    "ambiguity": "auto",
    "regex": false,
    "propagate_positions": false,
    "lexer_callbacks": {},
    "maybe_placeholders": false,
    "edit_terminals": null,
    "g_regex_flags": 0,
    "use_bytes": false,
    "import_paths": [],
    "source_path": null,
    "_plugins": {}
  },
  "__type__": "Lark"
};

var MEMO={
  "0": {
    "name": "WS_INLINE",
    "pattern": {
      "value": "(?:(?:\\ |\t))+",
      "flags": [],
      "raw": null,
      "_width": [
        1,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "1": {
    "name": "GROUP",
    "pattern": {
      "value": "group",
      "flags": [],
      "raw": "/group/",
      "_width": [
        5,
        5
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "2": {
    "name": "SET",
    "pattern": {
      "value": "set",
      "flags": [],
      "raw": "/set/",
      "_width": [
        3,
        3
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "3": {
    "name": "SEQUENCE",
    "pattern": {
      "value": "sequence",
      "flags": [],
      "raw": "/sequence/",
      "_width": [
        8,
        8
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "4": {
    "name": "QUANTOR_UNIVERSAL",
    "pattern": {
      "value": "(ALL|!ALL|\u00acALL)",
      "flags": [],
      "raw": "/(ALL|!ALL|\u00acALL)/",
      "_width": [
        3,
        4
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "5": {
    "name": "QUANTOR_EXISTENTIAL",
    "pattern": {
      "value": "(EXIST|!EXIST|\u00acEXIST)",
      "flags": [],
      "raw": "/(EXIST|!EXIST|\u00acEXIST)/",
      "_width": [
        5,
        6
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "6": {
    "name": "OPERATOR_UNARY",
    "pattern": {
      "value": "NOT",
      "flags": [],
      "raw": "/NOT/",
      "_width": [
        3,
        3
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "7": {
    "name": "OPERATOR_BINARY",
    "pattern": {
      "value": "(NAND|!AND|\u00acAND|NOR|!OR|\u00acOR|XOR|IMPLY|NIMPLY|!IMPLY|\u00acIMPLY)",
      "flags": [],
      "raw": "/(NAND|!AND|\u00acAND|NOR|!OR|\u00acOR|XOR|IMPLY|NIMPLY|!IMPLY|\u00acIMPLY)/",
      "_width": [
        3,
        6
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "8": {
    "name": "OPERATOR_N_ARY",
    "pattern": {
      "value": "(AND|OR)",
      "flags": [],
      "raw": "/(AND|OR)/",
      "_width": [
        2,
        3
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "9": {
    "name": "RESULTS_ARROW",
    "pattern": {
      "value": "=>",
      "flags": [],
      "raw": "/=>/",
      "_width": [
        2,
        2
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "10": {
    "name": "ENUM_FUNCTIONS",
    "pattern": {
      "value": "frequency|minimum|maximum|average|stddev",
      "flags": [],
      "raw": "/frequency|minimum|maximum|average|stddev/",
      "_width": [
        6,
        9
      ],
      "__type__": "PatternRE"
    },
    "priority": 3,
    "__type__": "TerminalDef"
  },
  "11": {
    "name": "VARIABLE",
    "pattern": {
      "value": "[a-zA-Z_][a-zA-Z0-9_\\.]*",
      "flags": [],
      "raw": "/[a-zA-Z_][a-zA-Z0-9_\\.]*/",
      "_width": [
        1,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 2,
    "__type__": "TerminalDef"
  },
  "12": {
    "name": "OPERATOR",
    "pattern": {
      "value": "(<>|>=|<=|<|>|!=|\u00ac=|\u00ac~|~|\u00ac|=|!|in)",
      "flags": [],
      "raw": "/(<>|>=|<=|<|>|!=|\u00ac=|\u00ac~|~|\u00ac|=|!|in)/",
      "_width": [
        1,
        2
      ],
      "__type__": "PatternRE"
    },
    "priority": 1,
    "__type__": "TerminalDef"
  },
  "13": {
    "name": "NUMBER_EXPRESSION",
    "pattern": {
      "value": "[(]*([a-zA-Z][a-zA-Z0-9]*|-?([0-9]+[.])?[0-9]+[smy]?)( +[*\\/+-] +[(]*([a-zA-Z][a-zA-Z0-9]*|-?([0-9]+[.])?[0-9]+[smy]?))?[)]*",
      "flags": [],
      "raw": "/[(]*([a-zA-Z][a-zA-Z0-9]*|-?([0-9]+[.])?[0-9]+[smy]?)( +[*\\/+-] +[(]*([a-zA-Z][a-zA-Z0-9]*|-?([0-9]+[.])?[0-9]+[smy]?))?[)]*/",
      "_width": [
        1,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 1,
    "__type__": "TerminalDef"
  },
  "14": {
    "name": "REPETITION",
    "pattern": {
      "value": "(\\d+\\.\\.(\\d+|\\*)|[1-9]+\\d*)",
      "flags": [],
      "raw": "/(\\d+\\.\\.(\\d+|\\*)|[1-9]+\\d*)/",
      "_width": [
        1,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 1,
    "__type__": "TerminalDef"
  },
  "15": {
    "name": "STRING_LITERAL",
    "pattern": {
      "value": "('.+'|\".+\")",
      "flags": [],
      "raw": "/('.+'|\".+\")/",
      "_width": [
        3,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "16": {
    "name": "REGEX",
    "pattern": {
      "value": "\\/.+\\/",
      "flags": [],
      "raw": "/\\/.+\\//",
      "_width": [
        3,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "17": {
    "name": "RANGE",
    "pattern": {
      "value": "([-+][0-9]+|0)[.]{2}([-+][0-9]+|0)",
      "flags": [],
      "raw": "/([-+][0-9]+|0)[.]{2}([-+][0-9]+|0)/",
      "_width": [
        4,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "18": {
    "name": "STRING",
    "pattern": {
      "value": "[^\n\r ].*",
      "flags": [],
      "raw": "/[^\\n\\r ].*/",
      "_width": [
        1,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "19": {
    "name": "SL_COMMENT",
    "pattern": {
      "value": "#[^\r\n]+(\r?\n[\t ]*)+",
      "flags": [],
      "raw": null,
      "_width": [
        3,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "20": {
    "name": "DL_COMMENT",
    "pattern": {
      "value": "<#(>|#*[^#>]+)*#+>(\r?\n[\t ]*)+",
      "flags": [],
      "raw": null,
      "_width": [
        5,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "21": {
    "name": "_NL",
    "pattern": {
      "value": "(\r?\n[\t ]*)+",
      "flags": [],
      "raw": "/(\\r?\\n[\\t ]*)+/",
      "_width": [
        1,
        4294967295
      ],
      "__type__": "PatternRE"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "22": {
    "name": "AT",
    "pattern": {
      "value": "@",
      "flags": [],
      "raw": "\"@\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "23": {
    "name": "PLAIN",
    "pattern": {
      "value": "plain",
      "flags": [],
      "raw": "\"plain\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "24": {
    "name": "ANALYSIS",
    "pattern": {
      "value": "analysis",
      "flags": [],
      "raw": "\"analysis\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "25": {
    "name": "COLLOCATION",
    "pattern": {
      "value": "collocation",
      "flags": [],
      "raw": "\"collocation\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "26": {
    "name": "CONTEXT",
    "pattern": {
      "value": "context",
      "flags": [],
      "raw": "\"context\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "27": {
    "name": "ENTITIES",
    "pattern": {
      "value": "entities",
      "flags": [],
      "raw": "\"entities\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "28": {
    "name": "ATTRIBUTES",
    "pattern": {
      "value": "attributes",
      "flags": [],
      "raw": "\"attributes\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "29": {
    "name": "FILTER",
    "pattern": {
      "value": "filter",
      "flags": [],
      "raw": "\"filter\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "30": {
    "name": "FUNCTIONS",
    "pattern": {
      "value": "functions",
      "flags": [],
      "raw": "\"functions\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "31": {
    "name": "CENTER",
    "pattern": {
      "value": "center",
      "flags": [],
      "raw": "\"center\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "32": {
    "name": "WINDOW",
    "pattern": {
      "value": "window",
      "flags": [],
      "raw": "\"window\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "33": {
    "name": "SPACE",
    "pattern": {
      "value": "space",
      "flags": [],
      "raw": "\"space\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "34": {
    "name": "ATTRIBUTE",
    "pattern": {
      "value": "attribute",
      "flags": [],
      "raw": "\"attribute\"",
      "__type__": "PatternStr"
    },
    "priority": 0,
    "__type__": "TerminalDef"
  },
  "35": {
    "origin": {
      "name": "start",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      },
      {
        "name": "__start_plus_0",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": true,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "36": {
    "origin": {
      "name": "start",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": true,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "37": {
    "origin": {
      "name": "start",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__start_plus_0",
        "__type__": "NonTerminal"
      }
    ],
    "order": 2,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": true,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "38": {
    "origin": {
      "name": "start",
      "__type__": "NonTerminal"
    },
    "expansion": [],
    "order": 3,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": true,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "39": {
    "origin": {
      "name": "query",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "statement__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "40": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "SEQUENCE",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "repetition",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_3",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "sequence",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "41": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "SEQUENCE",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_3",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 1,
    "alias": "sequence",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "42": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "SEQUENCE",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "repetition",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_3",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 2,
    "alias": "sequence",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "43": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "SEQUENCE",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_3",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 3,
    "alias": "sequence",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "44": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "SET",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_3",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 4,
    "alias": "set",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "45": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "SET",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_3",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 5,
    "alias": "set",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "46": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "GROUP",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_3",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 6,
    "alias": "group",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "47": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "GROUP",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_3",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 7,
    "alias": "group",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "48": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "quantor__universal",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "args__q_two",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 8,
    "alias": "universal_quantification",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "49": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "quantor__existential",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "args__q_one",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 9,
    "alias": "existential_quantification",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "50": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "operator__unary",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "args__one",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 10,
    "alias": "logical_op_unary",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "51": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "operator__binary",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "args__two",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 11,
    "alias": "logical_op_binary",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "52": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "operator__n_ary",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "args__any",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 12,
    "alias": "logical_op_n_ary",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "53": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "layer",
        "__type__": "NonTerminal"
      },
      {
        "name": "AT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "part_of",
        "__type__": "NonTerminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_2",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 13,
    "alias": "unit",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "54": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "layer",
        "__type__": "NonTerminal"
      },
      {
        "name": "AT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "part_of",
        "__type__": "NonTerminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 14,
    "alias": "unit",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "55": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "layer",
        "__type__": "NonTerminal"
      },
      {
        "name": "AT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "part_of",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_2",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 15,
    "alias": "unit",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "56": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "layer",
        "__type__": "NonTerminal"
      },
      {
        "name": "AT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "part_of",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 16,
    "alias": "unit",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "57": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "layer",
        "__type__": "NonTerminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_2",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 17,
    "alias": "unit",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "58": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "layer",
        "__type__": "NonTerminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 18,
    "alias": "unit",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "59": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "layer",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__statement___plus_2",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 19,
    "alias": "unit",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "60": {
    "origin": {
      "name": "statement__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "layer",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 20,
    "alias": "unit",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "61": {
    "origin": {
      "name": "members",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "statement__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": "members",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "62": {
    "origin": {
      "name": "constraints",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "entity",
        "__type__": "NonTerminal"
      },
      {
        "name": "operator",
        "__type__": "NonTerminal"
      },
      {
        "name": "comparison_type__",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "comparison",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "63": {
    "origin": {
      "name": "constraints",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "statement__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "64": {
    "origin": {
      "name": "quantor__universal",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "QUANTOR_UNIVERSAL",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "65": {
    "origin": {
      "name": "quantor__existential",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "QUANTOR_EXISTENTIAL",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "66": {
    "origin": {
      "name": "operator__unary",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "OPERATOR_UNARY",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "67": {
    "origin": {
      "name": "operator__binary",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "OPERATOR_BINARY",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "68": {
    "origin": {
      "name": "operator__n_ary",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "OPERATOR_N_ARY",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "69": {
    "origin": {
      "name": "args__q_one",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "statement__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "70": {
    "origin": {
      "name": "args__q_two",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "statement__",
        "__type__": "NonTerminal"
      },
      {
        "name": "statement__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "71": {
    "origin": {
      "name": "args__one",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "constraints",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "72": {
    "origin": {
      "name": "args__two",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "constraints",
        "__type__": "NonTerminal"
      },
      {
        "name": "constraints",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "73": {
    "origin": {
      "name": "args__any",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "constraints",
        "__type__": "NonTerminal"
      },
      {
        "name": "__statement___plus_2",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "74": {
    "origin": {
      "name": "results",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "RESULTS_ARROW",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "results_type__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": "results",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "75": {
    "origin": {
      "name": "results_type__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "PLAIN",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "context",
        "__type__": "NonTerminal"
      },
      {
        "name": "entities",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "results_plain",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "76": {
    "origin": {
      "name": "results_type__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "ANALYSIS",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "attributes",
        "__type__": "NonTerminal"
      },
      {
        "name": "filter",
        "__type__": "NonTerminal"
      },
      {
        "name": "functions",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 1,
    "alias": "results_analysis",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "77": {
    "origin": {
      "name": "results_type__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "ANALYSIS",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "attributes",
        "__type__": "NonTerminal"
      },
      {
        "name": "functions",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 2,
    "alias": "results_analysis",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "78": {
    "origin": {
      "name": "results_type__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "COLLOCATION",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "center",
        "__type__": "NonTerminal"
      },
      {
        "name": "window",
        "__type__": "NonTerminal"
      },
      {
        "name": "attribute",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 3,
    "alias": "results_collocation",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "79": {
    "origin": {
      "name": "results_type__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "COLLOCATION",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "space",
        "__type__": "NonTerminal"
      },
      {
        "name": "attribute",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 4,
    "alias": "results_collocation",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "80": {
    "origin": {
      "name": "context",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "CONTEXT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": "context",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "81": {
    "origin": {
      "name": "context",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "CONTEXT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 1,
    "alias": "context",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "82": {
    "origin": {
      "name": "context",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "CONTEXT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      }
    ],
    "order": 2,
    "alias": "context",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "83": {
    "origin": {
      "name": "context",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "CONTEXT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "label",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 3,
    "alias": "context",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "84": {
    "origin": {
      "name": "entities",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "ENTITIES",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__entities_plus_4",
        "__type__": "NonTerminal"
      },
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": "entities",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "85": {
    "origin": {
      "name": "entities",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "ENTITIES",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__entities_plus_4",
        "__type__": "NonTerminal"
      },
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 1,
    "alias": "entities",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "86": {
    "origin": {
      "name": "entities",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "ENTITIES",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__entities_plus_4",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      }
    ],
    "order": 2,
    "alias": "entities",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "87": {
    "origin": {
      "name": "entities",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "ENTITIES",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__entities_plus_4",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 3,
    "alias": "entities",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "88": {
    "origin": {
      "name": "attributes",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "ATTRIBUTES",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__attributes_plus_5",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "attributes",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "89": {
    "origin": {
      "name": "filter",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "FILTER",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__filter_plus_6",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "filter",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "90": {
    "origin": {
      "name": "functions",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "FUNCTIONS",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__functions_plus_7",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "functions",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "91": {
    "origin": {
      "name": "center",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "CENTER",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "entity_ref__",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "center",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "92": {
    "origin": {
      "name": "window",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "WINDOW",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "range__",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "window",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "93": {
    "origin": {
      "name": "space",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "SPACE",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "__entities_plus_4",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "space",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "94": {
    "origin": {
      "name": "attribute",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "ATTRIBUTE",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "_INDENT",
        "filter_out": true,
        "__type__": "Terminal"
      },
      {
        "name": "attribute__",
        "__type__": "NonTerminal"
      },
      {
        "name": "_DEDENT",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "attribute",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "95": {
    "origin": {
      "name": "entity",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "VARIABLE",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "96": {
    "origin": {
      "name": "operator",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "OPERATOR",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "97": {
    "origin": {
      "name": "comparison_type__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "NUMBER_EXPRESSION",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "math_comparison",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "98": {
    "origin": {
      "name": "comparison_type__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "STRING_LITERAL",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 1,
    "alias": "string_comparison",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "99": {
    "origin": {
      "name": "comparison_type__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "REGEX",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 2,
    "alias": "regex_comparison",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "100": {
    "origin": {
      "name": "comparison_type__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "VARIABLE",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 3,
    "alias": "entity_comparison",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "101": {
    "origin": {
      "name": "label",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "VARIABLE",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "label",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "102": {
    "origin": {
      "name": "layer",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "VARIABLE",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "layer",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "103": {
    "origin": {
      "name": "part_of",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "VARIABLE",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "part_of",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "104": {
    "origin": {
      "name": "repetition",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "REPETITION",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": "repetition",
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "105": {
    "origin": {
      "name": "entity_ref__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "VARIABLE",
        "filter_out": false,
        "__type__": "Terminal"
      },
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "106": {
    "origin": {
      "name": "entity_ref__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "VARIABLE",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "107": {
    "origin": {
      "name": "functions__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "ENUM_FUNCTIONS",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "108": {
    "origin": {
      "name": "attribute__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "STRING",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "109": {
    "origin": {
      "name": "filter__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "STRING",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "110": {
    "origin": {
      "name": "range__",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "RANGE",
        "filter_out": false,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "111": {
    "origin": {
      "name": "__start_plus_0",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "query",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "112": {
    "origin": {
      "name": "__start_plus_0",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "results",
        "__type__": "NonTerminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "113": {
    "origin": {
      "name": "__start_plus_0",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__start_plus_0",
        "__type__": "NonTerminal"
      },
      {
        "name": "query",
        "__type__": "NonTerminal"
      }
    ],
    "order": 2,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "114": {
    "origin": {
      "name": "__start_plus_0",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__start_plus_0",
        "__type__": "NonTerminal"
      },
      {
        "name": "results",
        "__type__": "NonTerminal"
      }
    ],
    "order": 3,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "115": {
    "origin": {
      "name": "__start_star_1",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "116": {
    "origin": {
      "name": "__start_star_1",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__start_star_1",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "117": {
    "origin": {
      "name": "__statement___plus_2",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "constraints",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "118": {
    "origin": {
      "name": "__statement___plus_2",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__statement___plus_2",
        "__type__": "NonTerminal"
      },
      {
        "name": "constraints",
        "__type__": "NonTerminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "119": {
    "origin": {
      "name": "__statement___plus_3",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "members",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "120": {
    "origin": {
      "name": "__statement___plus_3",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__statement___plus_3",
        "__type__": "NonTerminal"
      },
      {
        "name": "members",
        "__type__": "NonTerminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "121": {
    "origin": {
      "name": "__entities_plus_4",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "entity_ref__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "122": {
    "origin": {
      "name": "__entities_plus_4",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__entities_plus_4",
        "__type__": "NonTerminal"
      },
      {
        "name": "entity_ref__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "123": {
    "origin": {
      "name": "__attributes_plus_5",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "attribute__",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "124": {
    "origin": {
      "name": "__attributes_plus_5",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__attributes_plus_5",
        "__type__": "NonTerminal"
      },
      {
        "name": "attribute__",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "125": {
    "origin": {
      "name": "__filter_plus_6",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "filter__",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "126": {
    "origin": {
      "name": "__filter_plus_6",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__filter_plus_6",
        "__type__": "NonTerminal"
      },
      {
        "name": "filter__",
        "__type__": "NonTerminal"
      },
      {
        "name": "_NL",
        "filter_out": true,
        "__type__": "Terminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "127": {
    "origin": {
      "name": "__functions_plus_7",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "functions__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 0,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  },
  "128": {
    "origin": {
      "name": "__functions_plus_7",
      "__type__": "NonTerminal"
    },
    "expansion": [
      {
        "name": "__functions_plus_7",
        "__type__": "NonTerminal"
      },
      {
        "name": "functions__",
        "__type__": "NonTerminal"
      }
    ],
    "order": 1,
    "alias": null,
    "options": {
      "keep_all_tokens": false,
      "expand1": false,
      "priority": null,
      "template_source": null,
      "empty_indices": [],
      "__type__": "RuleOptions"
    },
    "__type__": "Rule"
  }
};
