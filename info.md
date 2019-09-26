# shittynest

A shitty Nest thermostats integration that uses the web api to work after Works with Nest was shut down (fuck Google)

## Drawbacks

- No proper error handling
- Won't work with 2FA enabled accounts
- Will only work the for thermostat, I have no other devices to test with
- Nest could change their webapp api at any time, making this defunct
- Won't work with Google-linked accounts
- Presets don't work (Eco, Away)

## Example configuration.yaml

```yaml
shittynest:
  email: email@domain.com
  password: !secret nest_password

climate:
  - platform: shittynest
    scan_interval: 10
```
