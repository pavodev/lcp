<template>
  <svg xmlns="http://www.w3.org/2000/svg" 
       :width="width+'px'"
       :height="height+'px'"
       @mousemove="drag($event)"
       @mouseup="drop()"
       ref="corpusSVG"
       v-if="bounds.minX">
    
    <line v-for="link in graph.links"
          :key="`line-${link.source.index}`"
          :x1="coords[link.source.index].x"
          :y1="coords[link.source.index].y"
          :x2="coords[link.target.index].x"
          :y2="coords[link.target.index].y"
          stroke="black" stroke-width="2"/>
    
    <g v-for="(node, i) in graph.nodes"
            :key="`group-${i}`">
      <rect
            :x="getX(coords[i].x)"
            :y="getY(coords[i].y)"
            :width="rectWidth"
            :height="rectHeight"
            :rx="15" :fill="colors[Math.ceil(Math.sqrt(node.index))]"
            stroke="black" stroke-width="1"
            @mousedown="currentMove = {x: $event.screenX, y: $event.screenY, node: node}"/>

      <text
            :x="getX(coords[i].x) + 10"
            :y="getY(coords[i].y) + 36" 
            v-html="node.text"/>
    </g>
    
  </svg>
</template>

<script>
import * as d3 from 'd3'

export default {
  name: "CorpusGraphView",
  data() {
    return {
      graph: {
        nodes: [
          {index: 0, x: 50, y: 0, text: "Corpus", fixed: true, depth: 0},
          {index: 1, x: 0, y: 0, text: "Document", depth: 1},
          {index: 2, x: 0, y: 0, text: "Segment", depth: 2},
          {index: 3, x: 0, y: 0, text: "NamedEntity", depth: 1},
          {index: 4, x: 0, y: 0, text: "Token", depth: 3},
          {index: 5, x: 0, y: 0, text: "form", depth: 4},
          {index: 6, x: 0, y: 0, text: "lemma", depth: 4},
          {index: 7, x: 0, y: 0, text: "form", depth: 2},
        ],
        links: [
          {source: 0, target: 1},
          {source: 1, target: 2},
          {source: 2, target: 4},
          {source: 0, target: 3},
          {source: 3, target: 4},
          {source: 4, target: 5},
          {source: 4, target: 6},
          {source: 3, target: 7},
        ]
      },
      width: 100,
      height: 100,
      rectWidth: 100,
      rectHeight: 50,
      padding: 20,
      colors: ['#2196F3', '#E91E63', '#7E57C2', '#009688', '#00BCD4', '#EF6C00', '#4CAF50', '#FF9800', '#F44336', '#CDDC39', '#9C27B0'],
      simulation: null,
      currentMove: null
    };
  },
  props: ["corpus"],
  methods: {
    drag(e) {
      if (this.currentMove) {
        console.log(e);
        // this.currentMove.node.fx = this.currentMove.node.x - (this.currentMove.x - e.screenX) * (this.bounds.maxX - this.bounds.minX) / (this.width - 2 * this.padding)
        // this.currentMove.node.fy = this.currentMove.node.y -(this.currentMove.y - e.screenY) * (this.bounds.maxY - this.bounds.minY) / (this.height - 2 * this.padding)
        // this.currentMove.x = e.screenX
        // this.currentMove.y = e.screenY
      }
    },
    drop(){
      // delete this.currentMove.node.fx
      // delete this.currentMove.node.fy    
      // this.currentMove = null
      // this.simulation.alpha(1)
      // this.simulation.restart()
    },
    checkContainerHeight() {
      if (this.$refs.corpusSVG) {
        const {width, height} = this.$refs.corpusSVG.parentElement.getBoundingClientRect();
        if (width != this.width || height != this.height) {
          this.width = width;
          this.height = height;
        }
      }
      window.requestAnimationFrame(()=>this.checkContainerHeight());
    },
    getX(x) {
      return Math.min(Math.max(x - this.rectWidth/2, 0), this.width - this.rectWidth);
    },
    getY(y) {
      return Math.min(Math.max(y - this.rectHeight/2, 0), this.height - this.rectHeight);
    }
  },
  computed: {
    bounds() {
      return {
        minX: Math.min(...this.graph.nodes.map(n => n.x)),
        maxX: Math.max(...this.graph.nodes.map(n => n.x)),
        minY: Math.min(...this.graph.nodes.map(n => n.y)),
        maxY: Math.max(...this.graph.nodes.map(n => n.y))
      }
    },
    coords() {
      return this.graph.nodes.map(node => {
        return {
          x: this.padding + (node.x - this.bounds.minX) * (this.width - 2*this.padding) / (this.bounds.maxX - this.bounds.minX),
          y: this.padding + (node.y - this.bounds.minY) * (this.height - 2*this.padding) / (this.bounds.maxY - this.bounds.minY)
        }
      })
    }
  },
  mounted() {
    this.simulation = d3.forceSimulation(this.graph.nodes, this.rectWidth)
        .force('charge', d3.forceManyBody().strength(() => -100))
        .force('link', d3.forceLink(this.graph.links))
        .force('x', d3.forceX())
        .force('y', d3.forceY().y(function(d) {
          return d.depth * 30;
        }));
    // find a better solution than timeout
    this.checkContainerHeight();
  },
  beforeUnmount() {
  }
};
</script>
  
<style>

</style>