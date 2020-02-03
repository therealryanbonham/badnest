# badnest

A bad Nest integration that uses the web api to work after Works with Nest was shut down (bad Google, go sit in your corner and think about what you did)

## Why is it bad

This isn't an advertised or public API, it's still better than web scraping, but will never be as reliable as the original API

## Features

- Doesn't use the now defunct Works with Nest API
- Works with migrated/new accounts via Google auth
- Nest Protect support
- Nest Thermostat support
- Nest Thermostat Sensor support
- Nest Camera support

## Drawbacks

- Tested with a single thermostat, I have no other devices to test with
- Camera integration is untested by me
- Nest Protect integration is untested by me
- Nest could change their webapp api at any time, making this defunct (this has happened before, see <https://github.com/USA-RedDragon/badnest/issues/67>)

## Configuration

The camera's region is one of `us` or `eu` depending on your region.
If you're not in the US or EU, you should be able to add your
two-character country code, and it should work.

### Example configuration.yaml - When you're not using the Google Auth Login

Google recently introduced reCAPTCHA when logging to Nest. That means username
and password cannot be used directly any more. Instead, you have to obtain
`user_id` and `access_token` for your account by logging in manually. To do that,
open developer tools in your browser, switch to the "Network" tab, log in to Nest
and look for the request similar to `https://home.nest.com/session?_=1578693398448`.
You will find `user_id` and `access_token` in the response to the request.

```yaml
badnest:
  user_id: 11111
  access_token: !secret nest_access_token
  region: us

climate:
  - platform: badnest
    scan_interval: 10

camera:
  - platform: badnest

sensor:
  - platform: badnest
```

### Example configuration.yaml - When you are using the Google Auth Login

```yaml
badnest:
  issue_token: "https://accounts.google.com/o/oauth2/iframerpc....."
  cookie: "OCAK=......"
  region: us

climate:
  - platform: badnest
    scan_interval: 10

camera:
  - platform: badnest

sensor:
  - platform: badnest
```

Google Login support added with many thanks to: chrisjshull from <https://github.com/chrisjshull/homebridge-nest/>

The values of `"issue_token"` and `"cookie"` are specific to your Google Account. To get them, follow these steps (only needs to be done once, as long as you stay logged into your Google Account).

1. Open a Chrome browser tab in Incognito Mode (or clear your cache).
2. Open Developer Tools (View/Developer/Developer Tools).
3. Click on 'Network' tab. Make sure 'Preserve Log' is checked.
4. In the 'Filter' box, enter `issueToken`
5. Go to `home.nest.com`, and click 'Sign in with Google'. Log into your account.
6. One network call (beginning with `iframerpc`) will appear in the Dev Tools window. Click on it.
7. In the Headers tab, under General, copy the entire `Request URL` (beginning with `https://accounts.google.com`, ending with `nest.com`). This is your `"issue_token"` in `configuration.yaml`.
8. In the 'Filter' box, enter `oauth2/iframe`
9. Several network calls will appear in the Dev Tools window. Click on the last `iframe` call.
10. In the Headers tab, under Request Headers, copy the entire `cookie` (beginning `OCAK=...` - **include the whole string which is several lines long and has many field/value pairs** - do not include the `cookie:` name). This is your `"cookie"` in `configuration.yaml`.

## Notes

The target temperature reported by the integration sometimes _seems_ to be slightly off by a few tens of a degree.
This is caused by the fact that the Nest mobile app actually actually allows users to set the temperature in small
increments, but the displayed temperature is rounded to the nearest 0.5 degree. In other words, the temperature
displayed by the integration is correct, just _more exact_ than what is shown in the app.
