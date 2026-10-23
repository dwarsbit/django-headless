# Writing style guide

How the Django Headless documentation, the docs website and the README are
written: the voice, the words, and what they do and do not mention. It
applies to every user-facing text in this repository, and to anyone writing
it, people and AI agents alike. The changelog follows the voice and
terminology rules, but it records history, so the rules on what not to
mention do not apply to it.

When this guide and an existing page disagree, the guide wins: fix the page.

## 1. Voice and tone

**Talk to the reader as "you". Never write "we".** The project is
"Django Headless", not "we" or "us".

| Do | Don't |
|----|-------|
| Expose the model and its routes appear under `/api/`. | We generate the routes for you. |
| Django Headless casts the value to the field's type. | We cast values to the right type. |

**Plain and precise.** Write like the Django documentation: calm, factual,
specific. Explain *why* when the reason helps the reader decide or avoid a
mistake. No hype, no exclamation marks, no filler.

| Do | Don't |
|----|-------|
| Run `python manage.py runserver`; the article list is at `/api/blog.article`. | That's it! 🎉 Your API is live! |
| `LookupFilter` accepts every lookup the field supports. | Powerful, flexible filtering out of the box. |

Avoid these words: *simply, just, easy, easily, quickly, instant(ly),
obviously, of course, powerful, seamless(ly), blazing, magic(al), amazing,
awesome, robust, cutting-edge, leverage, utilize*. They promise or judge
instead of inform.

**State limitations and risks plainly, with the fix.** Do not soften them
and do not alarm. Every caveat says what to do about it.

> Do: `PAGE_SIZE` has no effect without a pagination class; set
> `DEFAULT_PAGINATION_CLASS` as well.
>
> Don't: Note that pagination might not work in some setups.

## 2. Spelling and mechanics

- **American English**: customize, behavior, serialize, license (noun and
  verb), canceled.
- **Sentence case** for every heading: "Exposing models", "Read-only
  models", not "Read-Only Models".
- **Em dashes sparingly**: at most one per paragraph. Prefer a period, a
  colon or parentheses. Never use an em dash where a comma works.
- **Short paragraphs**: about four sentences at most, one idea each. Lead
  with the point; details follow.
- **Lists** for three or more parallel items; a sentence for two.
- **Procedures** are numbered steps in the imperative ("Add…", "Run…",
  "Set…"), one action per step.
- **Code font** for anything you type or read in code: setting names
  (`PAGE_SIZE`), class names (`LookupFilter`), decorator options
  (`read_only`), query parameters (`?expand=`), routes
  (`/api/blog.article`), headers (`X-Secret-Key`), commands
  (`manage.py runserver`), file names (`settings.py`) and literal values
  (`None`, `"X-Secret-Key"`).
- **Settings** in prose as `HEADLESS["PAGE_SIZE"]` on first mention, then
  `PAGE_SIZE` when the context is clear. DRF settings as
  `REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]`.
- **Status codes** in code font with their reason phrase on first mention
  (`403 Forbidden`), the number alone after (`403`).
- **Bold** only for a lead-in term in a list item, or a warning-level word.
  Do not bold for emphasis in running text.
- **Admonitions** (`:::note`, `:::tip`, `:::warning`) for information the
  reader must not miss; at most one or two per page.
- **Links**: link the first mention of a setting, page or concept on a page;
  link text says where it goes ("see [Permissions](./permissions.md)"),
  never "click here". Pages link to each other with relative file links;
  the README links to `https://djangoheadless.org/docs/…`.

## 3. Emoji

One emoji per **page title**, unique across the site, for recognition in the
sidebar. No emoji anywhere else: not in section headings, body text, lists,
admonitions or the README.

The changelog and the boot log are the exceptions: each changelog entry and
each boot log line may start with one emoji as a category marker (🐛 fix,
🎁 feature, ⚙️ setting, 🛡️ security, ⚠️ breaking change).

## 4. Terminology

### The product

- **Django Headless** in running text.
- **`django-headless`** in code font only as the package name: in
  `pip install django-headless` and on PyPI.
- **`headless`** in code font only as the app label and import path:
  `INSTALLED_APPS`, `from headless import expose`.
- Never *DH*, *Headless* on its own, *the library* or *the plugin*.

### Exposing models and the API

- **expose a model**: decorate it with `@expose()` (or call
  `expose_model()`). The model is then an **exposed model**.
- **the API**: everything Django Headless serves under the path you include
  `headless.rest.urls` at.
- **generated route**: one URL pattern of the API with its methods, such as
  `GET /api/blog.article`. Use "route", not "endpoint".
- **singleton**: an exposed model with `singleton=True`; it has one route
  and no primary key in the URL.
