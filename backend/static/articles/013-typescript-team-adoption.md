---
id: 13
title: "A Leader's Guide to TypeScript Adoption"
summary: "How to move a team off habitual 'any' in TypeScript: why it happens, what it costs, how to measure it, and a tooling-plus-culture rollout that ratchets type safety up without blocking delivery."
tags: ["typescript", "leadership", "engineering-management", "code-quality", "team-culture"]
draft: false
published_date: "2025-11-15T10:00:00"
created_at: "2025-11-15T10:00:00"
updated_date: "2026-11-04T00:00:00"
---

## Intro

Many TypeScript codebases are full of `any`. Each one makes a compiler error go away, so in practice the codebase gets most of the overhead of TypeScript and little of the safety.

This is for tech leads and engineering managers who want to change that without stopping feature work. It covers why `any` spreads, what it costs, how to measure it, and a rollout that tightens types gradually.

## Definitions

- **`any`**: turns off type checking for a value. Anything assigned to or read from it goes unchecked.
- **`unknown`**: the safe alternative. The value can be anything, but you have to narrow it (check its type) before using it.
- **Boundary**: where untyped data enters your code: API responses, `JSON.parse`, local storage, third-party libraries.
- **Ratchet**: a CI check that allows a metric to stay the same or improve, but never get worse.

## Why Developers Reach for `any`

The incentives are lopsided. `any` removes the error immediately, and nothing bad happens until much later, usually to someone else.

Common triggers:

1. **Poorly typed third-party libraries**
2. **Deadline pressure**: "I'll fix the types later"
3. **Hard type errors**: generics, conditional types, and inference failures take real expertise to untangle
4. **Untyped data at boundaries**: an API response has no type until someone writes one

Most of these are tooling and skills problems, not attitude problems. Address them that way.

## What `any` Costs

### Bugs pass the compiler

```typescript
function orderTotal(order: any) {
  return order.items.reduce((sum, item) => sum + item.price, 0);
}
```

If the API renames `price` to `priceInCents`, this doesn't throw. It returns `NaN`, and the `NaN` spreads into whatever uses the total.

Static types only help here if the type comes from the API itself (generated from an OpenAPI schema) or the response is validated at the boundary (see Zod below). A hand-written interface that's out of date gives the same false confidence as `any`.

### Refactors turn into grep

With a typed `Product`, renaming `price` makes the compiler list every usage. With `any`, you grep for `price`, check each result by hand, and find the ones you missed in production.

### Function signatures stop documenting anything

```typescript
// Answers its own questions
function createOrder(userId: string, items: CartItem[], payment: PaymentMethod): Promise<Order>

// Every caller has to read the implementation
function createOrder(userId: any, items: any, payment: any): any
```

### Editor tooling stops working

Autocomplete, go-to-definition, find-references, and rename all depend on types. On an `any`, they return nothing.

### How much to expect

Types don't catch everything. A study of public JavaScript bugs found that adding TypeScript or Flow annotations would have caught about **15%** of them ([Gao, Bird & Barr, ICSE 2017](https://earlbarr.com/publications/typestudy.pdf)). That's a real share of bugs, but sell types on refactoring speed and readability too, not on bug counts alone.

## Measuring It

Measure your own codebase before you argue for a change. Numbers from your team are more persuasive than numbers from an article.

| Metric | How to measure | What it tells you |
|--------|----------------|-------------------|
| `any` count | `@typescript-eslint/no-explicit-any` violations, tracked per week | Whether things are getting better or worse |
| Type-related production bugs | Tag incidents for 1–2 sprints: undefined access, wrong shape, null errors | How much the problem actually costs |
| Refactor overrun | Estimated vs actual time for the last large refactor | Cost of not being able to find usages |
| Review questions | Count "what type is this?" comments in PRs | Time reviewers spend on missing information |

If the data shows `any` isn't hurting much, believe it and spend the effort somewhere else.

## Rollout

### 1. Make escape hatches explicit and searchable

