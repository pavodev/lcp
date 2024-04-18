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

<style>
/* need to use a non-scoped style because these classes are dynamically added */
.invalidDQDGlyph {
  border: 4px solid red;
  background: linear-gradient(45deg, rgba(0,0,0,0) 0%,rgba(0,0,0,0) 43%,#fff 45%,#fff 55%,rgba(0,0,0,0) 57%,rgba(0,0,0,0) 100%), linear-gradient(135deg, red 0%,red 43%,#fff 45%,#fff 55%,red 57%,red 100%);
  border-radius: 0.25em;
}
.invalidDQDLine {
	background: rgba(255, 55, 55, 0.15);
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
let decorations = null;
// We use a hack to suggest continuation for attributes with categorical values
let suggestValuesCommandId = null; // Reference to a monaco command to immediately show the suggestion modal again
let suggestValuesArray = null;  // This is either null, or set to an array of the relevant categorical values

const KEYWORDS = ['sequence','set','group','EXISTS','NOT','plain','analysis','context','entities'];

export default {
  name: "EditorView",
  data() {
    return {
      queryData: this.query,
      languageObj: null,
    };
  },
  props: ["query", "defaultQuery", "corpora", "invalidError"],
  watch: {
    defaultQuery(){
      editor.getModel().setValue(this.defaultQuery);
    },
    corpora: {
      handler: function() {

        // Distroy old provider if exists
        if (this.languageObj) {
          this.languageObj()
        }

        // Register a completion item provider for the new language
        const { dispose } = monaco.languages.registerCompletionItemProvider("DQDmonaco", {
          provideCompletionItems: (model, position) => {
            var word = model.getWordUntilPosition(position), column = position.column;
            while (suggestValuesArray===null && word.word=="" && column>0) {
              column--;
              let previousWord = model.getWordUntilPosition({lineNumber: position.lineNumber, column: column}).word;
              if (previousWord) return this.triggerAutocomplete(previousWord, /*prefixWithSpace:*/ true);
            }
            var range = {
              startLineNumber: position.lineNumber,
              endLineNumber: position.lineNumber,
              startColumn: word.startColumn,
              endColumn: word.endColumn,
            };

            // Use suggestValuesArray if it is set
            var suggestions = suggestValuesArray
              ? suggestValuesArray.map( (item) => Object({
                label: item,
                kind: monaco.languages.CompletionItemKind.Text,
                insertText: `"${item}"`,
                range: range
              }))
              : this.mainSuggestions(range)
              // : [
              //     {
              //       label: "Token",
              //       kind: monaco.languages.CompletionItemKind.Text,
              //       insertText: "Token\n\tform = test1",
              //       range: range
              //     },
              //     {
              //       label: "Segment",
              //       kind: monaco.languages.CompletionItemKind.Text,
              //       insertText: "Segment s1",
              //       range: range,
              //     },
              //     // {
              //     //   label: "NOT",
              //     //   kind: monaco.languages.CompletionItemKind.Keyword,
              //     //   insertText: "NOT\n\t",
              //     //   range: range,
              //     // },
              //     ...this.columnHeaders().map(item => {
              //       return {
              //         label: item,
              //         kind: monaco.languages.CompletionItemKind.Keyword,
              //         insertText: `${item} = `,
              //         range: range,
              //         command: {
              //           id: suggestValuesCommandId,
              //           title: "insert values",
              //           arguments: [item]
              //         }
              //       }
              //     }),
              //     {
              //       label: "from",
              //       kind: monaco.languages.CompletionItemKind.Keyword,
              //       insertText: "from = ",
              //       range: range,
              //     },
              //     {
              //       label: "head",
              //       kind: monaco.languages.CompletionItemKind.Keyword,
              //       insertText: "head = ",
              //       range: range,
              //     },
              //     {
              //       label: "dep",
              //       kind: monaco.languages.CompletionItemKind.Keyword,
              //       insertText: "dep = ",
              //       range: range,
              //     },
              //     {
              //       label: "to",
              //       kind: monaco.languages.CompletionItemKind.Keyword,
              //       insertText: "to = ",
              //       range: range,
              //     },
              //     {
              //       label: "label",
              //       kind: monaco.languages.CompletionItemKind.Keyword,
              //       insertText: "label = ",
              //       range: range,
              //     },
              //     // {
              //     //   label: "pos",
              //     //   kind: monaco.languages.CompletionItemKind.Keyword,
              //     //   insertText: "pos = ",
              //     //   range: range,
              //     // },
              //     // {
              //     //   label: "AND",
              //     //   kind: monaco.languages.CompletionItemKind.Keyword,
              //     //   insertText: "AND\n\t",
              //     //   range: range,
              //     // },
              //     // {
              //     //   label: "OR",
              //     //   kind: monaco.languages.CompletionItemKind.Keyword,
              //     //   insertText: "OR\n\t",
              //     //   range: range,
              //     // },
              //     {
              //       label: "DepRel",
              //       kind: monaco.languages.CompletionItemKind.Text,
              //       insertText: "DepRel dr1\n\t",
              //       insertTextRules:
              //         monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              //       range: range,
              //     },
              //     {
              //       label: "group",
              //       kind: monaco.languages.CompletionItemKind.Snippet,
              //       insertText: "group g\n\tt1\n\tt2",
              //       insertTextRules:
              //         monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              //       documentation: "If-Else Statement",
              //       range: range,
              //     },
              //     {
              //       label: "distance",
              //       kind: monaco.languages.CompletionItemKind.Snippet,
              //       insertText: "distance\n\tfrom = \n\tto = \n\tvalue = ",
              //       insertTextRules:
              //         monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              //       documentation: "If-Else Statement",
              //       range: range,
              //     },
              //     {
              //       label: "sequence",
              //       kind: monaco.languages.CompletionItemKind.Snippet,
              //       insertText: "sequence\n\t",
              //       insertTextRules:
              //         monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
              //       documentation: "If-Else Statement",
              //       range: range,
              //     },
              //   ];
            suggestValuesArray = null;
            return { suggestions: suggestions };
          },
          triggerCharacters: ["="," "]
        });
        this.languageObj = dispose
      },
      immediate: true
    },
    invalidError: {
      handler() {
        this.updateErrors();
      }
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
      glyphMargin: true
    });

    editor.getModel().onDidChangeContent(() => {
      this.updateContent();
      this.updateErrors();
    });

    editor.getModel().updateOptions({ tabSize: 4 });

    // editor.onDidFocusEditorText(()=>{
    //   this.$refs.editor.style.height = "500px"
    //   editor.layout()
    // })
    // editor.onDidBlurEditorWidget(()=>{
    //   this.$refs.editor.style.height = "200px"
    //   editor.layout()
    // })

    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, ()=>console.log("Enter") || this.$emit("submit"));

    // Generate a command ID for manual triggering of autocompletion
    // eslint-disable-next-line no-unused-vars
    suggestValuesCommandId = editor.addCommand( 0, (_,suggestion) => this.triggerAutocomplete(suggestion) );

    window.addEventListener('contextmenu', e => {
      e.stopImmediatePropagation()
    }, true);
  },
  methods: {
    mainSuggestions(range) {
      const s = [];
      for (let [layer,props] of Object.entries(this.corpora.corpus.layer)) {
        s.push({
          label: layer,
          kind: monaco.languages.CompletionItemKind.Text,
          insertText: layer,
          range: range
        });
        for (let a in props.attributes)
          s.push({
          label: a,
          kind: monaco.languages.CompletionItemKind.Keyword,
          insertText: `${a} = `,
          range: range,
          command: {
            id: suggestValuesCommandId,
            title: "insert values",
            arguments: [a]
          }
        });
      }
      for (let k of KEYWORDS)
        s.push({
          label: k,
          kind: monaco.languages.CompletionItemKind.Keyword,
          insertText: k+' ',
          range: range
        });
      console.log("suggestions", s);
      return s;
    },
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
    triggerAutocomplete(prompt,prefixWithSpace=false) {
      if (!this.corpora || !this.corpora.corpus) return;
      console.log("prompt", prompt);
      if (prompt in this.corpora.corpus.layer)
        return setTimeout( ()=>{
          suggestValuesArray = [" "+prompt.charAt(0).toLowerCase()]; 
          editor.trigger('', 'editor.action.triggerSuggest', {});
        } , 1 );
      // eslint-disable-next-line no-unused-vars
      Object.entries(this.corpora.corpus.layer).forEach( ([_,{attributes}]) => {
        let props = (attributes||{})[prompt];
        if (!props || props.type != "categorical") return;
        let values = props.values;
        if (!(values instanceof Array) && prompt in this.corpora.corpus.glob_attr)
          values = this.corpora.corpus.glob_attr[prompt];
        if (!(values instanceof Array) || values.length==0) return;
        if (prefixWithSpace) values = values.map((v)=>" "+v);
        setTimeout( ()=>{ // Timeout necessary to prevent overlap from previous accepted suggestion
          suggestValuesArray = values; // can't directly pass an argument to triggerSuggest, so use this instead
          editor.trigger('', 'editor.action.triggerSuggest', {});
        } , 1 );
      });
    },
    processErrorMessage(message) {
      // if (message.startsWith("Unexpected token")) return "Invalid character";
      let msg = message.replace(/token [^(\s]+\([^),]+, ([^)]+)\)/,"$1")
                       .replace(/at line(.|\n)+$/,"");
      if (message.match(/Expected one of: \* STRING Previous tokens: \[Token\('OPERATOR', '[=<>]+'\)\]/))
        msg += " Provide a value for the comparison"
      return msg;
    },
    updateContent() {
      this.queryData = editor.getValue()
      this.$emit("update", this.queryData)
    },
    updateErrors() {
      if (decorations) decorations.clear();
      if (!this.invalidError) return null;
      try {
        let [line,column] = this.invalidError.match(/at line (\d+), column (\d+)/i).slice(1,3);
        setTimeout( ()=> {
          if (decorations) decorations.clear();
          if (!this.invalidError) return;
          let model = editor.getModel();
          [line,column] = [parseInt(line),parseInt(column)];
          let lineContent = model.getLineContent(line);
          if (column > lineContent.length) {
            let problematicText = this.invalidError.match(/^Unexpected \S+ \S+\([^),]+, '([^')]+)'\)/i);
            if (problematicText) {
              problematicText = problematicText[1];
              let oldline = line, nlines = model.getLineCount();
              while (line < nlines && !model.getLineContent(line).match(problematicText)) line++;
              if (line < nlines)
                column = model.getLineContent(line).length;
              else
                line = oldline;
            }
          }
          decorations = editor.createDecorationsCollection([{
            range: new monaco.Range(parseInt(line), 1, parseInt(line), parseInt(column)),
            options: {
              isWholeLine: true,
              inlineClassName: "invalidDQDLine",
              glyphMarginClassName: "invalidDQDGlyph",
              glyphMarginHoverMessage: { value: this.processErrorMessage(this.invalidError) }
            }
          }]);
        } , 1000);
      } catch { /* nothing */ }
    }
  },
};
</script>
