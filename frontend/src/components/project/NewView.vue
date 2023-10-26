<template>
  <div class="project-new">
    <div class="container">
      <div class="row">
        <div class="col-12">
          <div class="mb-3">
            <label for="url" class="form-label">Title</label>
            <input
              type="text"
              class="form-control"
              v-model="model.title"
              id="title"
              aria-describedby="titleHelp"
              maxlength="50"
            />
            <div id="titleHelp" v-if="titleState == false" class="form-text text-danger">
              Title is mandatory (min. length is seven letters).<br>
              Title will be manually checked. Try to be concise and informative.
            </div>
          </div>
        </div>
        <div class="col-4">
          <div class="mb-3">
            <label for="content" class="form-label">Start date</label>
            <DatePicker
              v-model:value="model.startDate"
              id="startDate"
              class="d-block"
            />
            <div id="urlHelp" v-if="startDateState == false" class="form-text text-danger">
              Start date is mandatory.
            </div>
          </div>
        </div>
        <div class="col-4">
          <div class="mb-3">
            <label for="content" class="form-label">End date</label>
            <DatePicker
              v-model:value="model.finishDate"
              id="finishDate"
              :disabled-date="disabledBeforeToday"
              class="d-block"
            />
            <div id="urlHelp" v-if="finishDateState == false" class="form-text text-danger">
              End date is mandatory.
            </div>
          </div>
        </div>
        <div class="col-12">
          <div class="mb-3">
            <label for="description" class="form-label">Purpose</label>
            <textarea
              class="form-control"
              placeholder="Please describe the purpose of your project"
              v-model="model.description"
              id="description"
              style="height: 100px"
            ></textarea>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>

<script>
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";

export default {
  name: 'ProjectNewView',
  data() {
    const today = new Date();
    let oneYear = new Date();
    oneYear.setYear(today.getFullYear() + 1);
    return {
      model: {
        title: '',
        startDate: today,
        finishDate: oneYear,
        description: '',
      },
      titleState: null,
      startDateState: null,
      finishDateState: null,
    };
  },
  computed: {
    ...mapState(useUserStore, ["userData"]),
  },
  methods: {
    disabledBeforeToday(date) {
      return (
        date < this.model.startDate ||
        date > new Date(new Date().getTime() + 4 * 365 * 24 * 3600 * 1000)
      );
    },
    validate() {
      this.titleState = this.model.title.trim().replace(/\s\s+/g, ' ').length >= 7;
      this.startDateState = this.model.startDate ? true : false;
      this.finishDateState = this.model.finishDate ? true : false;

      let validated =
        this.titleState &&
        this.startDateState &&
        this.finishDateState;
      this.$emit('updated', validated, this.model);
      return validated;
    },
  },
  updated() {
    this.validate();
  },
};
</script>