- **label**: the `app_label.model_name` part of the route (`blog.article`).

### People and clients

- **you**: the reader, a Django developer setting up Django Headless.
- **the frontend**: the site or app that reads content from the API
  (Next.js, Astro, a static site build). Name frameworks only as examples.
- **client**: any program that sends requests to the API, when the text is
  about requests in general (authentication, headers, status codes).
- Not *consumer*, *end user* or *customer*.

### Glossary

| Use | Not |
|-----|-----|
| expose a model | register a model, add a model, hook up a model |
| exposed model | registered model, headless model |
| generated route | endpoint, generated endpoint, URL, view |
| the API | the REST backend, the headless API, the server |
| list route, detail route | collection, index, item endpoint |
| singleton | singleton endpoint, settings model |
| setting (`HEADLESS["…"]`) | config option, parameter, flag |
| decorator option (`read_only`, `fields`) | argument, kwarg, flag |
| query parameter (`?expand=`, `?page=`) | query arg, GET param |
| lookup (`title__icontains`) | operator, filter expression |
| exclusion (`~published`) | negation, negative filter |
| expand a relation | embed, include, nest |
| boot log | startup log, banner, console output |
| frontend | consumer, client app (when the frontend is meant) |

## 5. What to mention, and what not

### Never mention

- **Implementation details.** Describe what Django Headless does for the
  reader, not how it is built. No `headless_registry`, `RestBuilder`,
  `get_serializer`, `get_view_set` or other internals.
- **Libraries the reader never touches.** No `rich`. Name `drf-flex-fields`
  only on the [Serializers](./website/docs/serializers.md) page, where
  `FlexibleSerializer` builds on it, and link to it there.
- **The internal API.** Only what `headless/__init__.py` and
  `headless.rest.filters` export, plus the documented integration points
  (`LookupFilter`, `SecretKeyAuthentication`, `PageNumberPagination`,
  `FlexibleSerializer`, `headless.rest.urls`, the `HEADLESS` settings), are
  documented. Anything else is not, and examples never import it.
- **Roadmap promises.** No "coming soon", "planned for", dates or versions
  for features that do not ship. Describe what exists.
- **Version history in prose.** No "formerly", "used to", "since rc.5",
  "new in", "previously", "no longer". History belongs in the changelog.

### Mention, with care

- **Django REST Framework**: freely, since the API is a DRF API. Write
  "Django REST Framework" on first mention on a page and "DRF" after. Link
  to the DRF documentation for DRF concepts (authentication classes,
  permission classes, filter backends) rather than explaining them again.
- **Other tools** (Strapi, Wagtail's API, django-ninja, …): only on a single
  comparison page, factually and without judging them. Nowhere else.
- **Django Content Studio**: only as a "see also" link, for readers who need
  an admin for editors.
- **Django**: freely. Link to the Django documentation for Django concepts
  rather than explaining them again.

## 6. Code examples

- **Complete and runnable.** Every snippet includes its imports and works
  as-is in a project with Django Headless installed. If a snippet is a
  fragment of a larger file (a `HEADLESS` dict, one model), say so in the
  text before it.
- **File path first.** Start each Python snippet with a comment naming the
  file: `# blog/models.py`, `# mysite/settings.py`, `# mysite/urls.py`.
- **One example project**: a blog, used on every page.
  - project package `mysite`; app `blog`; the API included at `api/`;
  - models `Article`, `Category` (related to `Article`), `Review` (a
    reverse relation of `Article`) and `SiteSettings` (a singleton);
  - routes `/api/blog.article`, `/api/blog.category`,
    `/api/blog.sitesettings`; the host `https://example.org`.
- **Requests** as the method and path in a `http` block
  (`GET /api/blog.article?published=true`). Use `curl` in a `bash` block
  only when headers matter.
- **Responses** as JSON with realistic data, indented with four spaces.
  Shorten long objects with `"...": "..."` rather than inventing fields.
- **Real values.** Realistic names and values (`"Getting started with
  Django"`, `"published"`), not `foo`, `bar` or `my_field`. Secrets as
  placeholders that read as such: `"your-secret-key"`.
- **Formatted** like the codebase: black for Python (line length 120),
  double quotes, two blank lines before a decorated class.

## 7. Page structure

1. **Title** with the page's emoji, in sentence case.
2. **Opening paragraph**: what the feature is and when to use it, in two or
   three sentences.
3. **The common case first**, with a complete example.
4. **Options and variations** after, most used first.
5. **Caveats** where they apply, each with its fix.
6. **Related pages** at the end when useful, as plain links.

The README follows the same voice and terminology. It covers what Django
Headless is, a short feature list without emoji, a quick start that works
when pasted, and links into the documentation; everything else lives on the
docs website.
