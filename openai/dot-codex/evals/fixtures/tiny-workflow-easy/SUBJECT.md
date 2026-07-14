`parse_retry_delay()` accepts blank or whitespace-only strings and silently
turns them into `0`. Make blank input raise `ValueError` with an actionable
message. Keep the change contained unless the contract requires otherwise, and
add or update focused tests.
