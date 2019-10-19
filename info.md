# badnest

A bad Nest thermostat and camera integration that uses the web api to work after Works with Nest was shut down (bad Google, go sit in your corner and think about what you did)

## Why is it bad?

This isn't an advertised or public API, it's still better than web scraping, but will never be as good as the original API

## Drawbacks

- No proper error handling
- Won't work with 2FA enabled accounts
- Tested with a single thermostat, I have no other devices to test with
- Camera integration is untested by me
- Nest could change their webapp api at any time, making this defunct
- Won't work with Google-linked accounts
- Presets don't work (Eco, Away)

## Example configuration.yaml

```yaml
badnest:
  email: email@domain.com
  password: !secret nest_password

camera:
  - platform: badnest

climate:
  - platform: badnest
    scan_interval: 10
```
