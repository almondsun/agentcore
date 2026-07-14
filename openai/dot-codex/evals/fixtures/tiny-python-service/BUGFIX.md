`lookup_user()` accepts blank or whitespace-only IDs, which normalize to an
empty string and leak downstream as `user:`. Make blank IDs raise `ValueError`
from the normalization path while preserving that contract through the API.
