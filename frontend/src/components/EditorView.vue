<template>
  <div id="query-editor">
    <div id="editor" ref="editor"></div>
  </div>
</template>

<style scoped>
#query-editor {
  text-align: left;
}
#editor {
  height: 500px;
  width: 100%;
}
</style>

<script>
import * as monaco from "monaco-editor";
import DQDmonaco from "@/dqd_monaco.js";
import DQDParser from "@/dqd_parser.js";


function checkCode (content) {
  let retval = null
  class TreeIndenter extends DQDParser.Indenter {
    static get NL_type() {
      return "_NL";
    }
    get NL_type() {
      return this.constructor.NL_type;
    }
    static get OPEN_PAREN_types() {
      return [];
    }
    get OPEN_PAREN_types() {
      return this.constructor.OPEN_PAREN_types;
    }
    static get CLOSE_PAREN_types() {
      return [];
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
  let parser = DQDParser.get_parser({
    parser: "lalr",
    postlex: new TreeIndenter
  })
  try {
    parser.parser.parse(content)
  }
  catch (e) {
    // console.log("ERROR", e.token_history, e.line, e.column)
    retval = e.token_history
  }
  return retval
}

// monaco.editor.defineTheme('DQDTheme', MonacoTheme)
monaco.editor.defineTheme('DQDTheme', {
  base: 'vs',
  inherit: true,
  colors: {
    "input.background": "#DDD6C1",
		"input.foreground": "#586E75",
  },
  rules: [
    { token: "identifier", foreground: "4287f5" },
    { token: "type.identifier", foreground: "2a7f62" },
    { token: "keyword", foreground: "ff6600" },
  ],
  tokenColors: [],
});


monaco.editor.onDidCreateModel(function(model) {
  function validate() {
    let errorList = checkCode(model.getValue())
    let markers = []

    if (errorList) {
      markers = errorList.map(errorLine => {
        return {
          severity: monaco.MarkerSeverity.Error,
          startLineNumber: errorLine.line,
          startColumn: errorLine.column,
          endLineNumber: errorLine.end_line,
          endColumn: errorLine.end_column,
          message: 'Error message ...'
        }
      })
    }

    // var markers = [{
    //   severity: monaco.MarkerSeverity.Error,
    //   startLineNumber: 1,
    //   startColumn: 2,
    //   endLineNumber: 1,
    //   endColumn: 5,
    //   message: 'hi there'
    // }];

    // {
    //   "type": "_NL",
    //   "start_pos": 23,
    //   "value": "\n    ",
    //   "line": 3,
    //   "column": 12,
    //   "end_line": 4,
    //   "end_column": 5,
    //   "end_pos": 28
    // }

    // change mySpecialLanguage to whatever your language id is
    monaco.editor.setModelMarkers(model, 'DQDmonaco', markers);
  }

  let handle = null;
  model.onDidChangeContent(() => {
    // debounce
    clearTimeout(handle);
    handle = setTimeout(() => validate(), 500);
  });
  validate();
});
monaco.languages.register({ id: "DQDmonaco" });
monaco.languages.setMonarchTokensProvider("DQDmonaco", DQDmonaco);

let editor = null;
// We use a hack to suggest continuation for attributes with categorical values
let suggestValuesCommandId = null; // Reference to a monaco command to immediately show the suggestion modal again
let suggestValuesArray = null;  // This is either null, or set to an array of the relevant categorical values

export default {
  name: "EditorView",
  data() {
    return {
      queryData: this.query,
      languageObj: null,
    };
  },
  props: ["query", "corpora"],
  watch: {
    corpora: {
      handler: function() {

        // Distroy old provider if exists
        if (this.languageObj) {
          this.languageObj()
        }

        // Register a completion item provider for the new language
        const { dispose } = monaco.languages.registerCompletionItemProvider("DQDmonaco", {
          provideCompletionItems: (model, position) => {
            var word = model.getWordUntilPosition(position);
            var range = {
              startLineNumber: position.lineNumber,
              endLineNumber: position.lineNumber,
              startColumn: word.startColumn,
              endColumn: word.endColumn,
            };
            // Retrieve the command ID if the command was already created, or else create it now
            suggestValuesCommandId = suggestValuesCommandId || editor.addCommand( 0, (_,suggestion) => { // eslint-disable-line no-unused-vars
              if (!this.corpora || !this.corpora.corpus) return;
              // eslint-disable-next-line no-unused-vars
              Object.entries(this.corpora.corpus.layer).forEach( ([_,{attributes}]) => {
                let props = (attributes||{})[suggestion];
                if (props && props.type == "categorical" && props.values instanceof Array)
                  setTimeout( ()=>{ // Timeout necessary to prevent overlap from previous accepted suggestion
                    suggestValuesArray = props.values; // can't directly pass an argument to triggerSuggest, so use this instead
                    editor.trigger('', 'editor.action.triggerSuggest', {});
                  } , 1 );
              });
            } );
            // Use suggestValuesArray if it is set
            var suggestions = suggestValuesArray ? suggestValuesArray.map( (item) => Object({
              label: item,
              kind: monaco.languages.CompletionItemKind.Text,
              insertText: item,
              range: range
            })) : [
              {
                label: "Token",
                kind: monaco.languages.CompletionItemKind.Text,
                insertText: "Token\n\tform = test1",
                range: range
              },
              {
                label: "Segment",
                kind: monaco.languages.CompletionItemKind.Text,
                insertText: "Segment s1",
                range: range,
              },
              // {
              //   label: "NOT",
              //   kind: monaco.languages.CompletionItemKind.Keyword,
              //   insertText: "NOT\n\t",
              //   range: range,
              // },
              ...this.columnHeaders().map(item => {
                return {
                  label: item,
                  kind: monaco.languages.CompletionItemKind.Keyword,
                  insertText: `${item} = `,
                  range: range,
                  command: {
                    id: suggestValuesCommandId,
                    title: "insert values",
                    arguments: [item]
                  }
                }
              }),
              {
                label: "from",
                kind: monaco.languages.CompletionItemKind.Keyword,
                insertText: "from = ",
                range: range,
              },
              {
                label: "head",
                kind: monaco.languages.CompletionItemKind.Keyword,
                insertText: "head = ",
                range: range,
              },
              {
                label: "dep",
                kind: monaco.languages.CompletionItemKind.Keyword,
                insertText: "dep = ",
                range: range,
              },
              {
                label: "to",
                kind: monaco.languages.CompletionItemKind.Keyword,
                insertText: "to = ",
                range: range,
              },
              {
                label: "label",
                kind: monaco.languages.CompletionItemKind.Keyword,
                insertText: "label = ",
                range: range,
              },
              // {
              //   label: "pos",
              //   kind: monaco.languages.CompletionItemKind.Keyword,
              //   insertText: "pos = ",
              //   range: range,
              // },
              // {
              //   label: "AND",
              //   kind: monaco.languages.CompletionItemKind.Keyword,
              //   insertText: "AND\n\t",
              //   range: range,
              // },
              // {
              //   label: "OR",
              //   kind: monaco.languages.CompletionItemKind.Keyword,
              //   insertText: "OR\n\t",
              //   range: range,
              // },
              {
                label: "DepRel",
                kind: monaco.languages.CompletionItemKind.Text,
                insertText: "DepRel dr1\n\t",
                insertTextRules:
                  monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                range: range,
              },
              {
                label: "group",
                kind: monaco.languages.CompletionItemKind.Snippet,
                insertText: "group g\n\tt1\n\tt2",
                insertTextRules:
                  monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: "If-Else Statement",
                range: range,
              },
              {
                label: "distance",
                kind: monaco.languages.CompletionItemKind.Snippet,
                insertText: "distance\n\tfrom = \n\tto = \n\tvalue = ",
                insertTextRules:
                  monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: "If-Else Statement",
                range: range,
              },
              {
                label: "sequence",
                kind: monaco.languages.CompletionItemKind.Snippet,
                insertText: "sequence\n\t",
                insertTextRules:
                  monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                documentation: "If-Else Statement",
                range: range,
              },
            ];
            suggestValuesArray = null;
            return { suggestions: suggestions };
          },
        });
        this.languageObj = dispose
      },
      immediate: true
    }
  },
  mounted() {
    editor = monaco.editor.create(document.getElementById("editor"), {
      language: "DQDmonaco",
      value: this.query,
      theme: 'DQDTheme',
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      renderLineHighlight: "none",
      automaticLayout: true,
      folding: false,
    });

    editor.getModel().onDidChangeContent(() => {
      this.updateContent()
    });

    // editor.onDidFocusEditorText(()=>{
    //   this.$refs.editor.style.height = "500px"
    //   editor.layout()
    // })
    // editor.onDidBlurEditorWidget(()=>{
    //   this.$refs.editor.style.height = "200px"
    //   editor.layout()
    // })

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, ()=>this.$emit("submit"));
    
    window.addEventListener('contextmenu', e => {
      e.stopImmediatePropagation()
    }, true);
  },
  methods: {
    columnHeaders() {
      let keywords = []
      if (this.corpora && this.corpora.corpus) {
        let partitions = this.corpora.corpus.partitions
          ? this.corpora.corpus.partitions.values
          : [];
        let columns = this.corpora.corpus["mapping"]["layer"][this.corpora.corpus["segment"]];
        if (partitions.length) {
          columns = columns["partitions"][partitions[0]];
        }
        keywords = columns["prepared"]["columnHeaders"]
      }
      return keywords;
    },
    categoricalValues() {
      let keywords = []
      if (this.corpora && this.corpora.corpus)
        // eslint-disable-next-line no-unused-vars
        Object.entries(this.corpora.corpus.layer).forEach( ([_,{attributes}]) => Object.values(attributes||{}).forEach( props => {
          if (props.type == "categorical" && props.values instanceof Array)
            keywords.push(...props.values);
        }) );
      return keywords;
    },
    updateContent() {
      this.queryData = editor.getValue()
      this.$emit("update", this.queryData)
    },
  },
};
</script>
