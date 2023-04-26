<template>
  <div id="dep-rel-view">
  </div>
</template>

<style scoped>
  * >>> svg {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 12px;
  }
  * >>> svg .dep-text,
  * >>> svg .link-text {
    font-size: 9px;
  }
  * >>> svg g.text-pos {
    font-size: 80%;
    font-weight: bold;
    fill: #1e9989;
  }
  * >>> svg .link-pointer {
    fill: #656565;
  }
  * >>> svg g.text-lemma {
    font-size: 80%;
  }
  * >>> svg line.link-line {
    stroke:#1e9989;
    stroke-width: 1px;
  }

  * >>> svg g.links g.link-type-det line.link-line {
    stroke:#0078BF;
  }
  * >>> svg g.links g.link-type-det .link-text,
  * >>> svg g.links g.link-type-det .link-pointer {
    fill: #0078BF;
  }

  * >>> svg g.links g.link-type-verb line.link-line {
    stroke:#EF82F4;
  }
  * >>> svg g.links g.link-type-verb .link-text,
  * >>> svg g.links g.link-type-verb .link-pointer {
    fill: #EF82F4;
  }

  * >>> svg g.links g.link-type-punct line.link-line {
    stroke:rgb(199, 199, 199);
  }
  * >>> svg g.links g.link-type-punct .link-text,
  * >>> svg g.links g.link-type-punct .link-pointer {
    fill: rgb(199, 199, 199);
  }

  * >>> svg g.links g.link-type-conj line.link-line {
    stroke: #FFA17A;
  }
  * >>> svg g.links g.link-type-conj .link-text,
  * >>> svg g.links g.link-type-conj .link-pointer {
    fill: #FFA17A;
  }
</style>

<script>
import * as d3 from 'd3'

const browserText = (function () {
  const canvas = document.createElement('canvas'),
      context = canvas.getContext('2d');

  function getWidth(text, fontSize, fontFace) {
      context.font = fontSize + 'px ' + fontFace;
      return context.measureText(text).width;
  }

  return {
      getWidth: getWidth
  };
})()

