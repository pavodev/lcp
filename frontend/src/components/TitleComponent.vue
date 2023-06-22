<template>
  <div id="title-view">
    <h2 v-html="title"></h2>
    <!-- <div class="container text-start">
      <div class="row">
        <div class="col">

        </div>
      </div>
    </div> -->
  </div>
</template>

<script>
export default {
  name: "TitleView",
  props: ["title"],
}
</script>
