let config = null;
if (process.env.NODE_ENV === "production") {
  config = {
    apiUrl: "http://localhost:9090",
    appDomain: "uplord.linguistik.uzh.ch",
    environment: "production",
    apiHeaders: {},
    sentryDSN: null,
  };
} else if (process.env.NODE_ENV === "test") {
  config = {
    apiUrl: "http://localhost:9090",
    appDomain: "uplord.test.linguistik.uzh.ch",
    environment: "test",
    apiHeaders: {},
    sentryDSN: null,
  };
} else if (process.env.NODE_ENV === "dev") {
  config = {
    apiUrl: "http://localhost:9090",
    appDomain: "uplord.dev.linguistik.uzh.ch",
    environment: "development",
    apiHeaders: {},
    sentryDSN: null,
  };
} else {
  // development
  config = {
    apiUrl: "http://localhost:9090",
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

      // "X-Remote-User": "igor.mustac@gmail.com",
      // "X-Display-Name": "Igor Mustac",
      // "X-Edu-Person-Unique-Id": "553131353436323305@gmail.com",
      // "X-Home-Organization": "switch.ch",
      // "X-Schac-Home-Organization": "switch.ch",
      // "X-Persistent-Id": "https://aai-idp.uzh.ch/idp/shibboleth!https://liri.linguistik.uzh.ch/shibboleth!switchkf123123QnxHUi4aIyJGRB+o=",
      // "X-Given-Name": "Igor1",
      // "X-Surname": "Mustac1",
      // "X-Principal-Name": "553131353436323305@gmail.com",
      // "X-Mail": "igor.mustac@gmail.com",
      // "X-Shib-Identity-Provider": "https://aai-idp.uzh.ch/idp/shibboleth",
    },
    sentryDSN: null,
  };
}

export default config;
