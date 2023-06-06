const Utils = {
    uuidv4(){
      return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
      )
    },
    sortHelper(a, b){
      if (typeof a === 'string' || a instanceof String){
        a = a.replace(/[^a-zA-Z 0-9]/g, "")
      }
      if (typeof b === 'string' || b instanceof String){
        b = b.replace(/[^a-zA-Z 0-9]/g, "")
      }
      return Intl.Collator().compare(a, b);
    },
    nFormatter: (num, digits) => {
      const lookup = [
        { value: 1, symbol: '' },
        { value: 1e6, symbol: ' M' },
        // { value: 1e9, symbol: 'G' },
        // { value: 1e12, symbol: 'T' },
        // { value: 1e15, symbol: 'P' },
        // { value: 1e18, symbol: 'E' },
      ];
      const rx = /\.0+$|(\.[0-9]*[1-9])0+$/;
      var item = lookup
        .slice()
        .reverse()
        .find(function (item) {
          return num >= item.value;
        });
      return item ? (num / item.value).toFixed(digits).replace(rx, '$1') + item.symbol : '0';
    },
    msToTime(duration) {
      var milliseconds = Math.floor((duration % 1000) / 100),
        seconds = Math.floor((duration / 1000) % 60),
        minutes = Math.floor((duration / (1000 * 60)) % 60),
        hours = Math.floor((duration / (1000 * 60 * 60)) % 24);

      hours = (hours < 10) ? "0" + hours : hours;
      minutes = (minutes < 10) ? "0" + minutes : minutes;
      seconds = (seconds < 10) ? "0" + seconds : seconds;

      return hours + ":" + minutes + ":" + seconds + "." + milliseconds;
    },
    frameNumberToSeconds(frameNumber, frameRate = 25) {
      return frameNumber*1000/frameRate;
    },
  }

  export default Utils
