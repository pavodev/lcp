<template>
  <div class="about">
    <!-- <h1>This is a player page</h1> -->

    <!-- <VideoPlayer :corpora="['asdads']" /> -->

    <video width="320" height="240" ref="videoPlayer1">
      <source src="http://localhost:3000/video/e822e422-32e1-4635-a0c9-0366970affeb/video.mp4" type="video/mp4">
      Your browser does not support the video tag.
    </video>

    <video width="480" height="320" ref="videoPlayer2" @timeupdate="timeupdate">
      <source src="http://localhost:3000/video/e822e422-32e1-4635-a0c9-0366970affeb/24fps.mp4" type="video/mp4">
      Your browser does not support the video tag.
    </video>

    <video width="320" height="240" ref="videoPlayer3">
      <source src="http://localhost:3000/video/e822e422-32e1-4635-a0c9-0366970affeb/video.mp4" type="video/mp4">
      Your browser does not support the video tag.
    </video>

    <video width="240" height="160" ref="videoPlayer4">
      <source src="http://localhost:3000/video/e822e422-32e1-4635-a0c9-0366970affeb/24fps.mp4" type="video/mp4">
      Your browser does not support the video tag.
    </video>

    <br>

    <a href="#" @click="playerPlay" class="btn btn-primary">Play</a>
    <a href="#" @click="playerStop" class="btn btn-primary ms-1">Stop</a>
    <a href="#" @click="playerVolumeUp" class="btn btn-primary ms-1">Vol +</a>
    <a href="#" @click="playerVolumeDown" class="btn btn-primary ms-1">Vol -</a>
    <!-- <a href="#" @click="playerSetTime" class="btn btn-primary ms-1">Set time (0:10)</a> -->
    <a href="#" @click="playerFrameUp" class="btn btn-primary ms-1">Frame +</a>
    <a href="#" @click="playerFrameDown" class="btn btn-primary ms-1">Frame -</a>
    <a href="#" @click="playerFrame100" class="btn btn-primary ms-1">Set Frame 100</a>
    <br>

    <div class="container mt-4">
      <div class="row">
        <div class="col12" style="position: relative;" @click="timelineClick">
          <div class="vertical-line" :style="'margin-left: ' + progress + '%'"></div>
          <div class="progress" style="height: 10px;" ref="timeline">
            <div class="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
          </div>
          <div class="progress" style="height: 10px;">
            <div class="progress-bar bg-info" role="progressbar" style="width: 35%" aria-valuenow="25" aria-valuemin="0" aria-valuemax="100"></div>
          </div>
          <div class="progress" style="height: 10px;">
            <div class="progress-bar bg-danger" role="progressbar" style="width: 25%; margin-left: 20%" aria-valuenow="25" aria-valuemin="0" aria-valuemax="100"></div>
          </div>
          <div class="progress" style="height: 10px;">
            <div class="progress-bar bg-success" role="progressbar" style="width: 55%; margin-left: 40%" aria-valuenow="25" aria-valuemin="0" aria-valuemax="100"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// import VideoPlayer from "@/components/VideoPlayer";

export default {
  data(){
    return {
      progress: 0
    }
  },
  methods: {
    playerPlay(){
      this.$refs.videoPlayer1.play()
      this.$refs.videoPlayer2.play()
      this.$refs.videoPlayer3.play()
      this.$refs.videoPlayer4.play()
    },
    playerStop(){
      this.$refs.videoPlayer1.pause()
      this.$refs.videoPlayer2.pause()
      this.$refs.videoPlayer3.pause()
      this.$refs.videoPlayer4.pause()
    },
    playerVolumeUp(){
      let vol = this.$refs.videoPlayer2.volume
      vol = Math.min(1, vol + 0.05)
      this.$refs.videoPlayer2.volume = vol
      console.log("Vol", this.$refs.videoPlayer2.volume)
    },
    playerVolumeDown(){
      let vol = this.$refs.videoPlayer2.volume
      vol = Math.max(0, vol - 0.05)
      this.$refs.videoPlayer2.volume = vol
      console.log("Vol", this.$refs.videoPlayer2.volume)
    },
    playerFrameUp(){
      let currentFrame = this.$refs.videoPlayer2.currentTime.toFixed(5)*24
      console.log("CFU", currentFrame)
      let newTime = parseFloat((currentFrame + 1)/24.)
      console.log("UFG", currentFrame, newTime)
      this.$refs.videoPlayer1.currentTime = newTime
      this.$refs.videoPlayer2.currentTime = newTime
      this.$refs.videoPlayer3.currentTime = newTime
      this.$refs.videoPlayer4.currentTime = newTime
    },
    playerFrame100(){
      let value = (100./24.).toFixed(5)
      this.$refs.videoPlayer1.currentTime = value;
      this.$refs.videoPlayer2.currentTime = value;
      this.$refs.videoPlayer3.currentTime = value;
      this.$refs.videoPlayer4.currentTime = value;
    },
    playerFrameDown(){
      let currentFrame = this.$refs.videoPlayer2.currentTime.toFixed(5)*24
      console.log("CFD", currentFrame)
      let newTime = parseFloat((currentFrame - 1)/24.)
      console.log("DFG", currentFrame, newTime)
      this.$refs.videoPlayer1.currentTime = newTime
      this.$refs.videoPlayer2.currentTime = newTime
      this.$refs.videoPlayer3.currentTime = newTime
      this.$refs.videoPlayer4.currentTime = newTime
    },
    // playerSetTime(){
    //   this.$refs.videoPlayer1.currentTime = 10.56547
    //   this.$refs.videoPlayer2.currentTime = 10.56547
    //   this.$refs.videoPlayer3.currentTime = 10.56547
    // },
    timeupdate(){
      // let percent = this.$refs.videoPlayer2.currentTime / this.$refs.videoPlayer2.duration
      this.progress = (this.$refs.videoPlayer2.currentTime / this.$refs.videoPlayer2.duration) * 100
      // console.log("Current time", this.$refs.videoPlayer2.currentTime, this.$refs.videoPlayer2.duration, percent*100, this.progress)
    },
    timelineClick(event){
      let percent = parseFloat(event.clientX - this.$refs.timeline.getBoundingClientRect().left) / this.$refs.timeline.getBoundingClientRect().width
      let time = this.$refs.videoPlayer2.duration * percent
      this.$refs.videoPlayer1.currentTime = time
      this.$refs.videoPlayer2.currentTime = time
      this.$refs.videoPlayer3.currentTime = time
      this.$refs.videoPlayer4.currentTime = time
    }
  },
  mounted(){
    this.$refs.videoPlayer1.volume = 0
    this.$refs.videoPlayer2.volume = 1
    this.$refs.videoPlayer3.volume = 0
    this.$refs.videoPlayer4.volume = 0
  },
  // components: {
  //   VideoPlayer
  // }
}
</script>

<style scoped>
video {
  margin-right: 3px;
}
.vertical-line {
  position: absolute;
  width: 1px;
  height: 56px;
  margin-top: -10px;
  background-color: rgb(114, 114, 114);
}
.progress-bar {
  border-radius: 4px;
}
</style>
