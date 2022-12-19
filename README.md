# Amazon Chime SDK SMA Meeting Dialer

This demo will consume a JSON file uploaded to an S3 bucket and call all participants in the list.

## To Use

Upload the `trigger.json` file to the S3 bucket to begin the process. The json file should be formatted as:

```json
{
  "EventId": 12345,
  "Participants": [
    {
      "PhoneNumber": "+13125551212"
    },
    {
      "PhoneNumber": "+18155551212"
    }
  ]
}
```

## To Deploy

- aws cli
- Docker daemon

```
yarn launch
```
