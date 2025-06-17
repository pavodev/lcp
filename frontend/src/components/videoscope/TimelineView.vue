<template>
  <div>
    <!-- Desktop Timeline -->
    <div v-if="!isMobile">
      <div class="button-container">
        <button class="btn btn-primary btn-sm me-1" :disabled="zoomValue <= 1" @click="zoomOut">
          <FontAwesomeIcon :icon="['fas', 'magnifying-glass-minus']" class="me-1" />
          {{ $t('common-zoom-out') }}
        </button>
        <input type="range" min="1" :max="MAX_ZOOM_LEVEL" class="zoom-slider" v-model="zoomValue" step="1" />
        <button class="btn btn-primary btn-sm me-1" :disabled="zoomValue >= MAX_ZOOM_LEVEL" @click="zoomIn">
          <FontAwesomeIcon :icon="['fas', 'magnifying-glass-plus']" class="me-1" />
          {{ $t('common-zoom-in') }}
        </button>
        <button class="btn btn-primary btn-sm me-1" @click="resetZoom">
          <FontAwesomeIcon :icon="['fas', 'rotate-left']" class="me-1" />
          {{ $t('common-zoom-reset-default') }}
        </button>
        <button class="btn btn-primary btn-sm me-1" @click="fitZoom">
          <FontAwesomeIcon :icon="['fas', 'arrows-left-right-to-line']" class="me-1" />
          {{ $t('common-zoom-fit-content') }}
        </button>
      </div>
      <svg id="timeline-svg"></svg>
    </div>

    <!-- Mobile Timeline Button -->
    <div class="text-center" v-else>
      <button class="btn btn-primary btn-sm me-1" @click="showTimelineModal">
        <FontAwesomeIcon :icon="['fas', 'chart-gantt']" class="me-1" />
        {{ $t('common-show-timeline') }}
      </button>
    </div>

    <!-- Timeline Modal (Mobile Only) -->
    <div v-if="isModalOpen && isMobile" class="timeline-modal">
      <div class="modal-content">
        <div class="modal-header">
          <h5>{{ $t('common-timeline') }}</h5>
          <button class="close-button" @click="closeTimelineModal">
            <FontAwesomeIcon :icon="['fas', 'times']" />
          </button>
        </div>
        
        <!-- Mobile Rotation Instructions -->
        <div v-if="!isLandscape" class="rotation-instructions">
          <FontAwesomeIcon :icon="['fas', 'mobile-screen-button']" class="rotation-icon" />
          <p class="p-0 m-0">{{ $t('common-rotate-device') }}</p>
        </div>

        <div v-if="isLandscape" class="timeline-container">
          <div class="button-container">
            <button class="btn btn-primary btn-sm me-1" :disabled="zoomValue <= 1" @click="zoomOut">
              <FontAwesomeIcon :icon="['fas', 'magnifying-glass-minus']" class="me-1" />
              {{ $t('common-zoom-out') }}
            </button>
            <input type="range" min="1" :max="MAX_ZOOM_LEVEL" class="zoom-slider" v-model="zoomValue" step="1" />
            <button class="btn btn-primary btn-sm me-1" :disabled="zoomValue >= MAX_ZOOM_LEVEL" @click="zoomIn">
              <FontAwesomeIcon :icon="['fas', 'magnifying-glass-plus']" class="me-1" />
              {{ $t('common-zoom-in') }}
            </button>
            <button class="btn btn-primary btn-sm me-1" @click="resetZoom">
              <FontAwesomeIcon :icon="['fas', 'rotate-left']" class="me-1" />
              {{ $t('common-zoom-reset-default') }}
            </button>
            <button class="btn btn-primary btn-sm me-1" @click="fitZoom">
              <FontAwesomeIcon :icon="['fas', 'arrows-left-right-to-line']" class="me-1" />
              {{ $t('common-zoom-fit-content') }}
            </button>
          </div>
          <div class="timeline-wrapper">
            <svg id="timeline-svg-mobile"></svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-modal {
  position: fixed;
  top: 56px; /* Height of the navigation bar */
  left: 0;
  width: 100%;
  max-width: 100vw;
  height: calc(100% - 56px); /* Subtract navigation bar height */
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  touch-action: none;
}