export default {
  name: "DepRelView",
  props: ["data", "sentences"],
  data(){
    const { tokens, links } = this.buildGraphData(this.data, this.sentences)
    return {
      tokens: tokens,
      links: links,
      tokenSpace: 25,
    }
  },
  methods: {
    buildGraphData(data, sentences) {
      // let startId = this.data[1]
      let startId = sentences[0]
      let tokens = []
      let links = []
      let sumX = 0
      let matrix = []
      let linksDict = {}

      // Compile tokens and link matrix
      sentences[1].forEach((token, index) => {
        let textWidth = browserText.getWidth(token[0], 12, "Arial")
        let typeWidth = browserText.getWidth(token[2], 12, "Arial")
        tokens.push({
          id: startId + index,
          // name: startId + index
          form: token[0],
          lemma: token[1],
          pos: token[2],
          width: textWidth,
          sumX: sumX
        })
        sumX += Math.max(textWidth, typeWidth)

        // Matrix
        if (token[4]) {
          let currentTokenIndex = index
          let targetTokenIndex = token[4] - startId
          let currentTokenId = startId + index
          let targetTokenId = token[4]
          let indexLevel = Math.abs(targetTokenIndex - currentTokenIndex)

          if (!(indexLevel in linksDict)) {
            linksDict[indexLevel] = []
          }

          linksDict[indexLevel].push({
            source: currentTokenId,
            target: targetTokenId,
            label: token[5],
            originalLevel: indexLevel,
          })
        }
      })


      // Compile links
      Object.keys(linksDict).sort((a, b) => a - b).forEach(levelIndex => {
        linksDict[levelIndex].forEach(link => {
          let level = link.originalLevel
          let sourceIndex = link.source - startId
          let targetIndex = link.target - startId

          if (targetIndex < sourceIndex) {
            [sourceIndex, targetIndex] = [targetIndex, sourceIndex];
          }

          // Check level
          while (
            level > 1 &&
            (
              matrix.length < level ||
              matrix[level - 1].slice(sourceIndex, targetIndex).reduce((a, b) => a + b, 0) == 0
            )
          ) {
            level -= 1
          }

          while (matrix.length <= level) {
            matrix.push([])
          }
          if (matrix[level].length < targetIndex) {
            let extendArray = new Array(targetIndex - matrix[level].length + 1).fill(0)
            matrix[level].push.apply(matrix[level], extendArray)
          }
          matrix[level].fill(1, sourceIndex, targetIndex + 1)

          links.push({
            ...link,
            level: level,
          })
        })
      })

      return { tokens, links }
    },
    // calcArc(link) {
    //   let startId = this.data[2]
    //   let sourceIndex = link.source - startId
    //   let targetIndex = link.target - startId
    //   let startX = this.tokens[sourceIndex].sumX + this.tokens[sourceIndex].width/2 + sourceIndex*this.tokenSpace
    //   let endX = this.tokens[targetIndex ].sumX + this.tokens[targetIndex].width/2 + targetIndex*this.tokenSpace
    //   if (startX > endX) {
    //     let tmp = startX
    //     startX = endX
    //     endX = tmp
    //   }

    //   const r = Math.hypot(endX - startX, 0)*1.2;
    //   return `
    //     M${startX},60
    //     A${r},${r} 0 0,1 ${endX},60
    //   `;
    // },
    calcLine(link) {
      let diff = Math.abs(link.target - link.source)
      let startId = this.sentences[0]
      let sourceIndex = link.source - startId
      let targetIndex = link.target - startId
      let startX = this.tokens[sourceIndex].sumX + this.tokens[sourceIndex].width/2 + sourceIndex*this.tokenSpace
      let endX = this.tokens[targetIndex ].sumX + this.tokens[targetIndex].width/2 + targetIndex*this.tokenSpace
      let arrowPlacment = 'end';
      if (startX > endX) {
        let tmp = startX
        startX = endX
        endX = tmp
        arrowPlacment = 'start'
      }
      return [startX + 2, endX - 2, 70 - diff*10, arrowPlacment]
    },
  },
  mounted() {
    const countTokens = this.tokens.length
    const totalWidth = this.tokens[countTokens - 1].sumX + this.tokens[countTokens - 1].width + countTokens*this.tokenSpace + 100

    let maxLevel = Math.max(...Object.values(this.links).map(link => link.level))
    var margin = { top: 20, right: 50, bottom: 20, left: 50 },
      width = totalWidth - margin.left - margin.right,
      height = 90 + maxLevel*15 - margin.top - margin.bottom;

    d3.select("div#dep-rel-view").html('')
    const svg = d3.select("div#dep-rel-view").append("svg")
      .attr("width", width + margin.right + margin.left)
      .attr("height", height + margin.top + margin.bottom)
      .attr("viewBox", [0, 0, width, height])
      // .style("font", "10px sans-serif");

    svg.append("defs")
      .append("marker")
        .attr("id", "link-pointer")
        .attr("markerWidth", 10)
        .attr("markerHeight", 7)
        .attr("orient", "auto")
        .attr("refX", 4)
        .attr("refY", 3)
        .append("polygon")
          .attr("class", "link-pointer")
          .attr("points", "0 0, 5 3, 0 6")

    svg.append("g")
      .selectAll("text")
      .data(this.tokens)
      .join("text")
      .attr("class", d => (d.id >= this.data[1] && d.id <= this.data.at(-1)) ? "text-bold text-danger" : "")
      .text(d => d.form)
      .attr("x", (d, index) => (this.tokenSpace * index + d.sumX))
      .attr("y", 10 + maxLevel*15);

    svg.append("g")
    .attr("class", "text-lemma")
      .selectAll("text")
      .data(this.tokens)
      .join("text")
      .text(d => d.lemma)
      .attr("x", (d, index) => (this.tokenSpace * index + d.sumX))
      .attr("y", 35 + maxLevel*15);

    svg.append("g")
      .attr("class", "text-pos")
      .selectAll("text")
      .data(this.tokens)
      .join("text")
      .text(d => d.pos)
      .attr("x", (d, index) => (this.tokenSpace * index + d.sumX))
      .attr("y", 52 + maxLevel*15);

    // svg.append("g")
    //   .selectAll("path")
    //   .data(this.links)
    //   .join("path")
    //   .attr("d", d => this.calcArc(d))
    //   .attr("stroke", "#1e9989")
    //   .attr("id", (d, index) => `link-${index}`)
    //   .attr("fill", "transparent")
    //   .exit()

    // svg.append("g")
    //   .attr("class", "dep-text")
    //   .selectAll("text")
    //   .data(this.links)
    //   .join("text")
    //   .attr("x", d => `${d.offset}px`)
    //   .attr("baseline-shift", "-7px")
    //   .append("textPath")
    //     .attr("fill", "#1e9989")
    //     .attr("xlink:href", (d, index) => `#link-${index}`)
    //     // .attr("startOffset", "-50%")
    //     .text(d => d.label)

    let links = svg.append("g")
      .attr("class", "links")
      .selectAll(".deprel-link")
      .data(this.links)
      .enter()
      .append("g")
      .attr("class", d => `link-type-${d.label}`)

    links.append("line")
          .attr("x1", d => this.calcLine(d)[0] + 4)
          .attr("x2", d => this.calcLine(d)[1] - 4)
          .attr("y1", d => (maxLevel*15 - d.level*15))
          .attr("y2", d => (maxLevel*15 - d.level*15))
          .attr("class", "link-line")
    links.append("line")
          .attr("x1", d => this.calcLine(d)[0] + 4)
          .attr("x2", d => this.calcLine(d)[0])
          .attr("y1", d => (maxLevel*15 - d.level*15))
          .attr("y2", d => (maxLevel*15 - d.level*15) + 7)
          .attr("class", "link-line")
          .attr("marker-end", d => this.calcLine(d)[3] == "start" ? "url(#link-pointer)" : "")
    links.append("line")
          .attr("x1", d => this.calcLine(d)[1] - 4)
          .attr("x2", d => this.calcLine(d)[1])
          .attr("y1", d => (maxLevel*15 - d.level*15))
          .attr("y2", d => (maxLevel*15 - d.level*15) + 7)
          .attr("class", "link-line")
          .attr("marker-end", d => this.calcLine(d)[3] == "end" ? "url(#link-pointer)" : "")
    links.append("text")
          .attr("x", d => (this.calcLine(d)[0] + this.calcLine(d)[1])/2)
          .attr("y", d => (maxLevel*15 - 5 - d.level*15))
          .attr("class", "link-text")
          .attr("text-anchor", "middle")
          .attr("dominant-baseline", "middle")
          .text(d => d.label)
  },
}
</script>
