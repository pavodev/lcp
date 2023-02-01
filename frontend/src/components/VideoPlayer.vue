<template>
  <div class="video-border">
    <video ref="videoPlayer" class="video-js"></video>
  </div>
</template>

<script>
import videojs from 'video.js'
import 'video.js/dist/video-js.css'
import abLoopPlugin from 'videojs-abloop'
import config from '@/config'
import '@/components/videojs.framebyframe.css'

abLoopPlugin(window, videojs)

var VjsButton = videojs.getComponent('Button')
var FBFButton = videojs.extend(VjsButton, {
  constructor: function (player, options) {
    VjsButton.call(this, player, options)
    this.player = player
    this.frameTime = 1 / options.fps
    this.step_size = options.value
    this.on('click', this.onClick)
  },
  onClick: function () {
    // Start by pausing the player
    this.player.pause()
    // Calculate movement distance
    var dist = this.frameTime * this.step_size
    this.player.currentTime(this.player.currentTime() + dist)
  }
})

function framebyframe (options) {
  var player = this

  player.ready(function () {
    options.steps.forEach(function (opt) {
      var b = player.controlBar.addChild(
        new FBFButton(player, {
          el: videojs.dom.createEl(
            'button',
            {
              className: 'vjs-res-button vjs-control',
              // innerHTML: '<div class="vjs-control-content" style="font-size: 11px; line-height: 28px;"><span class="vjs-fbf">' + opt.text + '</span></div>'
              innerHTML: '<div class="vjs-control-content"><span class="vjs-fbf">' + opt.text + '</span></div>'
            },
            {
              role: 'button'
            }
          ),
          value: opt.step,
          fps: options.fps
        }),
        {},
        opt.index
      )
      player.controlBar.el().insertBefore(b.el(), player.controlBar.fullscreenToggle.el())
    })
  })
}

// Cross-compatibility for Video.js 5 and 6.
var registerPlugin = videojs.registerPlugin || videojs.plugin

registerPlugin('framebyframe', framebyframe)


export default {
  props: ['corpora'],
  data () {
    return {
      player: null,
      videoOptions: {
        plugins: {
          abLoopPlugin: {
            'enabled': true
          },
          framebyframe: {
            fps: 30,
            steps: [
              { text: '<', step: -1 },
              { text: '>', step: 1 }
            ]
          }
        },
        autoplay: false,
        controls: true,
        fluid: true,
        playbackRates: [0.5, 1, 1.5, 2],
        sources: [
          {
            src: config.apiUrl + '/video?corpora=' + Array.from(this.$props.corpora).join(','),
            type: 'video/mp4'
          }
        ]
      }
    }
  },
  methods: {
  },
  watch: {
    corpora (newCorpora, oldCorpora) {
      const newSrc = config.apiUrl + '/video?corpora=' + Array.from(newCorpora).join(',')
      this.videoOptions.sources.src = newSrc
      // this.player.src = newSrc
      this.$refs.videoPlayer.src = newSrc
      this.player.load()
      this.player.play()
    }
  },
  mounted () {
    this.player = videojs(this.$refs.videoPlayer, this.videoOptions, () => {})
  },
  beforeDestroy () {
    if (this.player) {
      this.player.dispose()
    }
  }
}
</script>

<style scoped>
.video-border {
  width: calc(100% - 10px);
  margin-top: 10px;
}
</style>