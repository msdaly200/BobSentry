**# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Stack

- **Backend:** Java 17/21/25, Maven (use `./mvnw` wrapper), Quarkus runtime
- **Frontend:** TypeScript/React in `js/`, PNPM workspaces (`pnpm@11.1.1`), Vite build, Wireit task orchestration
- **Testing (backend):** Two suites — new framework under `tests/` (JUnit 5 + `@KeycloakIntegrationTest`) and legacy Arquillian under `testsuite/integration-arquillian/`

## Build Commands

```bash
# Full build without tests
./mvnw clean install -DskipTests

# Build only the server distribution (fastest for server changes)
./mvnw -pl quarkus/deployment,quarkus/dist -am -DskipTests clean install
# Output ZIP: quarkus/dist/target/

# Build a single module after a code change (e.g. services)
./mvnw -f services/pom.xml clean install -DskipTests

# JS frontend (from js/)
pnpm --filter keycloak-admin-ui run build
pnpm --filter keycloak-admin-ui run lint
pnpm --filter keycloak-admin-ui run dev   # requires Keycloak running with KC_ADMIN_VITE_URL=http://localhost:5174
```

## Test Commands

### New test framework (`tests/` — preferred for new tests)

```bash
# Run all tests (uses embedded Keycloak by default)
./mvnw -f tests/pom.xml test

# Run a single test class
./mvnw -f tests/pom.xml test -Dtest=UsersTest

# Use remote Keycloak (must be running on localhost:8080)
KC_TEST_SERVER=remote ./mvnw -f tests/pom.xml test -Dtest=UsersTest

# Use embedded Quarkus server
KC_TEST_SERVER=embedded ./mvnw -f tests/pom.xml test -Dtest=UsersTest
```

### Legacy Arquillian suite (`testsuite/integration-arquillian/`)

```bash
# Run a single test (embedded Undertow — fastest, no dist rebuild needed)
./mvnw -f testsuite/integration-arquillian/pom.xml clean install -Dtest=LoginTest

# Production mode (Quarkus) — requires full dist build first
./mvnw -f testsuite/integration-arquillian/pom.xml -Pauth-server-quarkus clean install
```

## Code Style (Java)

- **Spotless enforces formatting** — run `./mvnw spotless:check` before a PR; auto-fix with `./mvnw spotless:apply`. Must use `./mvnw`, not `mvn` (plugin resolution differs).
- **Import order** (enforced by `.editorconfig`): `java.**`, `javax.**` → `jakarta.**` → `org.keycloak.**` → everything else. No wildcard imports.
- **Assertions in tests:** Use `org.hamcrest.MatcherAssert.assertThat` with Hamcrest matchers — **not** `org.junit.Assert.*`
- **No mocking frameworks** — zero tolerance; Keycloak does not use Mockito or similar
- Unit tests are avoided; write integration tests instead

## Code Style (TypeScript/React)

- **No default React import** — `import React from "react"` is an ESLint error; use named imports only.
- **Lodash imports must be member-scoped**: `import map from "lodash/map"`, not `import _ from "lodash"`.
- **Private class fields** must use `#field` syntax — `private` keyword is an ESLint error.
- **No nested component definitions** inside render functions — ESLint `react/no-unstable-nested-components` errors (causes re-mounting).
- **Non-null assertion (`!`)** is only valid on types from `keycloak-nodejs-admin-client` (generated from Java; nullability is unknown).
- **No Redux or global state libraries** — state lifted by component composition, then React context; never external state managers.
- **CSS classes** use BEM namespaced as `keycloak-admin--block[__element][--modifier]`; always use PatternFly CSS variables for colors/spacing, never hard-coded pixel/hex values.

## New Test Framework Patterns (tests/)

