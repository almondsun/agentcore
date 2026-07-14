Implement one consistent public status contract across the Python API and CLI:

- `summarize_user()` returns `id`, `status_code`, and `display_status`;
- aliases such as `enabled` normalize through the shared status module; and
- `format_summary_line()` uses the same normalization and displays the label.

Update focused regression coverage and treat this as a public interface change.
