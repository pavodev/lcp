<template>
  <div id="title-view">
    <div class="container mt-4 text-start">
      <div class="row">
        <div class="col">
          <h2 v-html="title"></h2>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "TitleView",
  props: ["title"],
}
</script>
