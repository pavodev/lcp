<template>
  <div ref="mermaidcontainer">
    <vue3-mermaid
      :nodes="graphData"
      type="graph TD"
      :config="mermaidConfig"
      :key="graphIndex"
    ></vue3-mermaid>
  </div>
</template>
  
<script>

export default {
  name: "CorpusGraphView",
  data() {
    return {
      graphIndex: 0,
      mermaidConfig: {
        theme: "neutral",
      }
    };
  },
  props: ["corpus"],
  computed: {
    graphData() {
      let corpus = this.corpus;
      let data = [
        {
          id: "1",
          text: corpus.meta.name.replace(/\(/gi, "").replace(/\)/gi, ""),
          next: Object.keys(corpus.layer).filter( (layer) => !("partOf" in corpus.layer[layer]) ).map(
            (layer) => `l-${layer.toLowerCase().replace(/@/gi, "_")}`
          ),
        },
      ];
      let partOfs = {};
      Object.keys(corpus.layer).forEach((layer, index) => {
        let next = [], link = [];
        if ("attributes" in corpus.layer[layer]) {
          Object.keys(corpus.layer[layer].attributes).forEach((attribute) => {
            let attributeId = `a-${index}-${attribute.toLowerCase()}`;
            let text = attribute.replace(/@/gi, "_");
            let attributes = corpus.layer[layer].attributes[attribute];
            let attributeData = {
              id: attributeId,
              text: text,
              edgeType: "circle",
            };
            if ("entity" in attributes && attributes.entity in corpus.layer) {
              attributeData.next = [`l-${attributes.entity.toLowerCase().replace(/@/gi, "_")}`];
              attributeData.link = ["-.->|refers to|"];
            }
            else if (attributes.type!=="text") {
              let possibleValues = Object.keys(attributes);
              if (attributes.type=="categorical"){
                if (attributes.values instanceof Array && attributes.values.length>0) {
                  possibleValues = attributes.values.filter(v=>v.match(/^[^'"()]+$/));
                  if (possibleValues.length != attributes.values.length)
                    possibleValues.push("/!\\ values with special characters not listed /!\\");
                }
                else
                  possibleValues = ["List of values missing from specs"];
              }
              attributeData.text = `<abbr title='${possibleValues.join(" ")}'>${attributeData.text}</abbr>`;
            }
            data.push(attributeData);
            next.push(attributeId);
            link.push("---")
          });
        }
        // Is this necessary? Meta is an attribute itself
        if ("meta" in corpus.layer[layer]) {
          Object.keys(corpus.layer[layer].meta).forEach((meta) => {
            let metaId = `a-${index}-${meta.toLowerCase()}`;
            data.push({
              id: metaId,
              text: meta.replace(/@/gi, "_"),
              edgeType: "circle",
            });
            next.push(metaId);
            link.push("---")
          });
        }
        if ("contains" in corpus.layer[layer]) {
          let containedId = `l-${corpus.layer[layer].contains.toLowerCase().replace(/@/gi, "_")}`;
          next.push(containedId);
          link.push("-->|contains|")
          data[0].next = data[0].next.filter( (layerId) => layerId != containedId );
        }
        let layerData = {
          id: `l-${layer.toLowerCase().replace(/@/gi, "_")}`,
          text: layer.replace(/@/gi, "_"),
          next: next,
          link: link
        };
        if ("partOf" in corpus.layer[layer]) {
          let parentLayerId = `l-${corpus.layer[layer].partOf.toLowerCase().replace(/@/gi,"")}`;
          partOfs[parentLayerId] = [...(partOfs[parentLayerId]||[]), layerData];
        }
        data.push(layerData);
      });
      // Handle the partOfs after adding their parents to the structure
      for (let parentLayerId in partOfs) {
        let parentLayer = data.find( (layer) => layer.id==parentLayerId );
        if (parentLayer===undefined) continue;
        // Remove the attributes from the parent: they will be inherited by the children
        // let parentAttributes = [];
        // parentLayer.next = parentLayer.next.filter( (layerId) => 
        //   !String.prototype.startsWith.call(layerId,'a-') || (parentAttributes.push(layerId) && false)
        // );
        for (let childLayerData of partOfs[parentLayerId]) {
          // Inherit the attributes
          // childLayerData.next.push(...parentAttributes);
          // childLayerData.link.push(...parentAttributes.map( (_) => `-->|via ${parentLayer.text}|` ))
          // Add and flag the layer as "part of" the parent
          parentLayer.next.push(childLayerData);
          parentLayer.link.push("---|part of|");
        }
      }
      return data;
    },
  },
  mounted() {
    // Dirty fix -- ask Igor why a fix is needed in the first place
    let updateGraphUntilSuccessful = ()=>{
      if (this.$refs.mermaidcontainer==null) return;
      if (this.$refs.mermaidcontainer.querySelector("text.error-text")===null) 
        return this.$emit("graphReady", this.$refs.mermaidcontainer);;
      this.graphIndex += 1;
      window.requestAnimationFrame(updateGraphUntilSuccessful);
    }
    updateGraphUntilSuccessful();
  }
};
</script>
  