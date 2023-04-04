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
  height: 300px;
  width: 730px;
}
</style>

<script>
import * as monaco from "monaco-editor";
import monacoDQD from "@/monaco-dqd.js";

monaco.languages.register({ id: "monacoDQD" });
monaco.languages.setMonarchTokensProvider("monacoDQD", monacoDQD);

let editor = null;

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
    corpora() {
      // Distroy old provider if exists
      if (this.languageObj) {
        this.languageObj()
      }

      // Register a completion item provider for the new language
      const { dispose } = monaco.languages.registerCompletionItemProvider("monacoDQD", {
        provideCompletionItems: (model, position) => {
          var word = model.getWordUntilPosition(position);
          var range = {
            startLineNumber: position.lineNumber,
            endLineNumber: position.lineNumber,
            startColumn: word.startColumn,
            endColumn: word.endColumn,
          };
          var suggestions = [
            {
              label: "Token",
              kind: monaco.languages.CompletionItemKind.Text,
              insertText: "Token\n\tform = test1",
              range: range,
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
              }
            }),
            // {
            //   label: "form",
            //   kind: monaco.languages.CompletionItemKind.Keyword,
            //   insertText: "form = ",
            //   range: range,
            // },
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
              insertText: "group\n\tToken\n\tloop =",
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
          return { suggestions: suggestions };
        },
      });
      this.languageObj = dispose
    },
  },
  mounted() {
    editor = monaco.editor.create(document.getElementById("editor"), {
      language: "monacoDQD",
      value: this.query,
      minimap: { enabled: false },
    });

    editor.getModel().onDidChangeContent(() => {
      this.updateContent()
    });
  },
  methods: {
    columnHeaders() {
      let keywords = []
      if (this.corpora && this.corpora.corpus) {
        let partitions = this.corpora.corpus.partitions
          ? this.corpora.corpus.partitions.values
          : [];
        let columns = this.corpora.corpus["mapping"]["layer"]["Segment"];
        if (partitions.length) {
          columns = columns["partitions"][partitions[0]];
        }
        keywords = columns["prepared"]["columnHeaders"]
      }
      return keywords;
    },
    updateContent() {
      this.queryData = editor.getValue()
      this.$emit("update", this.queryData)
    },
  },
};
</script>
