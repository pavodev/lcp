<template>
  <div id="analysis-view" v-if="data">
    <Pie :data="chartData" :options="chartOptions" />
  </div>
</template>

<style>
</style>

<script>
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { Pie } from 'vue-chartjs'

ChartJS.register(ArcElement, Tooltip, Legend)

export default {
  name: "ResultsAnalysisView",
  props: ["data", "attributes"],
  data() {
    // console.log("PIE", this.data, this.attributes)
    let results = this.attributes.slice(0, -1)
    return {
      chartData: {
        labels: results,
        datasets: [
          {
            backgroundColor: ['#41B883', '#E46651', '#00D8FF', '#DD1B16'].slice(0, results.length),
            data: [10, 40, 50, 100].slice(0, results.length)
          }
        ]
      },
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false
      },
    }
  },
  methods: {
  },
  components: {
    Pie,
  },
};
</script>
