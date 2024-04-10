let config = {};

const testUserHeaders = {
  "X-Remote-User": "firstname.lastname@uzh.ch",
  "X-Display-Name": "Firstname Lastname",
  "X-Mail": "firstname.lastname@uzh.ch",
  "X-Edu-Person-Unique-Id": "test_user_uniq_id@uzh.ch",
}

if (process.env.APP_TYPE == "vian") {
  if (process.env.NODE_ENV == "production") {
    config = {
      appName: "videoscope",
      apiUrl: "https://videoscope.linguistik.uzh.ch/be",
      wsUrl: "wss://videoscope.linguistik.uzh.ch/ws",
      apiHeaders: {},
      sentryDSN: null,
      baseMediaUrl: "https://videoscope.linguistik.uzh.ch/video",
    };
  } else if (process.env.NODE_ENV == "staging") {
    config = {
      appName: "videoscope",
      apiUrl: "https://videoscope.test.linguistik.uzh.ch/be",
      wsUrl: "wss://videoscope.test.linguistik.uzh.ch/ws",
      apiHeaders: {},
      sentryDSN: null,
      baseMediaUrl: "https://videoscope.test.linguistik.uzh.ch/media",
    };
  } else {
    // development
    config = {
      appName: "videoscope",
      apiUrl: "http://localhost:9090",
      wsUrl: "ws://localhost:9090/ws",
      apiHeaders: testUserHeaders,
      sentryDSN: null,
      baseMediaUrl: "http://localhost:8000",
    };
  }
}
else if (process.env.APP_TYPE == "ofrom") {
  if (process.env.NODE_ENV === "production") {
    config = {
      appName: "soundscript",
      apiUrl: "https://soundscript.linguistik.uzh.ch/be",
      wsUrl: "wss://soundscript.linguistik.uzh.ch/ws",
      apiHeaders: {},
      sentryDSN: null,
      baseMediaUrl: "https://soundscript.linguistik.uzh.ch/media",
    };
  } else if (process.env.NODE_ENV === "staging") {
    config = {
      appName: "soundscript",
      apiUrl: "https://soundscript.test.linguistik.uzh.ch/be",
      wsUrl: "wss://soundscript.test.linguistik.uzh.ch/ws",
      apiHeaders: {},
      sentryDSN: null,
      baseMediaUrl: "https://soundscript.test.linguistik.uzh.ch/media",
    };
  } else {
    // development
    config = {
      appName: "soundscript",
      apiUrl: "http://localhost:9090",
      wsUrl: "ws://localhost:9090/ws",
      apiHeaders: testUserHeaders,
      sentryDSN: null,
      baseMediaUrl: "http://localhost:8000",
    };
  }
}
else if (process.env.APP_TYPE == "catchphrase") {
  if (process.env.NODE_ENV === "production") {
    config = {
      appName: "catchphrase",
      apiUrl: "https://catchphrase.linguistik.uzh.ch/be",
      wsUrl: "wss://catchphrase.linguistik.uzh.ch/ws",
      apiHeaders: {},
      sentryDSN: null,
    };
  } else if (process.env.NODE_ENV === "staging") {
    config = {
      appName: "catchphrase",
      apiUrl: "https://catchphrase.test.linguistik.uzh.ch/be",
      wsUrl: "wss://catchphrase.test.linguistik.uzh.ch/ws",
      apiHeaders: {},
      sentryDSN: null,
    };
  } else if (process.env.NODE_ENV === "dev") {
    config = {
      appName: "catchphrase",
      apiUrl: "http://localhost:9090",
      apiHeaders: {},
      sentryDSN: null,
    };
  } else {
    // development
    config = {
      appName: "catchphrase",
      apiUrl: "http://localhost:9090",
      wsUrl: "ws://localhost:9090/ws",
      apiHeaders: testUserHeaders,
      sentryDSN: null,
      baseMediaUrl: "http://localhost:8000",
    };
  }
}
else {
  // LCP
  if (process.env.NODE_ENV === "production") {
    config = {
      appName: "LCP",
      apiUrl: "https://lcp.linguistik.uzh.ch/be",
      wsUrl: "wss://lcp.linguistik.uzh.ch/ws",
      apiHeaders: {},
      sentryDSN: null,
    };
  } else if (process.env.NODE_ENV === "staging") {
    config = {
      appName: "LCP",
      apiUrl: "https://lcp.test.linguistik.uzh.ch/be",
      wsUrl: "wss://lcp.test.linguistik.uzh.ch/ws",
      apiHeaders: {},
      sentryDSN: null,
    };
  } else if (process.env.NODE_ENV === "dev") {
    config = {
      appName: "LCP",
      apiUrl: "http://localhost:9090",
      apiHeaders: {},
      sentryDSN: null,
    };
  } else {
    // development
    config = {
      appName: "LCP",
      apiUrl: "http://localhost:9090",
      wsUrl: "ws://localhost:9090/ws",
      apiHeaders: testUserHeaders,
      sentryDSN: null,
      baseMediaUrl: "http://localhost:8000",
    };
  }
}
config.appType = process.env.APP_TYPE;

export default config;