Don't ban `any` on day one. Require that each new one says why and links to a ticket:

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- TODO(types): PROJ-1234 untyped SDK
const client: any = createLegacyClient();
```

The lint rule makes `any` visible, the disable comment requires a reason, and `TODO(types)` gives you something to grep and count.

### 2. Type the boundaries first

Most of the value comes from typing data where it enters the system. Validate it once at the edge, and everything inside gets real types.

```typescript
import { z } from "zod";

export const Product = z.object({
  id: z.string(),
  name: z.string(),
  priceInCents: z.number().int(),
});
export type Product = z.infer<typeof Product>;

const product = Product.parse(await response.json()); // throws on mismatch
```

If the backend publishes an OpenAPI schema, generate the client types from it instead of writing them by hand.

### 3. Share a few patterns

Most of the team shouldn't need advanced TypeScript. Provide a small set of shared types for common cases:

```typescript
export type AsyncState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: Error };
```

### 4. Ratchet in CI

Add a lint rule, then make sure the count can't go up.

```js
// eslint.config.js
rules: {
  "@typescript-eslint/no-explicit-any": "warn",        // "error" once the count is low
  "@typescript-eslint/no-unsafe-assignment": "warn",
  "@typescript-eslint/no-unsafe-member-access": "warn",
}
```

```bash
# CI: fail if the count of explicit `any` goes up
COUNT=$(npx eslint src --rule '@typescript-eslint/no-explicit-any: error' -f json \
  | jq '[.[].messages[] | select(.ruleId == "@typescript-eslint/no-explicit-any")] | length')
BASELINE=$(cat .any-baseline)
[ "$COUNT" -le "$BASELINE" ] || { echo "any count rose: $BASELINE -> $COUNT"; exit 1; }
```

Lower the baseline whenever the count drops.

For `tsconfig.json`, turn on `strict` for new packages. For existing ones, enable the individual strict flags one at a time, `strictNullChecks` first, since it usually catches the most real bugs.

### 5. Pilot on one feature

Pick one new feature, type it strictly, and compare it with a similar recent feature on the metrics above. Share the result whether or not it supports your case. A pilot only helps if people believe you'd report a bad result too.

### 6. Model it in code review

Unhelpful: "Don't use `any`."

Helpful: "`Pick<User, 'id' | 'name'>` here would stop us accidentally passing `email`, which is the bug from last week. Want to pair on it?"

Type the shared code yourself (API client, common utilities, core components), since everyone else depends on it.

## Timeline

| When | What |
|------|------|
| Month 1 | Lint rule as a warning, baseline measured, boundary validation for the main API |
| Month 2 | Pilot feature, metrics compared, results shared |
| Month 3 | CI ratchet on, strict mode for new code |
| Months 4–12 | Count goes down steadily; strict flags enabled one at a time on legacy packages |

## Pitfalls

- **Blocking every PR with `any` on day one.** People start using `as unknown as Foo` casts instead, which are just as unsafe and harder to find. Ratchet instead.
- **Making it a blame exercise.** Most existing `any` was written under deadline pressure. Fix the incentives, not the people.
- **Expecting everyone to become a TypeScript expert.** Shared patterns and typed boundaries do most of the work.
- **Hand-written API types.** They go stale silently. Generate them or validate at runtime.
- **Overselling.** If you promise types will eliminate bugs, the first type-safe bug will cost you credibility. Promise what the 15% figure supports.

## Measuring Success

- `any` count goes down steadily and never goes up
- Fewer type-related production bugs than your baseline
- Large refactors land closer to their estimates
- New code is strict by default without anyone pushing for it

## Conclusion

Treat `any` like any other tech debt: measure it, stop it from growing, and pay it down gradually. Type the boundaries first, ratchet in CI, and change behavior through code review rather than mandates.

## References

- Gao, Bird, Barr. [To Type or Not to Type: Quantifying Detectable Bugs in JavaScript](https://earlbarr.com/publications/typestudy.pdf). ICSE 2017.
- [typescript-eslint rules](https://typescript-eslint.io/rules/)
- [Zod](https://zod.dev/)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [Total TypeScript](https://www.totaltypescript.com/)