.modal-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  width: 100%;
  height: 100%;
  max-width: none;
  max-height: none;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  touch-action: none;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  position: sticky;
  top: 0;
  background-color: white;
  z-index: 1;
  padding: 10px 0;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 5px;
}

.rotation-instructions {
  display: none;
  text-align: center;
  margin: 20px 0;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.rotation-icon {
  font-size: 2rem;
  margin-bottom: 10px;
  animation: rotate 2s infinite;
}

.timeline-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.timeline-wrapper {
  flex: 1;
  overflow: auto;
  position: relative;
  width: 100%;
  height: 100%;
  touch-action: none; /* Prevent default touch actions */
}

.button-container {
  margin-left: 178px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 10px 0;
}

@media (max-width: 768px) {
  .rotation-instructions {
    display: block;
  }

  .button-container {
    margin-left: 0;
    justify-content: center;
  }

  .modal-content {
    padding: 10px;
    flex-direction: column;
  }

  .timeline-wrapper {
    width: 100%;
    height: 100%;
  }

  #timeline-svg-mobile {
    width: 100%;
    height: 100%;
  }
}

/* Add styles for landscape orientation */
@media (orientation: landscape) and (max-width: 768px) {
  .rotation-instructions {
    display: none;
  }

  .modal-content {
    flex-direction: column;
    padding: 10px;
  }

  .timeline-container {
    flex-direction: row;
    height: 100%;
  }

  .button-container {
    flex-direction: row;
    margin-right: 10px;
    margin-left: 0;
    padding: 5px;
  }

  .timeline-wrapper {
    flex: 1;
    height: 100%;
    min-height: 0;
  }

  #timeline-svg-mobile {
    width: 100%;
    height: 100%;
    min-height: 0;
  }
}

@keyframes rotate {
  0% { transform: rotate(0deg); }
  25% { transform: rotate(-90deg); }
  75% { transform: rotate(-90deg); }
  100% { transform: rotate(0deg); }
}

/* #timeline-svg {
    margin: 0 10px;
  } */
.button-container {
  margin-left: 178px;
}

/* .zoom-slider {
    margin-top: 5px;
  } */
/*
  .zoom-button {
    margin-right: 5px;
  } */

/* .slider-container {
    margin-top: 10px;
  } */

*>>>.tooltip-rect {
  fill: #fffffff0;
  stroke: #e6e6e6;
  stroke-width: 1px;
}

svg#timeline-svg {
  cursor: pointer;
  color: #2c3e50;
  font-size: 12px;
}

.mouse-text {
  background-color: #2c3e50;
}
</style>

<script>
import * as d3 from 'd3'

import Utils from "@/utils.js";

// Global variables
let svg = null;
let zoom;
let linearScale = null;
// eslint-disable-next-line
let playerState = false;
let hoveringAnnotation = null;
const padding = 180;
// const width = document.body.clientWidth - 20;
const paddingBeforeTimeline = 40;
const MAX_ZOOM_LEVEL = 100
const DEFAULT_ZOOM_LEVEL = 20;

