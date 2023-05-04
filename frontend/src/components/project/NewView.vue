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

          <div class="mb-3">
            <label for="url" class="form-label">URL</label>
            <input
              type="text"
              class="form-control"
              v-model="model.url"
              id="url"
              aria-describedby="urlHelp"
            />
          </div>
        </div>
        <div class="col-6">
          <div class="mb-3">
            <label for="content" class="form-label">Institution</label>
            <input type="text" class="form-control" disabled v-model="model.institution" id="institution" />
          </div>
        </div>
        <div class="col-6">
          <div class="mb-3">
            <label for="content" class="form-label">Organizational unit (e.g. department)</label>
            <input type="text" class="form-control" v-model="model.unit" id="unit" />
            <div id="urlHelp" v-if="unitState == false" class="form-text text-danger">
              Organizational unit is mandatory (min. length is two letters).
            </div>
          </div>
        </div>
        <div class="col-6">
          <div class="mb-3">
            <label for="content" class="form-label">Start date</label>
            <DatePicker
              v-model:value="model.startDate"
              id="startDate"
              :clearable="true"
              class="d-block"
            />
            <div id="urlHelp" v-if="startDateState == false" class="form-text text-danger">
              Start date is mandatory.
            </div>
          </div>
        </div>
        <div class="col-6">
          <div class="mb-3">
            <label for="content" class="form-label">End date</label>
            <DatePicker
              v-model:value="model.finishDate"
              id="finishDate"
              :disabled-date="disabledBeforeToday"
              :clearable="true"
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
// import { mapState } from 'vuex';
// import TempStore from '@/store/tempstore.js';
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";

export default {
  name: 'ProjectNewView',
  data() {
    return {
      model: {
        title: '',
        url: '',
        institution: '',
        unit: '',
        startDate: null,
        finishDate: null,
        description: '',
      },
      titleState: null,
      unitState: null,
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
    _checkURL(url) {
      try {
        url = new URL(url);
      } catch (_) {
        return false;
      }

      return url.protocol === 'http:' || url.protocol === 'https:';
    },
    validate() {
      this.titleState = this.model.title.trim().replace(/\s\s+/g, ' ').length >= 7;
      this.unitState = this.model.unit.length >= 2;
      this.startDateState = this.model.startDate ? true : false;
      this.finishDateState = this.model.finishDate ? true : false;

      let validated =
        this.titleState &&
        this.unitState &&
        this.startDateState &&
        this.finishDateState;
      this.$emit('updated', validated, this.model);
      return validated;
    },
  },
  mounted() {
    if (this.userData && this.userData.user){
      this.model.institution = this.userData.user.homeOrganization;
    }
  },
  updated() {
    this.validate();
  },
};
</script>
