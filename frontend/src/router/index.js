import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";

const routes = [
  {
    path: "/",
    name: "home",
    component: HomeView,
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
  },
  {
    name: "query",
    path: "/query",
    alias: "/query/:id/:name/",
    component: () =>
      import(/* webpackChunkName: "about" */ "../views/QueryView.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

export default router;
