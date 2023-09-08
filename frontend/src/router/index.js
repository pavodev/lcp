import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";

import { useUserStore } from "@/stores/userStore";

const routes = [
  {
    path: "/",
    name: "home",
    component: HomeView,
    meta: {
      requiresAuth: false,
    },
  },
  {
    name: "player",
    path: "/player",
    alias: "/player/:id/:name/",
    // route level code-splitting
    // this generates a separate chunk (about.[hash].js) for this route
    // which is lazy-loaded when the route is visited.
    component: () =>
      import(/* webpackChunkName: "about" */ "../views/PlayerView.vue"),
    meta: {
      requiresAuth: true,
    },
  },
  {
    name: "query",
    path: "/query",
    alias: "/query/:id/:name/",
    component: () =>
      import(/* webpackChunkName: "about" */ "../views/QueryView.vue"),
    meta: {
      requiresAuth: true,
    },
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

router.beforeEach((to, from, next) => {
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    // console.log("A", useUserStore().dataFetched, Object.keys(useUserStore().userData.user).length == 0)
    if (useUserStore().dataFetched && Object.keys(useUserStore().userData.user).length == 0) {
      window.location.replace("/login");
      // console.log("Redirect")
    }
    else {
      next()
    }
  }
  else {
    next()
  }
})

export default router;