export default {
  name: "TimelineView",
  props: ["data", "playerIsPlaying", "playerCurrentTime", "mediaDuration", "hoveredResult"],
  data() {
    return {
      defaultCurrentTime: this.playerCurrentTime,
      currentTime: 0,
      zoomValue: 1,
      MAX_ZOOM_LEVEL: MAX_ZOOM_LEVEL,
      isModalOpen: false,
      isMobile: false,
      isLandscape: false,
      svgWidth: 0
    }
  },
  watch: {
    hoveredResult() {
      console.log("hoveredResult", this.hoveredResult);
      if (this.hoveredResult && this.hoveredResult instanceof Array && this.hoveredResult.length > 2)
        console.log("frame range of hovered line", [...this.hoveredResult[2]]);
    },
    playerIsPlaying() {
      playerState = this.playerIsPlaying;
      // console.log("playerState", playerState);
    },
    playerCurrentTime() {
      if (this.isModalOpen && this.isLandscape) {
        // For mobile modal, we need to ensure the SVG is ready
        this.$nextTick(() => {
          this.updateCurrentPosition(this.playerCurrentTime);
        });
      } else {
        this.updateCurrentPosition(this.playerCurrentTime);
      }
    },
    zoomValue() {
      const transform = d3.zoomTransform(svg.node());
      const currentScale = transform.k;
      const scaleRatio = this.zoomValue / currentScale;
      let xPosition = 0;

      if (!this.playerIsPlaying) {
        // Zoom relative to the position of the vertical line
        const verticalLine = svg.selectAll(".vertical-line");
        xPosition = verticalLine.attr("x1");
      } else {
        // Zoom relative to the center of the timeline
        const svgBounds = svg.node().getBoundingClientRect();
        xPosition = (svgBounds.width / 2 - transform.x) / currentScale;
      }

      // Apply the zoom while keeping the center in place
      svg.transition().call(zoom.scaleBy, scaleRatio, [xPosition, 0]);
    },
  },
  methods: {
    resetZoom() {
      this.zoomValue = DEFAULT_ZOOM_LEVEL;
    },
    fitZoom() {
      this.zoomValue = 1;
    },
    zoomIn() {
      this.zoomValue = Math.min(parseFloat(this.zoomValue) + 1, MAX_ZOOM_LEVEL);
    },
    zoomOut() {
      this.zoomValue = Math.max(parseFloat(this.zoomValue) - 1, 1);
    },
    updateCurrentPosition(time) {
      this.currentTime = time;
      if (!svg) return;
      
      const transform = d3.zoomTransform(svg.node());
      const newXScale = transform.rescaleX(linearScale);
      const xPosition = newXScale(this.currentTime);
      
      if (!isNaN(xPosition)) {
        this.updateVerticalLine(xPosition);
        // Only center if we're not playing, to avoid jumping during playback
        if (!this.playerIsPlaying) {
          this.center();
        }
      }
    },
    updateVerticalLine(xPosition) {
      if (!svg) return;
      
      const verticalLine = svg.selectAll(".vertical-line");
      const transform = d3.zoomTransform(svg.node());
      const newXScale = transform.rescaleX(linearScale);
      let [domainStart, domainEnd] = newXScale.domain();
      
      if (isNaN(domainStart) || isNaN(domainEnd)) return;
      
      domainStart = Math.max(0, domainStart.toFixed(3));
      const inDomain = (this.currentTime >= domainStart && this.currentTime <= domainEnd);

      verticalLine
        .attr("x1", xPosition)
        .attr("x2", xPosition)
        .attr("opacity", inDomain ? 1 : 0);

      if (this.currentTime > domainEnd) {
        if (playerState) {
          this.moveRight();
        }
      }
    },
    center() {
      // Get the current transform and the current SVG dimensions.
  const currentTransform = d3.zoomTransform(svg.node());
  const svgBounds = svg.node().getBoundingClientRect();
  const svgWidth = svgBounds.width; // use the current rendered width

  // Create a scale based on the current transform.
  const newXScale = currentTransform.rescaleX(linearScale);

  // Compute the pixel position (under the current transform) for the current time.
  const currentX = newXScale(this.currentTime);

  // Compute the visible area in pixels.
  // (Assuming your clip area starts at "padding" and extends to (svgWidth - paddingBeforeTimeline))
  const visibleWidth = svgWidth - padding - paddingBeforeTimeline;
  const centerPixel = padding + visibleWidth / 2;

  // Compute how much (in pixels) we want to shift the timeline so that currentX becomes centered.
  let dx = centerPixel - currentX;
  let desiredX = currentTransform.x + dx;

  // --- Left Boundary Clamp ---
  // Under your base linearScale, data value 0 maps to "padding".
  // With a transform, the left edge appears at: currentTransform.x + currentTransform.k * padding.
  // We want to keep that ≤ padding.
  // Rearranging gives:
  //    currentTransform.x ≤ padding - currentTransform.k * padding = padding * (1 - currentTransform.k)
  const minAllowedX = padding * (1 - currentTransform.k);
  desiredX = Math.min(desiredX, minAllowedX);

  // --- Right Boundary Clamp ---
  // The right edge of your content (data value = this.mediaDuration) maps to:
  //   linearScale(this.mediaDuration)
  // With the transform it's at: currentTransform.x + currentTransform.k * linearScale(this.mediaDuration)
  // We want that to be exactly at the right visible boundary:
  //   svgWidth - paddingBeforeTimeline
  // Solving for the x translation gives:
  //   desiredX = (svgWidth - paddingBeforeTimeline) - currentTransform.k * linearScale(this.mediaDuration)
  const maxAllowedX = (svgWidth - paddingBeforeTimeline) - currentTransform.k * linearScale(this.mediaDuration);
  desiredX = Math.max(desiredX, maxAllowedX);

  // Build the new transform with the clamped translation.
  const newTransform = d3.zoomIdentity
    .translate(desiredX, currentTransform.y)
    .scale(currentTransform.k);

  // Apply the new transform with a smooth transition.
  svg.transition().call(zoom.transform, newTransform);
    },
    moveLeft() {
      console.log('MOVING LEFT');
      const currentTransform = d3.zoomTransform(svg.node());
      const newXScale = currentTransform.rescaleX(linearScale);

      // Get the width of the visible range
      const visibleWidth = newXScale.range()[1] - newXScale.range()[0];

      // Get the width of the entire data range
      const totalWidth = newXScale.domain()[1] - newXScale.domain()[0];

      // Calculate the amount to move the graph to the right (one width)
      const moveAmount = totalWidth - visibleWidth;

      // Calculate the new translation along the x-axis
      const newTx = currentTransform.x - moveAmount;

      // Update the zoom transform with the new translation
      svg.call(zoom.transform, d3.zoomIdentity.translate(newTx, currentTransform.y).scale(currentTransform.k));
    },
    moveRight() {
      console.log('MOVING RIGHT');
      const currentTransform = d3.zoomTransform(svg.node());
      const newXScale = currentTransform.rescaleX(linearScale);

      // Get the width of the visible range
      const visibleWidth = newXScale.range()[1] - newXScale.range()[0];

      // Get the width of the entire data range
      const totalWidth = newXScale.domain()[1] - newXScale.domain()[0];

      // Calculate the amount to move the graph to the right (one width)
      const moveAmount = totalWidth - visibleWidth;

      // Calculate the new translation along the x-axis
      const newTx = currentTransform.x + moveAmount;

      // Update the zoom transform with the new translation
      svg.call(zoom.transform, d3.zoomIdentity.translate(newTx, currentTransform.y).scale(currentTransform.k));
    },
    showTimelineModal() {
      this.isModalOpen = true;
      this.checkMobile();
      // Wait for the modal to be mounted and visible
      this.$nextTick(() => {
        // Only initialize if we're in landscape mode
        if (this.isLandscape) {
          this.initializeTimeline('timeline-svg-mobile');
          // Use setTimeout to ensure SVG is fully initialized and transformed
          setTimeout(() => {
            this.updateCurrentPosition(this.playerCurrentTime);
            this.center();
          }, 100);
        }
      });
    },
    closeTimelineModal() {
      this.isModalOpen = false;
    },
    checkMobile() {
      // Check if the device is mobile based on user agent
      const isMobileDevice = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
      this.isMobile = isMobileDevice;
      
      // Check orientation
      this.isLandscape = window.innerWidth > window.innerHeight;
    },
    handleResize() {
      // Only update mobile status if the device type has changed
      this.checkMobile();
      
      // If we're in the modal and the device is still mobile, keep it open
      if (this.isModalOpen && this.isMobile) {
        // Reinitialize the timeline if needed
        if (this.isLandscape) {
          this.$nextTick(() => {
            const svgElement = document.getElementById('timeline-svg-mobile');
            if (svgElement && svgElement.parentElement) {
              this.initializeTimeline('timeline-svg-mobile');
            }
          });
        }
      }
    },
    initializeTimeline(svgId = 'timeline-svg') {
      // Check if the SVG element exists and has a parent
      const svgElement = document.getElementById(svgId);
      if (!svgElement || !svgElement.parentElement) {
        console.warn(`SVG element ${svgId} not found or not mounted`);
        return;
      }

      // https://waldyrious.net/viridis-palette-generator/
      const barColors = [
        "#1fa187ff", "#46327eff", "#4ac16dff", "#277f8eff", "#440154ff", "#fde725ff", "#365c8dff", "#a0da39ff"
      ];

      // Clear any existing elements
      d3.select(`#${svgId}`).selectAll("*").remove();

      // Set up the SVG container
      svg = d3.select(`#${svgId}`);
      
      // Get the actual width of the container
      const containerWidth = svgId === 'timeline-svg-mobile' 
        ? svgElement.parentElement.clientWidth 
        : document.body.clientWidth - 20;
      
      // Debug logging for iOS
      console.log('Timeline initialization:', {
        svgId,
        containerWidth,
        parentWidth: svgElement.parentElement?.clientWidth,
        bodyWidth: document.body.clientWidth,
        mediaDuration: this.mediaDuration
      });
      
      // Ensure we have valid dimensions
      if (containerWidth <= 0 || !this.mediaDuration || this.mediaDuration <= 0) {
        console.warn('Invalid dimensions for timeline initialization:', {
          containerWidth,
          mediaDuration: this.mediaDuration
        });
        return;
      }
      
      this.svgWidth = containerWidth;

      // Create the scaleLinear with the correct width
      linearScale = d3.scaleLinear()
        .domain([0, this.mediaDuration || 0])
        .range([padding, containerWidth - paddingBeforeTimeline]);

      let data = [...this.data];

      // Add names to the chart
      let heightStart = {}
      let totalHeight = 50; // Height before the first row
      svg
        .selectAll(".name")
        .data(data)
        .enter()
        .append("text")
        .attr("class", "name")
        .attr("x", d => 10 + 20 * (d.level ? d.level : 0))
        .attr("y", (d, i) => {
          let height = totalHeight + 10
          totalHeight += d.heightLines * 15 + 10
          heightStart[i] = height
          return height + 13
        })
        .text((d) => d.name);

      let height = totalHeight + 20;
      
      // Set SVG dimensions
      svg
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("viewBox", `0 0 ${containerWidth} ${height}`)
        .attr("preserveAspectRatio", "xMidYMid meet");

      // Clear any existing clip paths
      svg.selectAll("clipPath").remove();

      svg
        .append("clipPath")
        .attr("id", "myClip")
        .append("rect")
          .attr("x", padding)
          .attr("y", "40")
          .attr("width", containerWidth - padding - paddingBeforeTimeline)
          .attr("height", totalHeight + 40);

      // Create a single group for all bars
      const barsGroup = svg.append("g").attr("clip-path", "url(#myClip)");

      // Create individual groups for each bar and its text label
      const barAndTextGroups = barsGroup.selectAll("g")
        .data(data.flatMap(d => d.values))
        .enter()
        .append("g")
          .attr("clip-path", (d, i) => `url(#barClip${i})`);

      // Define a clip path for each group
      barAndTextGroups.append("clipPath")
        .attr("id", (d, i) => `barClip${i}`)
        .append("rect")
        .attr("x", (d) => {
          const x = linearScale(d.x1);
          return isNaN(x) ? 0 : Math.max(0, x);
        })
        .attr("y", (d) => heightStart[d.l])
        .attr("width", (d) => {
          const width = linearScale(d.x2) - linearScale(d.x1);
          return isNaN(width) ? 0 : Math.max(0, width);
        })
        .attr("height", 20);

      // Create bars within each bar and text group
      barAndTextGroups
        .append("rect")
        .attr("rx", "2")
        .attr("x", (d) => {
          const x = linearScale(d.x1);
          return isNaN(x) ? 0 : Math.max(0, x);
        })
        .attr("y", (d) => heightStart[d.l])
        .attr("width", (d) => {
          const width = linearScale(d.x2) - linearScale(d.x1);
          return isNaN(width) ? 0 : Math.max(0, width);
        })
        .attr("height", 20)
        .attr("fill", (d) => (barColors[d.l % barColors.length]));

      // Add text labels to the bar and text groups
      barAndTextGroups
        .append("text")
        .attr("x", (d) => {
          const x = linearScale(d.x1) + 3;
          return isNaN(x) ? 3 : Math.max(3, x);
        })
        .attr("y", (d) => heightStart[d.l] + 14)
        .text((d) => d.n)
        .attr("fill", "white");

      // Clear any existing x-axis
      svg.selectAll(".x-axis").remove();

      // Add x-axis group
      const xAxisGroup = svg
        .append("g")
        .attr("class", "x-axis")
        .attr("transform", `translate(0, ${paddingBeforeTimeline})`);

      // Add initial x-axis
      let tickPadding = 6;
      const xAxis = d3
        .axisTop(linearScale)
        .tickFormat(d => {
          if (isNaN(d)) return '';
          return Utils.secondsToTime(d);
        })
        .tickPadding(tickPadding);
      xAxisGroup.call(xAxis);

      // Create zoom behavior with updated settings
      zoom = d3
        .zoom()
        .scaleExtent([1, 75])
        .translateExtent([
          [padding, -Infinity],
          [containerWidth - paddingBeforeTimeline, Infinity],
        ])
        .extent([
          [padding, 0],
          [containerWidth - paddingBeforeTimeline, height],
        ])
        .on("zoom", zoomed.bind(this));

      // Apply zoom behavior to SVG
      svg.call(zoom).on("wheel.zoom", null);

      // Update the zoomed function to handle axis updates better
      function zoomed(event) {
        const { transform } = event;
        const newXScale = transform.rescaleX(linearScale);
        
        // Update x-axis with better tick formatting
        xAxis.scale(newXScale)
          .ticks(Math.min(10, Math.floor(containerWidth / 100)))
          .tickFormat(d => {
            if (isNaN(d)) return '';
            return Utils.secondsToTime(d);
          });
        xAxisGroup.call(xAxis);

        // Update the bars with NaN checks
        barsGroup
          .selectAll("rect")
          .attr("x", (d) => {
            const x = newXScale(d.x1);
            return isNaN(x) ? 0 : Math.max(0, x);
          })
          .attr("width", (d) => {
            const width = newXScale(d.x2) - newXScale(d.x1);
            return isNaN(width) ? 0 : Math.max(0, width);
          });

        // Update the text with NaN checks
        barsGroup.selectAll("text")
          .attr("x", (d) => {
            const x = newXScale(d.x1) + 5;
            return isNaN(x) ? 5 : Math.max(5, x);
          });

        // Update the vertical line
        const verticalLineX = newXScale(this.currentTime);
        if (!isNaN(verticalLineX)) {
          this.updateVerticalLine(verticalLineX);
        }
      }

      // Set initial zoom level
      this.zoomValue = DEFAULT_ZOOM_LEVEL;
      const initialTransform = d3.zoomIdentity
        .translate(0, 0)
        .scale(DEFAULT_ZOOM_LEVEL);
      svg.call(zoom.transform, initialTransform);

      // Initial position of the vertical line
      const initialXPosition = linearScale(0);

      svg
        .append("line")
        .attr("class", "vertical-line")
        .attr("x1", initialXPosition)
        .attr("y1", 32)
        .attr("x2", initialXPosition)
        .attr("y2", height)
        .attr("stroke", "red")
        .attr("stroke-width", 1);

      svg
        .append("line")
        .attr("class", "mouse-line")
        .attr("x1", initialXPosition)
        .attr("y1", 0)
        .attr("x2", initialXPosition)
        .attr("y2", height)
        .attr("stroke", "#0050bf")
        .attr("stroke-width", 1)
        .attr("opacity", 0);

      svg
        .append("text")
        .attr("class", "mouse-text")
        .attr("x", initialXPosition)
        .attr("y", 10)
        .attr("fill", "#0050bf")
        .attr("font-size", "11px")
        .attr("opacity", 0);

      const mouseG = svg
        .append('g')
        .attr('class', 'mouse-over-effects')

      mouseG
        .append('svg:rect')
        .attr('width', containerWidth - padding - paddingBeforeTimeline)
        .attr('height', height)
        .attr('x', padding + 1)
        .attr('fill', 'none')
        .attr('pointer-events', 'all')
        .on('click', (event) => {
          const transform = d3.zoomTransform(svg.node());
          const clickX = transform.invertX(d3.pointer(event)[0]);
          let originalValue = linearScale.invert(clickX);
          originalValue = Math.max(0, Math.min(originalValue, this.mediaDuration));
          const newXScale = d3.zoomTransform(svg.node()).rescaleX(linearScale);
          this.$emit("updateTime", originalValue);
          this.updateVerticalLine(newXScale(originalValue));
        })
        .on('mouseout', function () {
          d3.select('.mouse-line').style('opacity', '0');
          d3.select('.mouse-text').style('opacity', '0');
        })
        .on('mouseover', function () {
          d3.select('.mouse-line').style('opacity', '0.5');
          d3.select('.mouse-text').style('opacity', '0.5');
        })
        .on('mousemove', (event) => {
          const [mouseOverX, mouseOverY] = d3.pointer(event);
          d3
            .select(".mouse-line")
            .attr("x1", mouseOverX)
            .attr("x2", mouseOverX)
            .style('opacity', '1');

          const hovering = barAndTextGroups
            .filter(function () {
              const rect = this.querySelector("rect");
              const { x, y, width, height } = Object.fromEntries([...rect.attributes].map(v => [v.name, v.value]));
              return x <= mouseOverX && Number(x) + Number(width) >= mouseOverX && y <= mouseOverY && Number(y) + Number(height) >= mouseOverY;
            });
          if ([...hovering].length && [...hovering][0] != hoveringAnnotation) {
            hoveringAnnotation = [...hovering][0];
            const rect = hoveringAnnotation.querySelector("rect");
            const { x, y, height } = Object.fromEntries([...rect.attributes].map(v => [v.name, v.value]));
            const event = {
              x: Number(x),
              y: Number(y) + Number(height),
              mouseX: mouseOverX,
              mouseY: mouseOverY,
              entry: hovering.data()[0].entry
            }
            this.$emit("annotationEnter", event);
          }
          else if ([...hovering].length == 0 && hoveringAnnotation) {
            hoveringAnnotation = null;
            this.$emit("annotationLeave");
          }

          const transform = d3.zoomTransform(svg.node());
          const clickX = transform.invertX(d3.pointer(event)[0]);
          const originalValue = linearScale.invert(clickX);

          d3
            .select(".mouse-text")
            .attr("x", mouseOverX + 5)
            .style('opacity', '1')
            .text(Utils.secondsToTime(originalValue, true));
        });

      // If we're initializing for mobile, update position and center
      if (svgId === 'timeline-svg-mobile') {
        this.updateCurrentPosition(this.playerCurrentTime);
        this.center();
      } else {
        this.updateCurrentPosition(this.defaultCurrentTime);
      }
    }
  },
  mounted() {
    this.checkMobile();
    window.addEventListener('resize', this.handleResize);
    window.addEventListener('orientationchange', this.handleResize);
    
    // Initialize timeline for desktop view
    if (!this.isMobile) {
      this.initializeTimeline();
    }
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize);
    window.removeEventListener('orientationchange', this.handleResize);
  }
};
</script>
