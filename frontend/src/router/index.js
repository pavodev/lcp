import { createRouter, createWebHistory } from "vue-router";
import config from "@/config";
import HomeViewBase from "../views/HomeView.vue";
import HomeViewLCP from "../views/lcp/HomeView.vue";

// import { useUserStore } from "@/stores/userStore";

const routes = [
  {
    path: "/",
    name: "home",
    component: config.appType == "lcp" ? HomeViewLCP : HomeViewBase,
    meta: {
      requiresAuth: false,
    },
  },
  {
    name: "query",
    path: "/query",
    alias: "/query/:id/:name/",
    component: () =>
      import("../views/QueryView.vue"),
    meta: {
      requiresAuth: true,
    },
  },
  {
    name: "user",
    path: "/user",
    // alias: "/user/:id/",
    component: () =>
      import("../views/UserView.vue"),
    meta: {
      requiresAuth: true,
    },
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

// router.beforeEach((to, from, next) => {
//   if (to.matched.some((record) => record.meta.requiresAuth)) {
//     // console.log("A", useUserStore().dataFetched, Object.keys(useUserStore().userData.user).length == 0)
//     if (useUserStore().dataFetched && Object.keys(useUserStore().userData.user).length == 0) {
//       window.location.replace("/login");
//       // console.log("Redirect")
//     }
//     else {
//       next()
//     }
//   }
//   else {
//     next()
//   }
// })

export default router;
