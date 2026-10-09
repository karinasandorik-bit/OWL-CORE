# SUSU-LABS/susu-web #51 — prepared delivery

Target: https://github.com/SUSU-LABS/susu-web/issues/51

Status: **UNPAID, UNASSIGNED, BUYER TERMS NOT CONFIRMED**.
This is a staged patch, NOT an upstream pull request or a completed paid delivery.

## Minimal implementation

Add a fourth optional parameter `extraSchema?: z.ZodType<Record<string, unknown>>`
to `apiRequestPageBody` after `itemSchema`. Before returning, check:

```ts
  if (extraSchema) {
    const parsed = extraSchema.safeParse(body);
    if (!parsed.success) {
      throw new ApiError(status, undefined,
        `The server returned unexpected extra fields: ${parsed.error.issues.map(
          (issue) => `${issue.path.join('.')}: ${issue.message}`
        ).join(', ')}`);
    }
  }
```

Pass `z.object({ unreadCount: z.number().int().nonnegative() }).passthrough()`
at the notifications caller. This preserves backwards compatibility for other
`apiRequestPageBody` consumers and validates the field where its contract is known.

## Regression cases

1. `unreadCount` absent -> ApiError.
2. `unreadCount` string -> ApiError.
3. `unreadCount` nonnegative integer -> unchanged body and page.
4. Existing generic `extraField` usage with no extra schema -> unchanged.
5. Invalid page or invalid item -> existing ApiError behavior.

## Release gate

Confirm buyer identity/authority, $50 funding, payment method and acceptance
before representing this as commissioned work. Verify source caller path before
making upstream code edits. No tests were run in the upstream project.
