<template>
  <div ref="image" class="image-container">
    <img :src="src" />
    <div
      v-for="(xyc, n) in highlights"
      class="highlight-box"
      :key="`div-highlight-${n}`"
      :style="[
        ['left',xyc[0]-1],
        ['top',xyc[1]-1],
        ['width',(xyc[2]-xyc[0])+2],
        ['height',(xyc[3]-xyc[1])+2],
        ['border-color',xyc[4]]
      ].map(([p,v],n)=>p+': '+v+(n<4?'px':'')).join('; ')"
    >
    </div>
  </div>
</template>

<script>


export default {
  name: "ImageViewer",
  data() {
  },
  props: ["src", "boxes"],
  methods: {
    method() {
      
    }
  },
  computed: {
    highlights() {
      let highlights = [];
      if (this.boxes && this.boxes instanceof Array)
        highlights = [...this.boxes];
      return highlights;
    },
  },
  mounted() {
    // pass
  },
  beforeUnmount() {
    // pass
  }
};
</script>

<style>
.image-container {
  position: relative;
}
.highlight-box {
  z-index: 99;
  position: absolute;
  border: solid 2px black;
}
</style>
