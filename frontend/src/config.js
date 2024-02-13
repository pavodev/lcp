let config = null;
if (process.env.APP_TYPE == "vian") {
  if (process.env.NODE_ENV === "production") {
    config = {
      appName: "VIAN-DH",
      apiUrl: "https://vian.linguistik.uzh.ch/be",
      wsUrl: "wss://vian.linguistik.uzh.ch/ws",
      appDomain: "vian.linguistik.uzh.ch",
      environment: "production",
      apiHeaders: {},
      sentryDSN: null,
      baseVideoUrl: "https://vian.linguistik.uzh.ch/video",
    };
  } else if (process.env.NODE_ENV === "test") {
    config = {
      appName: "VIAN-DH",
      apiUrl: "https://vian.test.linguistik.uzh.ch/be",
      wsUrl: "wss://vian.test.linguistik.uzh.ch/ws",
      appDomain: "vian.test.linguistik.uzh.ch",
      environment: "test",
      apiHeaders: {},
      sentryDSN: null,
      baseVideoUrl: "https://vian.test.linguistik.uzh.ch/video",
    };
  } else if (process.env.NODE_ENV === "dev") {
    config = {
      appName: "VIAN-DH",
      apiUrl: "http://localhost:9090",
      appDomain: "vian.dev.linguistik.uzh.ch",
      environment: "development",
      apiHeaders: {},
      sentryDSN: null,
      baseVideoUrl: "https://vian.dev.linguistik.uzh.ch/video",
    };
  } else {
    // development
    config = {
      appName: "VIAN-DH",
      apiUrl: "http://localhost:9090",
      wsUrl: "ws://localhost:9090/ws",
      appDomain: "localhost",
      environment: "development",
      apiHeaders: {
        // "X-Remote-User": "nikolina.rajovic@uzh.ch",
        // "X-Display-Name": "Nikolina Rajovic",
        // "X-Edu-Person-Unique-Id": "8599941289f8@uzh.ch",
        // "X-Home-Organization": "uzh.ch",

        "X-Remote-User": "igor.mustac@uzh.ch",
        "X-Display-Name": "Igor Mustac",
        "X-Edu-Person-Unique-Id": "553131353436323302@uzh.ch",
        "X-Home-Organization": "uzh.ch",
        "X-Schac-Home-Organization": "uzh.ch",
        "X-Persistent-Id":
          "https://aai-idp.uzh.ch/idp/shibboleth!https://liri.linguistik.uzh.ch/shibboleth!O7bJIkf8gJ9QnxHUi4aIyJGRB+o=",
        "X-Given-Name": "Igor",
        "X-Surname": "Mustac",
        "X-Principal-Name": "553131353436323302@uzh.ch",
        "X-Mail": "igor.mustac@uzh.ch",
        "X-Shib-Identity-Provider": "https://aai-idp.uzh.ch/idp/shibboleth",
      },
      sentryDSN: null,
      baseVideoUrl: "http://localhost:8000",
    };
  }
}
else {
  if (process.env.NODE_ENV === "production") {
    config = {
      appName: "catchphrase",
      apiUrl: "https://lcp.linguistik.uzh.ch/be",
      wsUrl: "wss://lcp.linguistik.uzh.ch/ws",
      appDomain: "lcp.linguistik.uzh.ch",
      environment: "production",
      apiHeaders: {},
      sentryDSN: null,
    };
  } else if (process.env.NODE_ENV === "test") {
    config = {
      appName: "catchphrase",
      apiUrl: "https://lcp.test.linguistik.uzh.ch/be",
      wsUrl: "wss://lcp.test.linguistik.uzh.ch/ws",
      appDomain: "lcp.test.linguistik.uzh.ch",
      environment: "test",
      apiHeaders: {},
      sentryDSN: null,
    };
  } else if (process.env.NODE_ENV === "dev") {
    config = {
      appName: "catchphrase",
      apiUrl: "http://localhost:9090",
      appDomain: "lcp.dev.linguistik.uzh.ch",
      environment: "development",
      apiHeaders: {},
      sentryDSN: null,
    };
  } else {
    // development
    config = {
      appName: "catchphrase",
      apiUrl: "http://localhost:9090",
      wsUrl: "ws://localhost:9090/ws",
      appDomain: "localhost",
      environment: "development",
      apiHeaders: {
        // "X-Remote-User": "nikolina.rajovic@uzh.ch",
        // "X-Display-Name": "Nikolina Rajovic",
        // "X-Edu-Person-Unique-Id": "8599941289f8@uzh.ch",
        // "X-Home-Organization": "uzh.ch",

        "X-Remote-User": "igor.mustac@uzh.ch",
        "X-Display-Name": "Igor Mustac",
        "X-Edu-Person-Unique-Id": "553131353436323302@uzh.ch",
        "X-Home-Organization": "uzh.ch",
        "X-Schac-Home-Organization": "uzh.ch",
        "X-Persistent-Id":
          "https://aai-idp.uzh.ch/idp/shibboleth!https://liri.linguistik.uzh.ch/shibboleth!O7bJIkf8gJ9QnxHUi4aIyJGRB+o=",
        "X-Given-Name": "Igor",
        "X-Surname": "Mustac",
        "X-Principal-Name": "553131353436323302@uzh.ch",
        "X-Mail": "igor.mustac@uzh.ch",
        "X-Shib-Identity-Provider": "https://aai-idp.uzh.ch/idp/shibboleth",
      },
      sentryDSN: null,
      baseVideoUrl: "http://localhost:8000",
    };
  }
}
config.appType = process.env.APP_TYPE == "vian" ? "vian" : "lcp";

export default config;