- Annotate test class with `@KeycloakIntegrationTest`; inject resources with `@InjectRealm`, `@InjectUser`, `@InjectClient`, `@InjectAdminClient`, etc.
- Resource lifecycle defaults: realm = `CLASS`, user = `CLASS`. Override with `@InjectRealm(lifecycle = LifeCycle.METHOD)` for per-method isolation.
- `LifeCycle.GLOBAL` persists across all test classes; mixing lifecycle scopes can cause reuse/cleanup bugs.
- `@InjectRealm(attachTo = "master")` attaches to an existing realm — **config is ignored and the realm is never auto-deleted**.
- When injecting **multiple instances of the same type**, each must have a unique `ref()` or injection matching breaks silently.
- Realm config is a `RealmConfig` inner class implementing `configure(RealmBuilder)` — pass via `@InjectRealm(config = MyConfig.class)`.
- `@InjectRealm(fromJson = "realm.json")` loads from test classpath; throws `RuntimeException` if file not found.
- Running code inside the server uses `@InjectRunOnServer RunOnServerClient` (replaces Arquillian's `RunOnServer`).
- `@TestSetup` methods run after all injections complete but before any test method; `@TestCleanup` runs after all methods.
- IDE execution works directly without Maven; the framework auto-starts Keycloak.
- The framework auto-creates missing dependencies not declared as fields — watch for unexpected resource setup overhead.
- **RealmConfig/ClientConfig/UserConfig classes can themselves inject dependencies** via `@InjectDependency` (e.g., `KeycloakUrls` for setting dynamic redirect URIs at config time).
- **Realm state cleanup strategies:** `managedRealm.dirty()` forces full realm recreation before next test; `managedRealm.updateWithCleanup(r -> ...)` applies a reversible change that auto-reverts; `managedRealm.cleanup().add(...)` registers arbitrary rollback logic.
- **Hot deployment for extension testing:** set `KC_TEST_SERVER_HOT_DEPLOY=true` and call `.dependencyCurrentProject()` on the server config to deploy the current module's compiled classes without rebuilding the server ZIP.
- **Test server modes** (set via `KC_TEST_SERVER`): `distribution` (default — installs ZIP to system temp, reused if ZIP unchanged), `embedded` (same JVM), `remote` (existing server on localhost:8080). `KC_TEST_SERVER_REUSE=true` leaves the server running between test suites.
- **Database modes** (set via `KC_TEST_DATABASE`): defaults to `dev-mem`; container options (`mariadb`, `postgres`, `mysql`, etc.) support reuse with `KC_TEST_DATABASE_REUSE=true` + `TESTCONTAINERS_REUSE_ENABLE=true`.

## Critical Gotchas

- **IDE builds:** Some code is generated by Maven plugins. Run `./mvnw clean install -DskipTests` once before using the IDE. Use `Build → Build Project`, never `Rebuild Project`.
- **Operator module** is excluded from default build; enable with `-Poperator`.
- **`org.keycloak.testsuite.*` classes must not be used in production code.**
- **Proto-schema compatibility checks** may fail in proxy environments; skip with `-DskipProtoLock=true`.
- **JS workspace deps** use `workspace:*` (PNPM) — do not manually version them.
- **Admin UI** build output goes to `target/classes/theme/keycloak.v2/admin/resources` (not `dist/`).
- **Account UI** is a separate app (`js/apps/account-ui`), uses Playwright (not Vitest) for tests, and builds to `target/classes/theme/keycloak.v3/account/resources`. It can also be built as an npm library with `LIB=true vite build`.
- **Maven default profiles** use negation activation (`!skipX`). To disable testsuite/adapters/docs inclusion pass `-DskipTestsuite`, `-DskipAdapters`, or `-DskipDocs`. The `distribution` and `operator` profiles must be explicitly opted in with `-Pdistribution` / `-Poperator`.
- **PRs require a linked GitHub Issue** and must be a single squashed commit rebased with `git rebase` (not `git pull`). AI-generated solutions must be disclosed in the PR description. Each commit must have a `--signoff`.
  **