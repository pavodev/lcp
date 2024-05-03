<template>
  <footer>
    <img class="logo" src="../assets/logos/uzh.svg" alt="UZH">
    <hr>
    Copyright &copy; 2024 LiRI
  </footer>
</template>

<style scoped>
.logo {
  height: 60px;
}
footer {
  text-align: center;
  width: 100%;
  font-size: 12px;
  margin-top: 50px;
  padding: 30px 0 15px;
  color: #fff;
  background-color: #2a7f62;
}
hr {
  margin-top: 30px;
}
</style>

<script>
export default {
  name: "FooterView",
};
</script>
