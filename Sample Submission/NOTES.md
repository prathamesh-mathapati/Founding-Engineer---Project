# Notes

## What I found
The data was in a semicolon separated format with AMC names in between. I parsed it accordingly.

## Decisions
I used a dictionary to store the schemes and computed the median change. Used FLOAT for NAV values.

## What I didn't do
Didn't add tests due to time. Would add more error handling.

## What breaks first
The parsing might break if the format changes. I would add more logging.

## Time
About 3 hours.
